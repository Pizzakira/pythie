"""Verdict cache -- memory kept OUTSIDE the model.

Every verification call is stateless: fresh context, no history, nothing
carried over. That buys reproducibility and prevents one block's verdict from
influencing the next.

It costs consistency across repeats: the same claim uttered twice could receive
two different verdicts, which is far more damaging to credibility than a single
wrong call -- same page, same sentence, two colours.

The fix is not to give the model memory. It is to keep the memory here, where
it is inspectable and deterministic: normalise the claim, look it up, reuse the
verdict. Every reuse is logged, so an auditor can see that block 12 reused
block 3's verdict rather than being asked again.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .schema import VerificationResult

# Function words carry no claim content and vary between two utterances of the
# same assertion. Dropping them makes "il y a 3 millions de chomeurs" and
# "on compte 3 millions de chomeurs" collide, which is what we want.
STOPWORDS = {
    "le", "la", "les", "un", "une", "des", "du", "de", "d", "l", "et", "ou",
    "a", "au", "aux", "en", "dans", "sur", "pour", "par", "avec", "sans",
    "il", "elle", "ils", "elles", "on", "nous", "vous", "je", "tu", "ce",
    "cet", "cette", "ces", "y", "est", "sont", "ete", "etre", "avoir", "ont",
    "que", "qui", "quoi", "dont", "ne", "pas", "plus", "aujourd", "hui",
    "aussi", "donc", "alors", "meme", "tout", "tous", "toute", "toutes",
}

NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


def normalise_claim(text: str) -> str:
    """Reduce a claim to a comparison key.

    Keeps figures verbatim -- they are the substance of the claim -- and strips
    accents, case, punctuation and function words. Two phrasings of the same
    assertion collapse to the same key; two different figures never do.
    """
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    # Normalise digit grouping: "2 710 400" and "2710400" are the same figure.
    text = re.sub(r"(?<=\d)[\s ](?=\d)", "", text)
    tokens = re.findall(r"[a-z0-9]+(?:[.,]\d+)?", text)
    kept = [t for t in tokens if t not in STOPWORDS]
    return " ".join(kept)


def claim_figures(text: str) -> Tuple[str, ...]:
    """Figures in the claim, normalised. Two claims cannot share a verdict
    unless they carry exactly the same figures."""
    cleaned = re.sub(r"(?<=\d)[\s ](?=\d)", "", text)
    return tuple(NUMBER.findall(cleaned))


@dataclass
class CacheEntry:
    key: str
    figures: Tuple[str, ...]
    result: VerificationResult
    first_statement_id: str
    first_text: str
    reuse_count: int = 0
    reused_by: List[str] = field(default_factory=list)


@dataclass
class VerdictCache:
    """Deterministic, inspectable, and scoped to one debate.

    Not persisted across debates on purpose: a figure true in March may be
    false in June, and a stale verdict is worse than a fresh one.
    """

    entries: Dict[str, CacheEntry] = field(default_factory=dict)
    hits: int = 0
    misses: int = 0

    def lookup(self, text: str) -> Optional[CacheEntry]:
        key = normalise_claim(text)
        entry = self.entries.get(key)
        if entry is None:
            self.misses += 1
            return None
        # Guard: identical key but different figures must never share a verdict.
        if entry.figures != claim_figures(text):
            self.misses += 1
            return None
        self.hits += 1
        return entry

    def store(self, statement_id: str, text: str, result: VerificationResult) -> None:
        key = normalise_claim(text)
        if key in self.entries:
            return
        self.entries[key] = CacheEntry(
            key=key,
            figures=claim_figures(text),
            result=result,
            first_statement_id=statement_id,
            first_text=text,
        )

    def record_reuse(self, entry: CacheEntry, statement_id: str) -> None:
        entry.reuse_count += 1
        entry.reused_by.append(statement_id)

    # -- audit trail -------------------------------------------------------

    def audit_log(self) -> List[dict]:
        """What an auditor needs: which verdicts were reused, and where."""
        return [
            {
                "key": e.key,
                "verdict": e.result.verdict.value,
                "first_seen_in": e.first_statement_id,
                "first_text": e.first_text,
                "reused": e.reuse_count,
                "reused_by": e.reused_by,
            }
            for e in self.entries.values()
            if e.reuse_count
        ]

    def write_audit(self, path: str | Path) -> None:
        Path(path).write_text(
            json.dumps(
                {
                    "hits": self.hits,
                    "misses": self.misses,
                    "reused_verdicts": self.audit_log(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
