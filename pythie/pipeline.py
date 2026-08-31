"""Stage orchestration.

  0.  triggers      regex, zero cost, auditable            triggers.py
  1.  triage        short model call, early exit           (model)
  2.  verification  model + closed local base              verify.py
  3.  rendering     two-degree HTML + JSON                 render.py

An early-exit funnel: a model call is only paid for what cleared the previous
stage. Degree 1 stops after stage 2 on triggered spans only; degree 2 replays
the whole thing with a full sweep.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from . import triggers as trig
from .backend import LocalBackend
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
) -> tuple[List[Statement], Stats]:
    """Run the statements through the stages and fill the statistics.

    Sequential on purpose: a single local model serves one request at a time,
    so parallelism would only queue.
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

        stats.verified += 1
        stats.by_verdict[result.verdict.value] = (
            stats.by_verdict.get(result.verdict.value, 0) + 1
        )
        stats.unverified_quotes += sum(1 for s in result.sources if not s.quote_verified)

    # Anything untouched stays unmarked.
    for statement in statements:
        if statement.verdict is None:
            statement.verdict = Verdict.OUT_OF_SCOPE

    return statements, stats
