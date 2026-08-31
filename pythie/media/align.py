"""Align transcript text with speaker turns.

Subtitles give TEXT + TIME but no speaker. Diarisation gives SPEAKER + TIME but
no text. Both live on the same timeline, so the merge is an interval join --
and it means we never have to re-transcribe material that already has captions.

Where the two disagree, the conservative reading wins: a caption spanning two
speakers is split, and a caption whose speaker was not identified stays
unattributed rather than being assigned to whoever spoke nearby.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from .audio import Turn
from .voiceprint import ANALYSED_ROLES, UNKNOWN


@dataclass
class Caption:
    """A timed text segment, from subtitles or ASR."""

    start: float
    end: float
    text: str


@dataclass
class Block:
    """What the analysis pipeline consumes: one speaking turn, with text."""

    start: float
    end: float
    speaker: str
    text: str
    role: str = ""
    identified: bool = True
    similarity: float = 0.0
    analysed: bool = True
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "debut": self.start,
            "fin": self.end,
            "locuteur": self.speaker,
            "texte": self.text,
            "role": self.role,
            "identifie": self.identified,
            "similarite": round(self.similarity, 3),
            "analyse": self.analysed,
            "note": self.note,
        }


def _overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))


def assign_speakers(
    captions: Sequence[Caption],
    turns: Sequence[Turn],
    min_share: float = 0.5,
) -> List[Tuple[Caption, Optional[Turn]]]:
    """Attach each caption to the turn it mostly falls inside.

    `min_share` is the fraction of the caption that must sit inside one turn.
    Below it, the caption straddles a speaker change and we refuse to pick:
    attributing half a sentence to the wrong person fabricates a quote.
    """
    pairs: List[Tuple[Caption, Optional[Turn]]] = []
    for caption in captions:
        span = max(caption.end - caption.start, 1e-6)
        best_turn: Optional[Turn] = None
        best_share = 0.0
        for turn in turns:
            share = _overlap(caption.start, caption.end, turn.start, turn.end) / span
            if share > best_share:
                best_share, best_turn = share, turn
        pairs.append((caption, best_turn if best_share >= min_share else None))
    return pairs


def build_blocks(
    captions: Sequence[Caption],
    turns: Sequence[Turn],
    *,
    min_share: float = 0.5,
) -> List[Block]:
    """Merge captions and turns into the blocks the pipeline analyses.

    Consecutive captions from the same speaker are joined into one block, so
    the reader gets paragraphs rather than subtitle fragments.
    """
    blocks: List[Block] = []
    current: Optional[Block] = None

    for caption, turn in assign_speakers(captions, turns, min_share):
        if turn is None or not turn.accepted:
            speaker, role, identified = UNKNOWN, "", False
            similarity = turn.similarity if turn else 0.0
            note = (
                turn.reason if turn
                else "aucun tour de parole ne couvre ce passage"
            )
        else:
            speaker, role, identified = turn.display_name, turn.role, True
            similarity, note = turn.similarity, ""

        # Only candidates are fact-checked, and only when positively
        # identified. A statement nobody can be shown to have made is judged
        # against nobody -- same reflex as "no source -> abstention".
        analysed = identified and role in ANALYSED_ROLES

        if current and current.speaker == speaker and current.role == role:
            current.end = caption.end
            current.text = f"{current.text} {caption.text}".strip()
            current.similarity = max(current.similarity, similarity)
        else:
            current = Block(
                start=caption.start,
                end=caption.end,
                speaker=speaker,
                text=caption.text.strip(),
                role=role,
                identified=identified,
                similarity=similarity,
                analysed=analysed,
                note=note,
            )
            blocks.append(current)

    return blocks


def coverage_report(blocks: Sequence[Block]) -> Dict[str, object]:
    """Diarisation quality, measured in seconds of speech.

    The number that matters is the unattributed share: it is the honest cost of
    refusing to guess, and it must be visible rather than hidden. A run with a
    high share is not broken -- it is telling you the enrolment is too thin.
    """
    total = sum(b.end - b.start for b in blocks) or 1e-6
    unattributed = sum(b.end - b.start for b in blocks if not b.identified)
    identified_not_analysed = sum(
        b.end - b.start for b in blocks if b.identified and not b.analysed
    )

    per_speaker: Dict[str, float] = {}
    for block in blocks:
        per_speaker[block.speaker] = per_speaker.get(block.speaker, 0.0) + (
            block.end - block.start
        )

    return {
        "total_seconds": round(total, 1),
        "unattributed_seconds": round(unattributed, 1),
        "unattributed_share": round(unattributed / total, 3),
        "identified_not_candidate_seconds": round(identified_not_analysed, 1),
        "analysed_seconds": round(total - unattributed - identified_not_analysed, 1),
        "per_speaker": {k: round(v, 1) for k, v in
                        sorted(per_speaker.items(), key=lambda kv: -kv[1])},
    }
