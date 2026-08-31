"""Voice prints: closed-set speaker identification.

THE REFRAMING
-------------
This is not open-set diarisation. We know who is on the panel. Candidates are a
finite, published list; moderators and journalists recur from one broadcast to
the next. Every one of them can be enrolled in advance from recorded material
that the candidate dossiers already reference.

So we do not discover how many speakers there are and cluster blindly. We embed
each segment and match it against enrolled prints. Unsupervised clustering
becomes nearest-neighbour lookup with a rejection threshold.

THE GOVERNING RULE
------------------
A WRONG ATTRIBUTION IS WORSE THAN NO ATTRIBUTION.

Attributing a false claim to the wrong candidate is not a wrong verdict, it is
a fabricated quote -- the worst output this system can produce. Below the
similarity threshold we return UNKNOWN and the statement is attributed to
nobody, therefore judged against nobody.

Same reflex as "no source -> abstention", applied to the voice.
"""

from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent
PRINTS_DIR = ROOT / "corpus" / "voiceprints"

UNKNOWN = "locuteur non identifie"

# Cosine similarity below which we refuse to name anyone.
# Deliberately conservative: the cost of a wrong name is far higher than the
# cost of an unattributed sentence.
ACCEPT_THRESHOLD = 0.62

# If the best two candidates are this close, the choice is not decisive.
# Two similar voices must produce an abstention, not a coin flip.
MARGIN_THRESHOLD = 0.06


class Role:
    CANDIDATE = "candidate"
    MODERATOR = "moderator"
    JOURNALIST = "journalist"
    OTHER = "other"


# Roles whose speech is not fact-checked. A moderator's question is not a claim
# by the panel; a journalist's framing is not a candidate's assertion.
NOT_ANALYSED = {Role.MODERATOR, Role.JOURNALIST}


def _slug(name: str) -> str:
    flat = unicodedata.normalize("NFKD", name)
    flat = "".join(c for c in flat if not unicodedata.combining(c)).lower()
    return "".join(c if c.isalnum() else "-" for c in flat).strip("-")


def normalise(vector: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vector)
    return vector / norm if norm else vector


@dataclass
class VoicePrint:
    """One enrolled speaker.

    `centroid` is the mean of several enrolment embeddings: one recording is
    never enough, because a single clip carries its own channel and its own
    acoustics rather than the voice.
    """

    speaker_id: str
    display_name: str
    role: str
    centroid: np.ndarray
    sample_count: int = 0
    total_seconds: float = 0.0
    sources: List[str] = field(default_factory=list)
    enrolled_on: str = ""

    @property
    def analysed(self) -> bool:
        return self.role not in NOT_ANALYSED

    def to_dict(self) -> dict:
        return {
            "speaker_id": self.speaker_id,
            "display_name": self.display_name,
            "role": self.role,
            "centroid": self.centroid.astype(float).tolist(),
            "sample_count": self.sample_count,
            "total_seconds": round(self.total_seconds, 1),
            "sources": self.sources,
            "enrolled_on": self.enrolled_on,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VoicePrint":
        return cls(
            speaker_id=data["speaker_id"],
            display_name=data["display_name"],
            role=data.get("role", Role.OTHER),
            centroid=normalise(np.asarray(data["centroid"], dtype=np.float32)),
            sample_count=data.get("sample_count", 0),
            total_seconds=data.get("total_seconds", 0.0),
            sources=data.get("sources", []),
            enrolled_on=data.get("enrolled_on", ""),
        )


@dataclass
class Identification:
    """The outcome of matching one segment. Always carries its own evidence."""

    speaker_id: str
    display_name: str
    role: str
    similarity: float
    margin: float
    accepted: bool
    reason: str

    @property
    def analysed(self) -> bool:
        return self.accepted and self.role not in NOT_ANALYSED


class Registry:
    """The enrolled panel. Loaded before a debate, never modified during one."""

    def __init__(self, prints: Optional[Dict[str, VoicePrint]] = None):
        self.prints: Dict[str, VoicePrint] = prints or {}

    # -- persistence -------------------------------------------------------

    @classmethod
    def load(cls, directory: Path | str = PRINTS_DIR) -> "Registry":
        directory = Path(directory)
        prints: Dict[str, VoicePrint] = {}
        if directory.is_dir():
            for path in sorted(directory.glob("*.json")):
                data = json.loads(path.read_text(encoding="utf-8"))
                voice_print = VoicePrint.from_dict(data)
                prints[voice_print.speaker_id] = voice_print
        return cls(prints)

    def save(self, directory: Path | str = PRINTS_DIR) -> None:
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        for voice_print in self.prints.values():
            (directory / f"{voice_print.speaker_id}.json").write_text(
                json.dumps(voice_print.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    # -- enrolment ---------------------------------------------------------

    def enrol(
        self,
        display_name: str,
        role: str,
        embeddings: Sequence[np.ndarray],
        *,
        seconds: float = 0.0,
        sources: Optional[List[str]] = None,
        enrolled_on: str = "",
    ) -> VoicePrint:
        """Build a print from several enrolment embeddings.

        Raises when given too little material: a print built on one short clip
        matches the recording, not the person, and would produce confident
        wrong attributions -- the exact failure this module exists to avoid.
        """
        if len(embeddings) < 3:
            raise ValueError(
                f"{display_name}: {len(embeddings)} embedding(s) supplied, at "
                "least 3 required. A print built on too little material "
                "captures the channel, not the voice."
            )

        stacked = np.stack([normalise(np.asarray(e, dtype=np.float32)) for e in embeddings])
        voice_print = VoicePrint(
            speaker_id=_slug(display_name),
            display_name=display_name,
            role=role,
            centroid=normalise(stacked.mean(axis=0)),
            sample_count=len(embeddings),
            total_seconds=seconds,
            sources=sources or [],
            enrolled_on=enrolled_on,
        )
        self.prints[voice_print.speaker_id] = voice_print
        return voice_print

    # -- identification ----------------------------------------------------

    def identify(
        self,
        embedding: np.ndarray,
        *,
        restrict_to: Optional[Sequence[str]] = None,
        threshold: float = ACCEPT_THRESHOLD,
        margin: float = MARGIN_THRESHOLD,
    ) -> Identification:
        """Match one segment against the enrolled panel.

        `restrict_to` narrows the search to who is actually on this panel,
        which is both faster and safer: a voice cannot be attributed to someone
        who is not in the room.
        """
        pool = [
            p for p in self.prints.values()
            if restrict_to is None or p.speaker_id in restrict_to
        ]
        if not pool:
            return Identification(
                UNKNOWN, UNKNOWN, Role.OTHER, 0.0, 0.0, False,
                "aucune empreinte enrolee pour ce plateau",
            )

        query = normalise(np.asarray(embedding, dtype=np.float32))
        scores = sorted(
            ((float(query @ p.centroid), p) for p in pool),
            key=lambda pair: pair[0],
            reverse=True,
        )
        best_score, best = scores[0]
        runner_up = scores[1][0] if len(scores) > 1 else 0.0
        gap = best_score - runner_up

        if best_score < threshold:
            return Identification(
                UNKNOWN, UNKNOWN, Role.OTHER, best_score, gap, False,
                f"similarite {best_score:.2f} sous le seuil {threshold:.2f}",
            )

        if len(scores) > 1 and gap < margin:
            # Two enrolled voices are equally close. Naming one would be a
            # coin flip, and a coin flip that fabricates a quote.
            return Identification(
                UNKNOWN, UNKNOWN, Role.OTHER, best_score, gap, False,
                f"choix non decisif entre {best.display_name} et "
                f"{scores[1][1].display_name} (marge {gap:.2f})",
            )

        return Identification(
            best.speaker_id, best.display_name, best.role,
            best_score, gap, True,
            f"similarite {best_score:.2f}, marge {gap:.2f}",
        )


def identify_overlapped() -> Identification:
    """Overlapping speech is never attributed.

    French political debates are saturated with crosstalk, and an embedding
    computed over two mixed voices resembles neither. The passage stays on
    screen with no speaker, hence no verdict imputed to anyone.
    """
    return Identification(
        UNKNOWN, UNKNOWN, Role.OTHER, 0.0, 0.0, False,
        "paroles superposees -- non attribue",
    )
