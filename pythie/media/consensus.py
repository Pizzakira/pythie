"""Two diarisers, one decision.

The two available approaches answer different questions and neither replaces
the other:

  - a segmentation model (pyannote) knows WHERE the speaker changes and WHERE
    voices overlap, but only ever returns anonymous labels (SPEAKER_00);
  - voice prints know WHO a stretch belongs to, but cannot see overlap.

So we run both on the same audio and combine them. Compute is not a constraint
here, and the second pass buys something the first cannot provide.

THE COMBINATION RULE
--------------------
Agreement attributes. Disagreement abstains.

This is not a vote. When the two layers disagree about a stretch, the honest
reading is that we do not know who spoke -- and under this project's governing
rule, a wrong attribution is worse than no attribution, because it fabricates a
quote rather than merely misjudging one. Disagreement is information, and its
safe interpretation is silence.

Overlap detected by the segmentation layer abstains outright: an embedding
computed over two mixed voices resembles neither, so identity is meaningless
there however confident the match looks.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from .audio import Turn
from .voiceprint import UNKNOWN, Identification, Registry, Role


@dataclass
class Segment:
    """A stretch produced by the segmentation layer, still anonymous."""

    start: float
    end: float
    label: str                 # SPEAKER_00, SPEAKER_01, ...
    overlapped: bool = False

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass
class Decision:
    """The combined outcome for one stretch, carrying its own justification."""

    start: float
    end: float
    speaker_id: str
    display_name: str
    role: str
    accepted: bool
    reason: str
    similarity: float = 0.0
    agreement: bool = False

    def to_turn(self) -> Turn:
        return Turn(
            start=self.start,
            end=self.end,
            speaker_id=self.speaker_id,
            display_name=self.display_name,
            role=self.role,
            similarity=self.similarity,
            accepted=self.accepted,
            reason=self.reason,
        )


def _abstain(segment: Segment, reason: str, similarity: float = 0.0) -> Decision:
    return Decision(
        start=segment.start,
        end=segment.end,
        speaker_id=UNKNOWN,
        display_name=UNKNOWN,
        role=Role.OTHER,
        accepted=False,
        reason=reason,
        similarity=similarity,
    )


def majority_identity(
    identifications: Sequence[Identification],
) -> Tuple[Optional[str], float, float]:
    """Which enrolled speaker dominates a set of per-window identifications.

    Returns (speaker_id, share, mean similarity). A stretch is only named when
    one identity accounts for most of its accepted windows; a stretch split
    between two names is a stretch we do not understand.
    """
    accepted = [i for i in identifications if i.accepted]
    if not accepted:
        return None, 0.0, 0.0

    counts: Dict[str, List[float]] = {}
    for identification in accepted:
        counts.setdefault(identification.speaker_id, []).append(identification.similarity)

    speaker_id, scores = max(counts.items(), key=lambda kv: len(kv[1]))
    share = len(scores) / len(accepted)
    return speaker_id, share, sum(scores) / len(scores)


def combine(
    segments: Sequence[Segment],
    windows: Dict[int, List[Identification]],
    registry: Registry,
    *,
    # 0.75 rather than a bare majority: one dissenting window out of three is
    # already disagreement, and under this project's rule disagreement abstains.
    # 2-of-3 (67%) abstains; 3-of-3 and 4-of-5 (80%) attribute.
    min_share: float = 0.75,
    min_windows: int = 2,
) -> List[Decision]:
    """Merge segmentation and identification into final speaker turns.

    `windows` maps a segment index to the identifications computed over short
    windows inside it. Several windows per segment matter: one window can be
    corrupted by a cough, a laugh or a passing overlap, and requiring a majority
    across windows filters that out without inventing anything.
    """
    decisions: List[Decision] = []

    for index, segment in enumerate(segments):
        # 1. Overlap short-circuits everything. Identity over mixed voices is
        #    meaningless regardless of how confident the match looks.
        if segment.overlapped:
            decisions.append(_abstain(segment, "paroles superposees -- non attribue"))
            continue

        identifications = windows.get(index, [])
        if len(identifications) < min_windows:
            decisions.append(
                _abstain(
                    segment,
                    f"{len(identifications)} fenetre(s) analysee(s), {min_windows} requises",
                )
            )
            continue

        speaker_id, share, similarity = majority_identity(identifications)

        # 2. No window cleared the acceptance threshold.
        if speaker_id is None:
            best = max((i.similarity for i in identifications), default=0.0)
            decisions.append(
                _abstain(segment, f"aucune empreinte au-dessus du seuil (max {best:.2f})", best)
            )
            continue

        # 3. The segment is split between two enrolled voices. The segmentation
        #    layer says one speaker, the identification layer says two: they
        #    disagree, so we abstain instead of picking the larger half.
        if share < min_share:
            decisions.append(
                _abstain(
                    segment,
                    f"desaccord entre segmentation et identification "
                    f"(identite dominante a {share:.0%})",
                    similarity,
                )
            )
            continue

        voice_print = registry.prints.get(speaker_id)
        if voice_print is None:
            decisions.append(_abstain(segment, f"empreinte {speaker_id} introuvable"))
            continue

        decisions.append(
            Decision(
                start=segment.start,
                end=segment.end,
                speaker_id=speaker_id,
                display_name=voice_print.display_name,
                role=voice_print.role,
                accepted=True,
                reason=f"accord des deux couches ({share:.0%} des fenetres, sim {similarity:.2f})",
                similarity=similarity,
                agreement=True,
            )
        )

    return decisions


def agreement_report(decisions: Sequence[Decision]) -> Dict[str, object]:
    """What the two layers cost and bought, in seconds.

    The abstention breakdown is the useful part: it says whether to enrol more
    material, tune the threshold, or accept that a debate was simply too noisy.
    """
    total = sum(d.end - d.start for d in decisions) or 1e-6
    attributed = sum(d.end - d.start for d in decisions if d.accepted)

    by_reason: Dict[str, float] = {}
    for decision in decisions:
        if decision.accepted:
            continue
        key = decision.reason.split("(")[0].strip()
        by_reason[key] = by_reason.get(key, 0.0) + (decision.end - decision.start)

    return {
        "total_seconds": round(total, 1),
        "attributed_seconds": round(attributed, 1),
        "attributed_share": round(attributed / total, 3),
        "abstentions_by_reason": {k: round(v, 1) for k, v in
                                  sorted(by_reason.items(), key=lambda kv: -kv[1])},
    }
