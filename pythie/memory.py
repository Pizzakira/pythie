"""Claim ledger -- memory kept OUTSIDE the model.

Every verification is a fresh, stateless call. What persists is the ANALYSIS,
here, where it is inspectable and deterministic.

WHY THIS IS A LEDGER AND NOT A CACHE
------------------------------------
A cache would short-circuit: same claim, return the stored verdict, never ask
again. That buys consistency cheaply and is brittle -- a wrong first verdict is
inherited silently by every repeat, and repetition is hidden rather than
measured.

Instead, each occurrence is re-verified from scratch, and what gets reused is
the GROUNDWORK: the routing decision, the sources opened, the measure
identified. That is the expensive half; the judgement is re-run.

Repetition then becomes a test rather than a shortcut:

  - three independent verifications agreeing is far stronger evidence than one
    verdict copied three times;
  - a disagreement between occurrences is DETECTED instead of masked, and the
    honest reading of two contradictory readings of the same sentence is that
    we do not know -- so we abstain, and correct the earlier block
    retroactively.

That retroactive correction is exactly the revision event the interface
already renders.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .schema import Verdict, VerificationResult

# Function words carry no claim content and vary between two utterances of the
# same assertion. Dropping them lets phrasings collide; figures never do.
STOPWORDS = {
    "le", "la", "les", "un", "une", "des", "du", "de", "d", "l", "et", "ou",
    "a", "au", "aux", "en", "dans", "sur", "pour", "par", "avec", "sans",
    "il", "elle", "ils", "elles", "on", "nous", "vous", "je", "tu", "ce",
    "cet", "cette", "ces", "y", "est", "sont", "ete", "etre", "avoir", "ont",
    "que", "qui", "quoi", "dont", "ne", "pas", "plus", "aujourd", "hui",
    "aussi", "donc", "alors", "meme", "tout", "tous", "toute", "toutes",
    "compte", "compter", "existe", "reste", "fait", "faire",
}

NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


def normalise_claim(text: str) -> str:
    """Reduce a claim to a comparison key.

    Figures are kept verbatim -- they are the substance. Accents, case,
    punctuation and function words go.
    """
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    text = re.sub(r"(?<=\d)[\s ](?=\d)", "", text)  # "2 710 400" -> "2710400"
    tokens = re.findall(r"[a-z0-9]+(?:[.,]\d+)?", text)
    return " ".join(t for t in tokens if t not in STOPWORDS)


def claim_figures(text: str) -> Tuple[str, ...]:
    """Figures in the claim. Two claims never share an entry unless their
    figures match exactly."""
    return tuple(NUMBER.findall(re.sub(r"(?<=\d)[\s ](?=\d)", "", text)))


class Corroboration(str, Enum):
    SINGLE = "single"              # seen once, nothing to compare against
    CORROBORATED = "corroborated"  # verified again, same verdict
    CONFLICTED = "conflicted"      # verified again, different verdict -> abstain


@dataclass
class Groundwork:
    """The reusable half: what it took to find the evidence.

    Reusing this skips the routing call. It never carries a verdict -- the
    judgement is always re-run.
    """

    domain: str
    source_keys: List[str]
    invoked_measure: str

    def as_hint(self) -> str:
        return (
            f"Une occurrence anterieure de cette affirmation a ete situee dans "
            f"le domaine « {self.domain} », grandeur « {self.invoked_measure} », "
            f"sources : {', '.join(self.source_keys)}."
        )


@dataclass
class Occurrence:
    statement_id: str
    text: str
    verdict: Verdict
    confidence: float
    stated_value: Optional[str] = None
    source_value: Optional[str] = None


@dataclass
class LedgerEntry:
    key: str
    figures: Tuple[str, ...]
    occurrences: List[Occurrence] = field(default_factory=list)
    groundwork: Optional[Groundwork] = None

    # Sticky: consolidation rewrites every occurrence to UNVERIFIED, which
    # would otherwise erase the evidence of the conflict and let a later
    # occurrence start over as if nothing had happened. Once a claim has been
    # read two different ways, that stays true for the rest of the debate.
    conflicted: bool = False

    @property
    def verdicts(self) -> List[Verdict]:
        return [o.verdict for o in self.occurrences]

    def status(self) -> Corroboration:
        if self.conflicted:
            return Corroboration.CONFLICTED
        settled = [
            o for o in self.occurrences
            if o.verdict in (Verdict.EXACT, Verdict.APPROXIMATE, Verdict.FALSE)
        ]
        if len(settled) < 2:
            return Corroboration.SINGLE
        distinct = {o.verdict for o in settled}
        return (
            Corroboration.CORROBORATED if len(distinct) == 1
            else Corroboration.CONFLICTED
        )

    def corroborated_confidence(self) -> float:
        """Confidence after corroboration.

        Independent agreement raises it, but never to certainty: two runs of
        the same model on the same evidence are not fully independent, so the
        bonus is deliberately modest.
        """
        settled = [o for o in self.occurrences if o.verdict != Verdict.UNVERIFIED]
        if not settled:
            return 0.0
        base = max(o.confidence for o in settled)
        if self.status() != Corroboration.CORROBORATED:
            return base
        bonus = min(0.05 * (len(settled) - 1), 0.10)
        return min(base + bonus, 0.98)


@dataclass
class Revision:
    """A verdict to rewrite on a block already on screen."""

    statement_id: str
    previous: Verdict
    new: Verdict
    note: str


@dataclass
class ClaimLedger:
    """Scoped to one debate.

    Not carried across debates on purpose: a figure true in March may be false
    in June, and a stale verdict is worse than a fresh one.
    """

    entries: Dict[str, LedgerEntry] = field(default_factory=dict)
    reused_groundwork: int = 0
    reverifications: int = 0

    # -- reusable groundwork ----------------------------------------------

    def groundwork_for(self, text: str) -> Optional[Groundwork]:
        """Prior routing for this claim, if any. Saves the routing call."""
        entry = self._entry_for(text)
        if entry and entry.groundwork:
            self.reused_groundwork += 1
            return entry.groundwork
        return None

    def prior_context(self, text: str) -> Optional[str]:
        """What earlier occurrences concluded, as CONTEXT for a re-verification.

        Handed to the model so it can consolidate or contradict -- never so it
        can copy. The judgement is still made against the primary sources.
        """
        entry = self._entry_for(text)
        if not entry or not entry.occurrences:
            return None
        lines = [
            f"  - {o.statement_id} : {o.verdict.value} "
            f"(enonce {o.stated_value or '-'}, source {o.source_value or '-'})"
            for o in entry.occurrences
        ]
        return (
            "Cette affirmation a deja ete verifiee dans ce debat :\n"
            + "\n".join(lines)
            + "\nVerifie-la de nouveau contre les sources fournies. Si tu "
            "aboutis a autre chose, dis-le : un desaccord est une information."
        )

    def _entry_for(self, text: str) -> Optional[LedgerEntry]:
        entry = self.entries.get(normalise_claim(text))
        if entry and entry.figures == claim_figures(text):
            return entry
        return None

    # -- recording ---------------------------------------------------------

    def record(
        self,
        statement_id: str,
        text: str,
        result: VerificationResult,
        groundwork: Optional[Groundwork] = None,
    ) -> List[Revision]:
        """Register an occurrence and consolidate.

        Returns the revisions to apply to blocks already displayed.
        """
        key = normalise_claim(text)
        entry = self.entries.get(key)
        if entry is None or entry.figures != claim_figures(text):
            entry = LedgerEntry(key=key, figures=claim_figures(text))
            self.entries[key] = entry
        else:
            self.reverifications += 1

        if groundwork and not entry.groundwork:
            entry.groundwork = groundwork

        entry.occurrences.append(
            Occurrence(
                statement_id=statement_id,
                text=text,
                verdict=result.verdict,
                confidence=result.confidence,
                stated_value=result.stated_value,
                source_value=result.source_value,
            )
        )

        return self._consolidate(entry)

    def _consolidate(self, entry: LedgerEntry) -> List[Revision]:
        """Reconcile occurrences of one claim.

        Agreement raises confidence on all of them. Disagreement means two
        independent readings of the same sentence reached different
        conclusions: we do not know, so every occurrence -- including the ones
        already on screen -- becomes an abstention.
        """
        status = entry.status()
        if status == Corroboration.SINGLE:
            return []

        if status == Corroboration.CORROBORATED:
            boosted = entry.corroborated_confidence()
            for occurrence in entry.occurrences:
                occurrence.confidence = max(occurrence.confidence, boosted)
            return []

        entry.conflicted = True
        note = (
            "Verdicts divergents entre occurrences de la meme affirmation ("
            + ", ".join(sorted({o.verdict.value for o in entry.occurrences}))
            + "). Deux lectures independantes ne concordent pas : verdict retire."
        )
        revisions = [
            Revision(
                statement_id=occurrence.statement_id,
                previous=occurrence.verdict,
                new=Verdict.UNVERIFIED,
                note=note,
            )
            for occurrence in entry.occurrences
            if occurrence.verdict != Verdict.UNVERIFIED
        ]
        for occurrence in entry.occurrences:
            occurrence.verdict = Verdict.UNVERIFIED
            occurrence.confidence = min(occurrence.confidence, 0.3)
        return revisions

    # -- audit -------------------------------------------------------------

    def audit_log(self) -> List[dict]:
        return [
            {
                "key": entry.key,
                "status": entry.status().value,
                "occurrences": [
                    {
                        "statement_id": o.statement_id,
                        "verdict": o.verdict.value,
                        "confidence": round(o.confidence, 3),
                    }
                    for o in entry.occurrences
                ],
                "groundwork_reused": entry.groundwork is not None,
            }
            for entry in self.entries.values()
            if len(entry.occurrences) > 1
        ]

    def write_audit(self, path: str | Path) -> None:
        Path(path).write_text(
            json.dumps(
                {
                    "reverifications": self.reverifications,
                    "groundwork_reuses": self.reused_groundwork,
                    "repeated_claims": self.audit_log(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
