"""Run memory and candidate-profile enrichment.

Each verification call is stateless -- fresh context, no history. But the
ANALYSIS ITSELF persists: once block 1 has been settled, its findings stay
consultable by block 2. Memory lives here, outside the model, where it is
inspectable and deterministic.

Two horizons:

  RUN MEMORY      lasts one debate. Lets a repeated claim reuse the verdict it
                  already received, so the same sentence never shows two
                  colours on the same page.

  PROFILE         lasts across debates. Verified findings enrich the candidate
                  dossier that was authored upstream: the figures they
                  habitually cite, and the claims already checked.

THE GUARDRAIL THAT MAKES THE LOOP SAFE
--------------------------------------
A feedback loop amplifies its own errors. If a wrong red becomes a "recurring
error" in a dossier, the next debate inherits the bias and prior history turns
into prejudice.

So enrichment never writes into the durable dossier. It writes to a REVIEW
QUEUE, which a human promotes. And a promoted entry remains what the
specification already fixed: a lead that triggers normal verification against
the primary source, never a verdict in itself.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

from .memory import VerdictCache, normalise_claim
from .schema import Statement, Verdict

ROOT = Path(__file__).resolve().parent.parent
CANDIDATES_DIR = ROOT / "corpus" / "candidats"
REVIEW_DIR = ROOT / "data" / "review"

# Only settled, well-evidenced verdicts are worth carrying forward. Abstentions
# say something about our base, not about the speaker, so they never enrich a
# profile.
PROMOTABLE = {Verdict.EXACT, Verdict.APPROXIMATE, Verdict.FALSE}
MIN_CONFIDENCE = 0.75


@dataclass
class Finding:
    """One verified claim, ready for review before it reaches a dossier."""

    speaker: str
    statement_id: str
    text: str
    claim_key: str
    verdict: str
    confidence: float
    stated_value: Optional[str]
    source_value: Optional[str]
    source_url: str
    source_vintage: str
    quote: str
    debate: str
    observed_on: str
    occurrences: int = 1

    def to_dict(self) -> dict:
        return {
            "speaker": self.speaker,
            "statement_id": self.statement_id,
            "text": self.text,
            "claim_key": self.claim_key,
            "verdict": self.verdict,
            "confidence": round(self.confidence, 3),
            "stated_value": self.stated_value,
            "source_value": self.source_value,
            "source_url": self.source_url,
            "source_vintage": self.source_vintage,
            "quote": self.quote,
            "debate": self.debate,
            "observed_on": self.observed_on,
            "occurrences": self.occurrences,
            "status": "pending_review",
            "usage_if_promoted": "lead_only",
        }


@dataclass
class RunMemory:
    """Everything one debate accumulates. Consultable, never fed back into the
    model's context."""

    debate: str
    cache: VerdictCache = field(default_factory=VerdictCache)
    findings: Dict[str, Finding] = field(default_factory=dict)

    def record(self, statement: Statement) -> Optional[Finding]:
        """Register a settled statement. Returns the finding when promotable."""
        if statement.verdict not in PROMOTABLE:
            return None
        if (statement.confidence or 0.0) < MIN_CONFIDENCE:
            return None
        if not any(s.quote_verified for s in statement.sources):
            # Without a literally verified quote there is nothing to carry
            # forward; the verdict itself was already withdrawn upstream.
            return None
        if statement.withdrawn:
            # A human took this off the page. It must not re-enter through the
            # back door of profile enrichment.
            return None

        key = normalise_claim(statement.text)
        existing = self.findings.get(key)
        if existing:
            existing.occurrences += 1
            return existing

        source = next(s for s in statement.sources if s.quote_verified)
        finding = Finding(
            speaker=statement.speaker,
            statement_id=statement.id,
            text=statement.text,
            claim_key=key,
            verdict=statement.verdict.value,
            confidence=statement.confidence or 0.0,
            stated_value=statement.stated_value,
            source_value=statement.source_value,
            source_url=source.url,
            source_vintage=source.data_date or "",
            quote=source.quote,
            debate=self.debate,
            observed_on=date.today().isoformat(),
        )
        self.findings[key] = finding
        return finding

    def by_speaker(self) -> Dict[str, List[Finding]]:
        grouped: Dict[str, List[Finding]] = {}
        for finding in self.findings.values():
            grouped.setdefault(finding.speaker, []).append(finding)
        return grouped


def write_review_queue(
    memory: RunMemory, directory: Path | str = REVIEW_DIR
) -> List[Path]:
    """Write findings to the review queue, one file per speaker.

    Nothing here is authoritative. A human reads it, decides what deserves to
    enter the durable dossier, and the dossier keeps `usage: lead_only`.
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []

    for speaker, findings in memory.by_speaker().items():
        slug = "".join(c if c.isalnum() else "-" for c in speaker.lower()).strip("-")
        path = directory / f"{slug}--{memory.debate}.json"
        path.write_text(
            json.dumps(
                {
                    "speaker": speaker,
                    "debate": memory.debate,
                    "generated_on": date.today().isoformat(),
                    "status": "pending_review",
                    "note": (
                        "Propositions d'enrichissement du dossier candidat. "
                        "Rien n'entre dans le dossier durable sans relecture "
                        "humaine. Une entree promue reste une PISTE : elle "
                        "declenche la verification normale contre la source "
                        "primaire, elle ne vaut jamais verdict."
                    ),
                    "findings": [f.to_dict() for f in
                                 sorted(findings, key=lambda x: -x.occurrences)],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        written.append(path)

    return written


def load_known_claims(speaker_slug: str, directory: Path | str = CANDIDATES_DIR) -> Dict[str, dict]:
    """Read the claims already recorded in a candidate dossier.

    Returned as leads only. `pipeline` may use them to skip re-deriving the
    invoked measure, never to shortcut the verdict.
    """
    path = Path(directory) / f"{speaker_slug}.yaml"
    if not path.exists():
        return {}

    import yaml

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    known: Dict[str, dict] = {}

    for entry in (data.get("chiffres_recurrents") or []):
        text = entry.get("enonce_type", "")
        if text:
            known[normalise_claim(text)] = {"kind": "recurring_figure", **entry}

    for entry in (data.get("erreurs_recurrentes") or []):
        text = entry.get("enonce_type", "")
        if text:
            known[normalise_claim(text)] = {"kind": "recurring_error", **entry}

    return known
