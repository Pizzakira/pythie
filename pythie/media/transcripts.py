"""Agreement between transcriptions -- the layer that guards against a
fabricated quote.

WHAT THIS EXISTS TO PREVENT
---------------------------
On 31/08/2026 the chain returned its first red, at 99% confidence, perfectly
sourced:

    FALSE -- "Je vous cite de au feu 600 millions de dettes francaises."
    600 millions contre 3 460 milliards (INSEE, fin 2025).

The verdict is sound if one accepts the text. The text is ASR debris -- "de au
feu" -- so the system marked as false a sentence nobody uttered. That is the
fabricated quote the whole architecture exists to prevent, and it appeared on
the first real pass, because this layer was described in METHODE.md §7 as "held
by design" while not existing at all.

THE RULE
--------
A value nobody but one transcription heard is not a value. It is not judged.

Agreement corroborates. Disagreement abstains. Silence abstains too: a witness
that says nothing where the primary heard a figure is not a confirmation, and
under this project's governing rule a wrong attribution costs more than a
missing one.

WHAT MUST AGREE
---------------
The FIGURE, not the wording. Two transcriptions of the same audio always differ
in punctuation, in filler words and in segment boundaries; requiring identical
sentences would abstain on everything and measure nothing but ASR style. What a
verdict rests on is the quantity -- and the quantity either matches or it does
not.

A statement's non-year quantities must ALL be found in an independent witness.
Years are compared when both carry one, but a missing year does not veto: a
witness that drops "en 2025" has not contradicted the figure.

A number found anywhere in a 40-second window would corroborate too easily --
debates are full of numbers. So a match must also be ANCHORED: the words around
the witness's figure must share content words with the statement. Alignment
between two transcriptions is loose (interpolated timestamps, merged blocks),
the anchor is what makes a loose window safe.

INDEPENDENCE IS DECLARED, NOT ASSUMED
-------------------------------------
Two ASR of the same family agreeing proves nothing: a fine-tune inherits the
failure modes of its base model, so it fails in the same places (METHODE.md §9).
Demonstrated on this audio at 150:18 -- both Whisper models write "debut du
cafe", CrisperWhisper writes "quinquennat", which is right (D-047). Only a
transcript declaring a DIFFERENT family counts as a witness.

DECLARED PARAMETERS, NOT YET SWEPT
----------------------------------
`Settings` below holds every adjustable value in this layer. They are estimates
until `ETUDES/banc_accord.py` sweeps them; the bench publishes the curve, and
METHODE.md §2 is the reason it exists.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

from ..numbers import Kind, Quantity, normalise, quantities


# --- transcripts -----------------------------------------------------------

STOPWORDS = {
    "le", "la", "les", "de", "des", "du", "un", "une", "et", "en", "a", "au",
    "aux", "que", "qui", "ce", "cette", "ces", "on", "il", "elle", "nous",
    "vous", "je", "tu", "ils", "elles", "est", "sont", "ete", "pas", "ne",
    "plus", "moins", "pour", "dans", "sur", "avec", "par", "se", "sa", "son",
    "ses", "leur", "leurs", "mais", "ou", "donc", "car", "y", "d", "l", "c",
    "j", "n", "s", "qu", "the", "of",
}


@dataclass
class Block:
    start: float
    end: float
    text: str


@dataclass
class Transcript:
    """One reading of the audio, with the family it belongs to declared."""

    name: str
    family: str
    blocks: List[Block] = field(default_factory=list)

    @classmethod
    def load(cls, path: str | Path, *, family: str = "", name: str = "") -> "Transcript":
        path = Path(path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        meta = payload.get("transcription", {})
        declared = family or meta.get("famille", "")
        if not declared:
            # Refusing to guess: an undeclared family would silently be counted
            # as independent from everything, which is the one error this layer
            # cannot afford. The caller must say.
            raise ValueError(
                f"{path.name} ne declare aucune famille de transcription. "
                "Precisez-la (--famille) : compter deux ASR de la meme famille "
                "comme deux temoins invaliderait tout l'accord."
            )
        return cls(
            name=name or meta.get("modele", path.stem),
            family=declared,
            blocks=[Block(b["debut"], b["fin"], b["texte"]) for b in payload["blocs"]],
        )

    @property
    def duration(self) -> float:
        return self.blocks[-1].end if self.blocks else 0.0

    def window(self, start: float, end: float) -> str:
        """Everything said between two marks, blocks included as soon as they
        overlap the interval at all."""
        return " ".join(b.text for b in self.blocks if b.end >= start and b.start <= end)


# --- the decision ----------------------------------------------------------

class Status(str, Enum):
    CONFIRMED = "confirmed"        # an independent witness heard the same figures
    DIVERGENT = "divergent"        # the witness heard other figures there
    ABSENT = "absent"              # the witness heard no figure there
    NO_WITNESS = "no_witness"      # no independent transcript covers this time
    NO_QUANTITY = "no_quantity"    # nothing numeric to corroborate


@dataclass
class Settings:
    """Every adjustable value of this layer, in one place.

    NOT SWEPT. These are estimates -- see METHODE.md §2, which names unswept
    thresholds as the weakest point of the project. `ETUDES/banc_accord.py`
    sweeps them and publishes the curve; until a value is justified by that
    curve it is an opinion, and it is written here so it can be argued with.
    """

    pad: float = 20.0
    """Seconds of slack on each side of a statement. Timestamps are
    interpolated inside a block, and two transcriptions cut blocks differently:
    the window must absorb that drift. Too wide and any figure in the
    neighbourhood corroborates -- which is what the anchor guards against."""

    min_anchor: float = 0.20
    """Share of the statement's content words that must appear next to the
    witness's figure. Keeps a match from landing on an unrelated number that
    happened to fall inside the window."""

    anchor_span: int = 12
    """Words on each side of the witness's figure that count as its context."""

    min_content_words: int = 3
    """Below this, a statement has too few content words for the anchor to mean
    anything, and the figure match stands alone."""


@dataclass
class Agreement:
    """What the witnesses said about one statement, and why it was believed."""

    status: Status
    witness: str = ""
    witness_text: str = ""
    matched: List[str] = field(default_factory=list)
    missing: List[str] = field(default_factory=list)
    unanchored: List[str] = field(default_factory=list)
    heard_instead: List[str] = field(default_factory=list)
    reason: str = ""

    @property
    def corroborated(self) -> bool:
        return self.status == Status.CONFIRMED

    def note(self) -> str:
        """One sentence for the rendered page. French, factual, no blame."""
        if self.status == Status.CONFIRMED:
            return (f"Chiffre corrobore par une seconde transcription "
                    f"independante ({self.witness}).")
        if self.unanchored and len(self.unanchored) == len(self.missing):
            # The figure IS in the witness, but surrounded by other words. Two
            # readings, and we cannot tell them apart: either the alignment
            # drifted, or the number belongs to another sentence entirely.
            return (f"Le chiffre « {', '.join(self.unanchored)} » figure chez "
                    f"{self.witness} mais dans un autre contexte. Correspondance "
                    "non ancree : pas de corroboration.")
        if self.status == Status.DIVERGENT:
            heard = ", ".join(self.heard_instead[:3]) or "autre chose"
            return (f"Desaccord entre transcriptions : « {', '.join(self.missing)} » "
                    f"d'un cote, « {heard} » de l'autre ({self.witness}). "
                    "Aucun verdict : on ne sait pas ce qui a ete dit.")
        if self.status == Status.ABSENT:
            return (f"La seconde transcription ({self.witness}) ne rapporte aucun "
                    f"chiffre a cet endroit. Valeur entendue par une seule source, "
                    "donc non jugee.")
        if self.status == Status.NO_WITNESS:
            return ("Une seule transcription disponible : le chiffre n'est "
                    "corrobore par aucune source independante.")
        return "Aucun chiffre a corroborer."


def _content_words(text: str) -> set[str]:
    return {w for w in normalise(text).split()
            if len(w) > 2 and w not in STOPWORDS and not w[0].isdigit()}


def _anchored(statement: str, witness_tokens: Sequence[str], position: int,
              settings: Settings) -> float:
    """How much of the statement's vocabulary surrounds the witness's figure."""
    wanted = _content_words(statement)
    if len(wanted) < settings.min_content_words:
        return 1.0
    lo = max(0, position - settings.anchor_span)
    hi = min(len(witness_tokens), position + settings.anchor_span)
    around = {w for w in witness_tokens[lo:hi]
              if len(w) > 2 and w not in STOPWORDS and not w[0].isdigit()}
    return len(wanted & around) / len(wanted)


def corroborate(
    text: str,
    start: float,
    end: float,
    witnesses: Sequence[Transcript],
    settings: Optional[Settings] = None,
) -> Agreement:
    """Was this statement's figure heard by anyone else?

    `witnesses` must already be filtered to independent families -- see
    `independent`. The first witness that confirms wins; a statement needs one
    corroboration, not unanimity, because a third transcription missing a
    passage says nothing about the two that agree.
    """
    settings = settings or Settings()
    required = [q for q in quantities(text) if q.kind is not Kind.YEAR]

    if not required:
        return Agreement(status=Status.NO_QUANTITY,
                         reason="aucun chiffre dans l'enonce")
    if not witnesses:
        return Agreement(status=Status.NO_WITNESS,
                         missing=[q.raw for q in required],
                         reason="aucune transcription independante")

    best: Optional[Agreement] = None

    for witness in witnesses:
        heard = witness.window(start - settings.pad, end + settings.pad)
        witness_tokens = normalise(heard).split()
        available = [q for q in quantities(heard) if q.kind is not Kind.YEAR]

        matched: List[str] = []
        missing: List[str] = []
        unanchored: List[str] = []
        for wanted in required:
            equal = [q for q in available if wanted.matches(q)]
            hit = next(
                (q for q in equal
                 if _anchored(text, witness_tokens, q.position, settings)
                 >= settings.min_anchor),
                None,
            )
            if hit:
                matched.append(wanted.raw)
                continue
            missing.append(wanted.raw)
            if equal:
                # Same number, wrong neighbourhood. Kept apart from a plain
                # disagreement: it says the window or the anchor is wrong, not
                # that two models heard different figures.
                unanchored.append(wanted.raw)

        if not missing:
            return Agreement(
                status=Status.CONFIRMED, witness=witness.name,
                witness_text=heard[:400], matched=matched,
                reason=f"{len(matched)} chiffre(s) retrouve(s) chez {witness.name}",
            )

        candidate = Agreement(
            status=Status.DIVERGENT if available else Status.ABSENT,
            witness=witness.name, witness_text=heard[:400],
            matched=matched, missing=missing, unanchored=unanchored,
            heard_instead=[q.raw for q in available][:6],
            reason=("chiffres differents" if available
                    else "aucun chiffre chez le temoin"),
        )
        # Prefer the most informative failure: a witness that heard other
        # figures tells us more than one that heard none.
        if best is None or (best.status is Status.ABSENT
                            and candidate.status is Status.DIVERGENT):
            best = candidate

    return best  # type: ignore[return-value]


def independent(primary: Transcript, others: Iterable[Transcript]) -> List[Transcript]:
    """Only transcripts from another family. A fine-tune is not a witness."""
    return [t for t in others if t.family != primary.family]


def report(agreements: Sequence[Agreement]) -> Dict[str, object]:
    """Coverage first, then the breakdown -- METHODE.md §5.

    The share of statements a layer refuses to let through is read BEFORE any
    accuracy claim, because a layer that lets nothing through is trivially
    never wrong.
    """
    total = len(agreements) or 1
    counts: Dict[str, int] = {}
    for agreement in agreements:
        counts[agreement.status.value] = counts.get(agreement.status.value, 0) + 1

    with_figures = [a for a in agreements if a.status is not Status.NO_QUANTITY]
    confirmed = counts.get(Status.CONFIRMED.value, 0)

    return {
        "statements": len(agreements),
        "with_figures": len(with_figures),
        "corroborated": confirmed,
        "corroborated_share": round(confirmed / max(len(with_figures), 1), 3),
        "blocked_share": round(
            (len(with_figures) - confirmed) / max(len(with_figures), 1), 3),
        "by_status": dict(sorted(counts.items(), key=lambda kv: -kv[1])),
    }
