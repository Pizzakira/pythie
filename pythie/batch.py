"""Batch hand-off: judge a run's claims outside the runtime.

WHAT THIS IS FOR
----------------
Two uses, one format.

  1. INTERIM BACKEND. While no API key is available, Pythie exports every claim
     with its evidence, a judge works through the file offline, and Pythie
     ingests the verdicts.
  2. GOLD SET. The same export, annotated by hand, becomes the reference the
     local model is measured against.

They are the same file because they should be: an interim verdict and a
reference verdict are produced from the same evidence and must be comparable.

WHAT MAKES IT SAFE
------------------
Ingested verdicts get NO privilege. They pass through the identical guardrails
as a model's output -- quote provenance, rank cap, published thresholds. A
verdict written by a human, by Claude, or by Qwen is checked the same way.

The export carries the composed brief and the primary source excerpts, so the
judging is done on exactly what the local model would have seen. Otherwise the
comparison would measure the evidence, not the judgement.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterator, List, Optional

from .backend import Reply
from .brief import Brief
from .retrieval import LocalBase, context_for_verification
from .schema import Statement, VerificationResult

FORMAT_VERSION = "1.0"


@dataclass
class BatchItem:
    """One claim, with everything needed to judge it and nothing more."""

    statement_id: str
    speaker: str
    text: str
    timestamp: Optional[float]
    invoked_measure: str
    domain: str
    source_keys: List[str]
    brief: str
    evidence: str

    def to_json(self) -> dict:
        return {
            "statement_id": self.statement_id,
            "speaker": self.speaker,
            "text": self.text,
            "timestamp": self.timestamp,
            "invoked_measure": self.invoked_measure,
            "domain": self.domain,
            "source_keys": self.source_keys,
            "brief": self.brief,
            "evidence": self.evidence,
        }


def export(
    statements: List[Statement],
    briefs: Dict[str, Brief],
    base: LocalBase,
    path: Path | str,
    *,
    debate: str = "",
) -> int:
    """Write one JSON object per line, ready to be judged.

    JSONL rather than a single array: a judge can work through it in chunks and
    a partial file stays valid.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    written = 0

    with path.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps({
            "_meta": {
                "format": FORMAT_VERSION,
                "debate": debate,
                "exported_on": datetime.now().isoformat(timespec="seconds"),
                "instructions": (
                    "Un objet par ligne. Pour chacun, rendre un verdict fonde "
                    "UNIQUEMENT sur le champ `evidence`. Si les extraits ne "
                    "permettent pas de trancher : unverified. La citation doit "
                    "etre recopiee mot pour mot depuis `evidence`."
                ),
            }
        }, ensure_ascii=False) + "\n")

        for statement in statements:
            brief = briefs.get(statement.id)
            if brief is None or brief.is_empty():
                continue
            item = BatchItem(
                statement_id=statement.id,
                speaker=statement.speaker,
                text=statement.text,
                timestamp=statement.timestamp,
                invoked_measure=brief.terms and ", ".join(brief.terms) or "",
                domain=brief.domains[0] if brief.domains else "",
                source_keys=brief.source_keys,
                brief=brief.text,
                evidence=context_for_verification(
                    base, brief.domains[0] if brief.domains else "", brief.source_keys
                ),
            )
            handle.write(json.dumps(item.to_json(), ensure_ascii=False) + "\n")
            written += 1

    return written


def read_items(path: Path | str) -> Iterator[BatchItem]:
    """Iterate the claims to judge, skipping the metadata header."""
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if "_meta" in record:
                continue
            yield BatchItem(**record)


@dataclass
class BatchBackend:
    """Replays verdicts judged offline, as if they came from a model.

    Deliberately a Backend like any other: the pipeline does not know or care
    where a verdict came from, and every guardrail downstream applies unchanged.
    """

    verdicts: Dict[str, dict] = field(default_factory=dict)
    name: str = "batch"
    missing: List[str] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path | str, name: str = "batch") -> "BatchBackend":
        verdicts: Dict[str, dict] = {}
        with Path(path).open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                if "_meta" in record:
                    continue
                statement_id = record.pop("statement_id", None)
                if statement_id:
                    verdicts[statement_id] = record
        return cls(verdicts=verdicts, name=name)

    def available(self) -> tuple[bool, str]:
        return bool(self.verdicts), f"{len(self.verdicts)} verdict(s) charge(s)"

    def verdict_for(self, statement_id: str) -> Optional[VerificationResult]:
        """Validated against the same schema as any model output.

        A malformed entry returns None and the caller abstains -- exactly what
        happens when a model drifts. No entry gets the benefit of the doubt for
        having been written by a person.
        """
        record = self.verdicts.get(statement_id)
        if record is None:
            self.missing.append(statement_id)
            return None
        try:
            return VerificationResult.model_validate(record)
        except Exception:
            return None

    def as_reply(self, statement_id: str) -> Reply:
        record = self.verdicts.get(statement_id)
        return Reply(
            data=record,
            raw=json.dumps(record, ensure_ascii=False) if record else "",
            backend=self.name,
        )


def compare(reference: BatchBackend, produced: BatchBackend) -> dict:
    """Score a run against a gold set.

    Metrics in the order that matters, not in the order that flatters:

      1. false positives -- true claims marked false. Decides publishability;
         each one is a potential lawsuit.
      2. abstention rate -- a system that never admits ignorance is lying.
      3. agreement -- how often the verdicts match at all.
    """
    shared = set(reference.verdicts) & set(produced.verdicts)
    if not shared:
        return {"error": "no statement id in common"}

    agree = 0
    false_positives: List[str] = []
    missed_falses: List[str] = []
    abstentions = 0

    for statement_id in shared:
        gold = reference.verdicts[statement_id].get("verdict")
        got = produced.verdicts[statement_id].get("verdict")
        if gold == got:
            agree += 1
        if got == "false" and gold in ("exact", "approximate"):
            false_positives.append(statement_id)
        if gold == "false" and got in ("exact", "approximate"):
            missed_falses.append(statement_id)
        if got == "unverified":
            abstentions += 1

    return {
        "compared": len(shared),
        "agreement": round(agree / len(shared), 3),
        "false_positives": len(false_positives),
        "false_positive_ids": false_positives,
        "missed_falses": len(missed_falses),
        "abstention_rate": round(abstentions / len(shared), 3),
        "only_in_reference": sorted(set(reference.verdicts) - shared),
        "only_in_run": sorted(set(produced.verdicts) - shared),
    }
