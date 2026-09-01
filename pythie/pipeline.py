"""Stage orchestration.

  0.  triggers      regex, zero cost, auditable            triggers.py
  0.5 agreement     figure heard twice, or not judged      media/transcripts.py
  1.  triage        short model call, early exit           (model)
  2.  verification  model + closed local base              verify.py
  3.  rendering     two-degree HTML + JSON                 render.py

An early-exit funnel: a model call is only paid for what cleared the previous
stage. Degree 1 stops after stage 2 on triggered spans only; degree 2 replays
the whole thing with a full sweep.

Stage 0.5 sits where it does for a reason: an uncorroborated figure must be
stopped BEFORE it costs a model call, and above all before it can come back
wearing a verdict. It is the cheapest stage and the one that matters most.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional, Sequence

from . import triggers as trig
from .backend import LocalBackend
from .media import transcripts
from .retrieval import LocalBase
from .schema import Category, Statement, TriageResult, Verdict
from .verify import verify

# Sentence split approximates the claim span. Good enough for a proof of
# concept; the right unit is the span itself, which may be a fragment or cross
# two sentences.
SENTENCE_END = re.compile(r"(?<=[.!?…])\s+(?=[A-ZÀÉÈÊÎÔÙ])")

TRIAGE_SYSTEM = """\
Tu tries des énoncés extraits d'un débat politique français. Tu ne vérifies rien
à ce stade : tu décides seulement si l'énoncé MÉRITE une vérification.

OBJECTIF DE L'OUTIL : déterminer qui énonce du vrai, du faux, ou de
l'approximatif. Rien d'autre. Pas d'analyse rhétorique, pas de qualification
des procédés, aucune mesure d'intention.

Conséquence : les emphases, figures de style, attaques personnelles et effets de
tribune ne sont PAS pris en compte. Ils sortent en `rhetoric` et ne sont jamais
marqués. Exception unique : si une figure contient une valeur testable — « on a
dépensé quarante milliards dans ce gouffre » — la valeur est retenue et la
figure ignorée.

CATÉGORIES
- fact      : affirmation sur le passé ou le présent, testable contre une source
              statistique ou juridique primaire
- pledge    : promesse ou intention. NI VRAIE NI FAUSSE — sort de l'échelle de
              vérité, sera confrontée au programme publié
- opinion   : jugement de valeur, non vérifiable par nature
- rhetoric  : attaque, question, formule, interpellation
- trivial   : exact mais sans enjeu informationnel

`relevant` est vrai UNIQUEMENT si category == "fact" ET que l'énoncé est
testable en l'état contre une source primaire.

`invoked_measure` : nomme la mesure EXACTE dont parle le locuteur, avec son
unité — « effectif de demandeurs d'emploi en catégorie A », jamais « chômage ».
Cette précision sert à détecter les confusions de définition.
"""


class Strictness(str, Enum):
    """How much the agreement layer is allowed to stop.

    `REDS` is the floor, not a setting to choose lightly: a green also quotes
    the speaker, and quoting a sentence nobody said is the same fabrication
    whatever colour it wears. It exists because a red is the one verdict that
    accuses, and because forbidding reds outright (D-044) was until now a rule
    kept by discipline rather than by the program.
    """

    STRICT = "strict"   # no coloured verdict on an uncorroborated figure
    REDS = "rouges"     # verify anyway, but never publish a red


def gate(
    statements: Sequence[Statement],
    spans: Dict[str, tuple[float, float]],
    witnesses: Sequence["transcripts.Transcript"],
    *,
    strictness: Strictness = Strictness.STRICT,
    settings: Optional["transcripts.Settings"] = None,
) -> tuple[List[Statement], Dict[str, "transcripts.Agreement"]]:
    """Stage 0.5. Split the candidates into those a second transcription heard
    and those it did not.

    Returns the statements that may proceed, and the agreement found for every
    statement examined -- including the ones that passed, because a corroborated
    verdict must be able to name the witness that corroborated it.

    Statements stopped here are marked `unverified` and carry the reason in
    their own words: this is a defect of OUR measurement chain, never a
    refutation of the speaker, and the page must say so.
    """
    allowed: List[Statement] = []
    found: Dict[str, transcripts.Agreement] = {}

    for statement in statements:
        start, end = spans.get(statement.id, (statement.timestamp or 0.0,
                                              statement.timestamp or 0.0))
        agreement = transcripts.corroborate(
            statement.text, start, end, witnesses, settings
        )
        found[statement.id] = agreement

        blocked = (
            strictness is Strictness.STRICT
            and agreement.status is not transcripts.Status.CONFIRMED
            and agreement.status is not transcripts.Status.NO_QUANTITY
        )
        if blocked:
            statement.verdict = Verdict.UNVERIFIED
            statement.confidence = 0.0
            statement.context_note = agreement.note()
        else:
            allowed.append(statement)

    return allowed, found


# D-044 is not lifted. The agreement layer exists and measures, but the
# pre-registered bench of 01/09 did NOT validate it: `ETUDES/banc_accord.py`
# found no setting satisfying the criteria written before the measurement, so
# by the decision rule published in `ETUDES/preinscription-accord.md` the layer
# is not authorised to unlock anything. Corroboration is reported; it does not
# grant permission. Lifting this requires a bench that passes, not a flag
# flipped because the layer now exists.
REDS_UNLOCKED_BY_AGREEMENT = False


def guard_red(
    statement: Statement,
    agreement: Optional["transcripts.Agreement"],
    *,
    unlock: bool = REDS_UNLOCKED_BY_AGREEMENT,
) -> bool:
    """Last line: no red is published.

    Applied AFTER verification, whatever the strictness and whatever the
    caller did, so that a red cannot reach the page through a path that forgot
    to gate. D-044 stops being a rule someone has to remember and becomes a
    property of the program.

    `unlock=True` lets a corroborated figure carry a red. It is off, and stays
    off until a pre-registered bench says the corroboration is worth that
    permission -- the one on 01/09 did not.
    """
    if statement.verdict is not Verdict.FALSE:
        return False
    if unlock and agreement is not None and agreement.corroborated:
        return False

    note = (
        "D-044 : aucun rouge n'est publie tant que la couche d'accord entre "
        "transcriptions n'a pas ete validee par un banc pre-inscrit."
        if not unlock else
        (agreement.note() if agreement else
         "Aucune transcription independante : le chiffre n'est corrobore par "
         "aucune seconde source.")
    )
    statement.verdict = Verdict.UNVERIFIED
    statement.confidence = min(statement.confidence or 0.0, 0.3)
    statement.context_note = (
        f"{statement.context_note or ''} (Rouge retire : {note})".strip()
    )
    return True


@dataclass
class Stats:
    """The numbers to look at first on a proof of concept."""

    statements: int = 0
    triggered: int = 0
    relevant: int = 0
    verified: int = 0
    by_verdict: Dict[str, int] = field(default_factory=dict)
    by_category: Dict[str, int] = field(default_factory=dict)
    unverified_quotes: int = 0

    def abstention_rate(self) -> float:
        if not self.verified:
            return 0.0
        return self.by_verdict.get(Verdict.UNVERIFIED.value, 0) / self.verified

    def reds(self) -> int:
        return self.by_verdict.get(Verdict.FALSE.value, 0)


def split(
    text: str, speaker: str, start_time: float = 0.0, duration: float = 0.0
) -> List[Statement]:
    """Split a speaking turn into statements, timestamped by interpolation."""
    sentences = [s.strip() for s in SENTENCE_END.split(text) if s.strip()]
    if not sentences:
        return []

    total = sum(len(s) for s in sentences) or 1
    statements: List[Statement] = []
    cursor = 0
    elapsed = 0.0

    for index, sentence in enumerate(sentences):
        elapsed += (len(sentence) / total) * duration
        offset = text.find(sentence, cursor)
        cursor = offset + len(sentence) if offset >= 0 else cursor
        statements.append(
            Statement(
                id=f"{speaker[:3].lower()}-{start_time:.0f}-{index}",
                speaker=speaker,
                text=sentence,
                start=max(offset, 0),
                end=max(offset, 0) + len(sentence),
                timestamp=start_time + elapsed,
                triggers=trig.detect(sentence),
            )
        )
    return statements


def analyze(
    statements: List[Statement],
    base: LocalBase,
    *,
    backend: Optional[LocalBackend] = None,
    degree: int = 2,
    on_progress: Optional[Callable[[str], None]] = None,
    witnesses: Sequence["transcripts.Transcript"] = (),
    spans: Optional[Dict[str, tuple[float, float]]] = None,
    strictness: Strictness = Strictness.STRICT,
) -> tuple[List[Statement], Stats]:
    """Run the statements through the stages and fill the statistics.

    Sequential on purpose: a single local model serves one request at a time,
    so parallelism would only queue.

    `witnesses` are independent transcriptions of the same audio. With none,
    every figure is uncorroborated and no red is published -- D-044 holds here
    too, by default and without the caller having to remember it. That is why
    the guard runs on both entry points rather than in the runner script.
    """
    backend = backend or LocalBackend()
    stats = Stats(statements=len(statements))
    log = on_progress or (lambda _m: None)

    # --- stage 0: deterministic filter ------------------------------------
    if degree == 1:
        candidates = [s for s in statements if trig.deserves_verification(s.triggers)]
    else:
        candidates = [s for s in statements if s.triggers or len(s.text) > 40]

    stats.triggered = len(candidates)
    log(f"stage 0 -- {len(candidates)}/{len(statements)} statements triggered")

    # --- stage 0.5: agreement between transcriptions ----------------------
    candidates, agreements = gate(
        candidates, spans or {}, witnesses, strictness=strictness
    )
    if witnesses:
        summary = transcripts.report(list(agreements.values()))
        log(f"stage 0.5 -- {summary['corroborated']}/{summary['with_figures']} "
            f"figures corroborated, {summary['blocked_share']:.0%} stopped")
    else:
        log("stage 0.5 -- no witness transcription: no figure is corroborated, "
            "no red will be published")

    # --- stage 1: triage ---------------------------------------------------
    measures: Dict[str, Optional[str]] = {}
    for statement in candidates:
        try:
            reply = backend.json_struct(
                system=TRIAGE_SYSTEM,
                message=f"Locuteur : {statement.speaker}\nEnonce : « {statement.text} »",
                schema=TriageResult,
                max_tokens=1536,
            )
            if not reply.data:
                log(f"  triage output invalid (truncated={reply.truncated})")
                continue
            triage = TriageResult.model_validate(reply.data)
        except Exception as error:  # one failure must not stop the batch
            log(f"  triage failed: {error}")
            continue

        statement.category = triage.category
        statement.relevant = triage.relevant
        statement.rejection_reason = None if triage.relevant else triage.reason
        measures[statement.id] = triage.invoked_measure
        stats.by_category[triage.category.value] = (
            stats.by_category.get(triage.category.value, 0) + 1
        )
        if not triage.relevant and triage.category != Category.PLEDGE:
            statement.verdict = Verdict.OUT_OF_SCOPE

    to_verify = [s for s in candidates if s.relevant]
    pledges = [s for s in candidates if s.category == Category.PLEDGE]
    stats.relevant = len(to_verify)
    log(f"stage 1 -- {len(to_verify)} to verify, {len(pledges)} pledges")

    # --- stage 2: verification --------------------------------------------
    for statement in to_verify:
        statement.verdict = Verdict.PENDING

    for statement in to_verify:
        try:
            result = verify(backend, base, statement)
        except Exception as error:
            log(f"  verification failed: {error}")
            statement.verdict = Verdict.UNVERIFIED
            continue

        statement.verdict = result.verdict
        statement.confidence = result.confidence
        statement.tags = result.tags
        statement.sources = result.sources
        statement.context_note = result.context_note
        statement.stated_value = result.stated_value
        statement.source_value = result.source_value
        statement.relative_gap = result.relative_gap

        # Last line, whatever the strictness and whatever the caller did.
        guard_red(statement, agreements.get(statement.id))

        stats.verified += 1
        stats.by_verdict[statement.verdict.value] = (
            stats.by_verdict.get(statement.verdict.value, 0) + 1
        )
        stats.unverified_quotes += sum(1 for s in result.sources if not s.quote_verified)

    # Anything untouched stays unmarked.
    for statement in statements:
        if statement.verdict is None:
            statement.verdict = Verdict.OUT_OF_SCOPE

    return statements, stats
