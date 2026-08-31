"""Model backend: local llama.cpp server (default), OpenAI-compatible API.

ARCHITECTURAL CONSEQUENCE OF RUNNING LOCALLY
--------------------------------------------
A local model has no server-side web-search tool. Source retrieval therefore
becomes ours (see retrieval.py).

That is a gain, not a loss. The hard prohibition no longer rests on an API
parameter we trust: the model only ever receives the excerpts we hand it. What
is not in the base does not exist for it. The prohibition becomes a physical
property of the corpus rather than an instruction.

The model never searches. It judges supplied evidence.

STRUCTURED OUTPUT
-----------------
llama-server constrains decoding with a GBNF grammar derived from a JSON
schema (`response_format: {"type": "json_schema", ...}`). Output is valid by
construction: we do not ask for JSON and hope, we make other tokens impossible.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Optional, Type

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


class LocalBackend:
    """llama-server, OpenAI-compatible API, schema-constrained decoding."""

    def __init__(self, url: str = LOCAL_URL, model: str = LOCAL_MODEL,
                 timeout: float = 300.0):
        self.url, self.model, self.timeout = url.rstrip("/"), model, timeout

    # -- diagnostics -------------------------------------------------------

    def available(self) -> tuple[bool, str]:
        try:
            with urllib.request.urlopen(f"{self.url}/models", timeout=5) as r:
                payload = json.loads(r.read())
            ids = [m["id"] for m in payload.get("data", payload.get("models", []))]
            return True, f"{len(ids)} model(s): {', '.join(ids[:4])}"
        except Exception as e:
            return False, f"{type(e).__name__}: {e}"

    # -- generation --------------------------------------------------------

    def json_struct(
        self,
        *,
        system: str,
        message: str,
        schema: Type[BaseModel],
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> Reply:
        """Generate output conforming to the given Pydantic schema.

        Low temperature by default: this checks facts, it does not write prose.
        The launcher's creative sampling settings are deliberately overridden.
        """
        body = {
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
        truncated = choice.get("finish_reason") == "length"

        try:
            obj = json.loads(extract_json(text))
        except json.JSONDecodeError:
            obj = None

        return Reply(
            data=obj,
            raw=text,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            truncated=truncated,
        )

    def _post(self, route: str, body: dict) -> dict:
        request = urllib.request.Request(
            self.url + route,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:400]
            raise BackendError(f"HTTP {e.code}: {detail}") from e
        except urllib.error.URLError as e:
            raise BackendError(
                f"llama-server unreachable at {self.url} -- {e.reason}. "
                "Start Qwen3.8UnslothQ4XL.bat."
            ) from e


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
    """Isolate the JSON object from output possibly preceded by a <think> block
    or wrapped in a Markdown fence."""
    t = text.strip()
    if "</think>" in t:
        t = t.rsplit("</think>", 1)[1].strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[-1]
        if "```" in t:
            t = t.rsplit("```", 1)[0]
    start, end = t.find("{"), t.rfind("}")
    return t[start:end + 1] if start != -1 and end > start else t
