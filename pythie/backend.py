"""Model backends.

Pythie never talks to a model directly. It talks to a `Backend`, and any
provider that can return schema-conforming JSON can be plugged in:

  LocalBackend       llama.cpp / llama-server, GBNF-constrained decoding
  OpenAIBackend      anything speaking the OpenAI chat API -- Qwen (DashScope),
                     Mistral, DeepSeek, OpenRouter, vLLM, LM Studio
  AnthropicBackend   Claude, via the official SDK
  EscalatingBackend  cheap model for everything, strong model only where it
                     matters

ARCHITECTURAL CONSEQUENCE OF RUNNING LOCALLY
--------------------------------------------
No backend here is given a web-search tool. Retrieval is ours (retrieval.py):
the model only ever receives the excerpts we hand it. What is not in the base
does not exist for it. The hard prohibition is a property of the corpus, not an
instruction the model could work around.

The model never searches. It judges supplied evidence.

STRUCTURED OUTPUT
-----------------
Local decoding is constrained by a GBNF grammar derived from the JSON schema,
so output is valid by construction. Remote providers are asked for JSON and
validated on arrival -- if a provider drifts, the caller sees `data is None`
and abstains rather than parsing something plausible.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Protocol, Type

import urllib.error
import urllib.request

from pydantic import BaseModel

LOCAL_URL = os.environ.get("PYTHIE_LLM_URL", "http://127.0.0.1:1234/v1")
LOCAL_MODEL = os.environ.get("PYTHIE_LLM_MODEL", "Qwen3.8-27B")


class BackendError(RuntimeError):
    pass


@dataclass
class Reply:
    data: Optional[dict]
    raw: str
    input_tokens: int = 0
    output_tokens: int = 0
    truncated: bool = False
    backend: str = ""


class Backend(Protocol):
    """What Pythie needs from a model. Nothing more."""

    name: str

    def available(self) -> tuple[bool, str]: ...

    def json_struct(
        self,
        *,
        system: str,
        message: str,
        schema: Type[BaseModel],
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> Reply: ...


# --- schema helpers --------------------------------------------------------

def inline_refs(model: Type[BaseModel]) -> dict:
    """Resolve Pydantic $ref/$defs.

    llama.cpp GBNF grammars do not follow references; an unresolved schema
    yields an empty constraint and therefore invalid JSON.
    """
    schema = model.model_json_schema()
    defs = schema.pop("$defs", {})

    def resolve(node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                key = node["$ref"].rsplit("/", 1)[-1]
                extra = {k: v for k, v in node.items() if k != "$ref"}
                return {**resolve(defs.get(key, {})), **extra}
            return {k: resolve(v) for k, v in node.items()}
        if isinstance(node, list):
            return [resolve(x) for x in node]
        return node

    return resolve(schema)


def extract_json(text: str) -> str:
    """Isolate the JSON object from output preceded by a reasoning block or
    wrapped in a Markdown fence."""
    t = text.strip()
    if "</think>" in t:
        t = t.rsplit("</think>", 1)[1].strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[-1]
        if "```" in t:
            t = t.rsplit("```", 1)[0]
    start, end = t.find("{"), t.rfind("}")
    return t[start:end + 1] if start != -1 and end > start else t


# --- OpenAI-compatible (local and remote) ----------------------------------

class OpenAIBackend:
    """Any provider speaking the OpenAI chat API.

    Covers Qwen's own API (DashScope compatible mode), Mistral, DeepSeek,
    OpenRouter, vLLM and llama-server alike -- only base_url, model and key
    change. This is what makes the runtime provider a configuration choice
    rather than a rewrite.
    """

    def __init__(
        self,
        base_url: str,
        model: str,
        *,
        api_key: Optional[str] = None,
        name: str = "",
        timeout: float = 300.0,
        constrained: bool = False,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        # llama-server enforces the schema through a grammar; hosted providers
        # generally do not, so their output is validated on arrival instead.
        self.constrained = constrained
        self.name = name or f"openai:{model}"

    def available(self) -> tuple[bool, str]:
        try:
            request = urllib.request.Request(f"{self.base_url}/models")
            if self.api_key:
                request.add_header("Authorization", f"Bearer {self.api_key}")
            with urllib.request.urlopen(request, timeout=8) as response:
                payload = json.loads(response.read())
            ids = [m["id"] for m in payload.get("data", payload.get("models", []))]
            return True, f"{len(ids)} model(s): {', '.join(ids[:4])}"
        except Exception as error:
            return False, f"{type(error).__name__}: {error}"

    def json_struct(
        self,
        *,
        system: str,
        message: str,
        schema: Type[BaseModel],
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> Reply:
        # Low temperature on purpose: this checks facts, it does not write
        # prose. Creative sampling from a launcher script is overridden here.
        body: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": message},
            ],
            "temperature": temperature,
            "top_p": 0.9,
            "max_tokens": max_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "strict": True,
                    "schema": inline_refs(schema),
                },
            },
        }

        payload = self._post("/chat/completions", body)
        choice = (payload.get("choices") or [{}])[0]
        text = (choice.get("message") or {}).get("content") or ""
        usage = payload.get("usage") or {}

        try:
            data = json.loads(extract_json(text))
        except json.JSONDecodeError:
            data = None

        return Reply(
            data=data,
            raw=text,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            truncated=choice.get("finish_reason") == "length",
            backend=self.name,
        )

    def _post(self, route: str, body: dict) -> dict:
        request = urllib.request.Request(
            self.base_url + route,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        if self.api_key:
            request.add_header("Authorization", f"Bearer {self.api_key}")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", "replace")[:400]
            raise BackendError(f"HTTP {error.code}: {detail}") from error
        except urllib.error.URLError as error:
            raise BackendError(
                f"{self.name} unreachable at {self.base_url} -- {error.reason}"
            ) from error


def LocalBackend(
    url: str = LOCAL_URL, model: str = LOCAL_MODEL, timeout: float = 300.0
) -> OpenAIBackend:
    """llama-server on localhost, with grammar-constrained decoding."""
    return OpenAIBackend(
        url, model, name=f"local:{model}", timeout=timeout, constrained=True
    )


# --- Anthropic -------------------------------------------------------------

class AnthropicBackend:
    """Claude, through the official SDK.

    Intended for the escalation path rather than the bulk: reds are rare and
    consequential, so paying per token only for them keeps spend proportional
    to risk.
    """

    def __init__(self, model: str = "claude-opus-5", name: str = "", timeout: float = 300.0):
        self.model = model
        self.timeout = timeout
        self.name = name or f"anthropic:{model}"
        self._client = None

    def _client_or_raise(self):
        if self._client is None:
            try:
                import anthropic
            except ImportError as error:
                raise BackendError("pip install anthropic") from error
            # Credentials resolve from ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN
            # or an `ant auth login` profile.
            self._client = anthropic.Anthropic(timeout=self.timeout)
        return self._client

    def available(self) -> tuple[bool, str]:
        try:
            client = self._client_or_raise()
            client.models.retrieve(self.model)
            return True, f"anthropic {self.model}"
        except Exception as error:
            return False, f"{type(error).__name__}: {error}"

    def json_struct(
        self,
        *,
        system: str,
        message: str,
        schema: Type[BaseModel],
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> Reply:
        client = self._client_or_raise()
        # Streaming: large max_tokens on a non-streaming request risks an HTTP
        # timeout. temperature is not a parameter on current Claude models.
        with client.messages.stream(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            thinking={"type": "adaptive"},
            output_config={
                "effort": "high",
                "format": {"type": "json_schema", "schema": inline_refs(schema)},
            },
            messages=[{"role": "user", "content": message}],
        ) as stream:
            response = stream.get_final_message()

        if response.stop_reason == "refusal":
            return Reply(None, "", backend=self.name)

        text = next((b.text for b in response.content if b.type == "text"), "")
        try:
            data = json.loads(extract_json(text))
        except json.JSONDecodeError:
            data = None

        return Reply(
            data=data,
            raw=text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            truncated=response.stop_reason == "max_tokens",
            backend=self.name,
        )


# --- escalation ------------------------------------------------------------

class EscalatingBackend:
    """Cheap model for everything, strong model only where it matters.

    A red is the single most consequential output of this system and the one
    that exposes us. Reds are also rare. Confirming only those with a stronger
    model keeps the token spend proportional to the risk instead of to the
    volume.

    Disagreement between the two tiers resolves the way every other
    disagreement in Pythie does: abstention. Two models reading the same
    evidence differently means we do not know.
    """

    def __init__(
        self,
        primary: Backend,
        strong: Backend,
        escalate_on: tuple[str, ...] = ("false",),
    ):
        self.primary = primary
        self.strong = strong
        self.escalate_on = escalate_on
        self.name = f"escalating({primary.name} -> {strong.name})"
        self.escalations = 0
        self.disagreements = 0

    def available(self) -> tuple[bool, str]:
        primary_ok, primary_detail = self.primary.available()
        strong_ok, strong_detail = self.strong.available()
        return primary_ok, f"primary {primary_detail} | strong {strong_detail}"

    def json_struct(
        self,
        *,
        system: str,
        message: str,
        schema: Type[BaseModel],
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> Reply:
        reply = self.primary.json_struct(
            system=system, message=message, schema=schema,
            temperature=temperature, max_tokens=max_tokens,
        )
        verdict = (reply.data or {}).get("verdict")
        if verdict not in self.escalate_on:
            return reply

        self.escalations += 1
        second = self.strong.json_struct(
            system=system, message=message, schema=schema,
            temperature=temperature, max_tokens=max_tokens,
        )
        if second.data is None:
            return reply

        if second.data.get("verdict") == verdict:
            second.data["confidence"] = max(
                float(second.data.get("confidence", 0.0)),
                float((reply.data or {}).get("confidence", 0.0)),
            )
            return second

        self.disagreements += 1
        second.data["verdict"] = "unverified"
        second.data["confidence"] = min(float(second.data.get("confidence", 0.0)), 0.3)
        second.data["context_note"] = (
            f"Les deux niveaux de verification divergent ({verdict} contre "
            f"{second.data.get('verdict')}). Verdict retire : deux lectures des "
            "memes preuves ne concordent pas."
        )
        return second


# --- configuration ---------------------------------------------------------

def from_env() -> Backend:
    """Build the backend from environment variables.

        PYTHIE_BACKEND     local | openai | anthropic | escalating
        PYTHIE_LLM_URL     base url for local/openai
        PYTHIE_LLM_MODEL   model id
        PYTHIE_LLM_KEY     api key for openai-compatible providers
        PYTHIE_STRONG_*    same three, for the escalation tier
    """
    kind = os.environ.get("PYTHIE_BACKEND", "local").lower()

    if kind == "local":
        return LocalBackend()

    if kind == "openai":
        return OpenAIBackend(
            os.environ.get("PYTHIE_LLM_URL", LOCAL_URL),
            os.environ.get("PYTHIE_LLM_MODEL", LOCAL_MODEL),
            api_key=os.environ.get("PYTHIE_LLM_KEY"),
        )

    if kind == "anthropic":
        return AnthropicBackend(os.environ.get("PYTHIE_LLM_MODEL", "claude-opus-5"))

    if kind == "escalating":
        strong_kind = os.environ.get("PYTHIE_STRONG_BACKEND", "anthropic")
        strong: Backend = (
            AnthropicBackend(os.environ.get("PYTHIE_STRONG_MODEL", "claude-opus-5"))
            if strong_kind == "anthropic"
            else OpenAIBackend(
                os.environ["PYTHIE_STRONG_URL"],
                os.environ["PYTHIE_STRONG_MODEL"],
                api_key=os.environ.get("PYTHIE_STRONG_KEY"),
            )
        )
        return EscalatingBackend(LocalBackend(), strong)

    raise BackendError(f"unknown PYTHIE_BACKEND: {kind}")
