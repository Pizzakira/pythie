"""Stage 2 -- verification against the local pyramid.

Two model calls, matching the two descents of the pyramid:

  1. ROUTING -- show the index and briefs; the model says which domain and
                which sources to open. It judges nothing yet.
  2. VERDICT -- hand it the chosen primary sources; it compares.
                It does not search: it sees only what we give it.

Then the guardrails, applied by the program and never by the model:
  - the quote must come from a primary source (never from a brief)
  - a verdict cannot exceed the rank of its source
  - numeric thresholds are applied mechanically
  - no source means abstention, never a fallback verdict

Prompts are in French because the analysed material is French; identifiers and
comments stay English per project convention.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from .backend import LocalBackend
from .numbers import Kind, quantities
from .retrieval import LocalBase, context_for_verification, validate_provenance
from .schema import (
    APPROXIMATE_POINTS,
    APPROXIMATE_THRESHOLD,
    EXACT_POINTS,
    EXACT_THRESHOLD,
    Source,
    Statement,
    Tag,
    Verdict,
    VerificationResult,
)


class Routing(BaseModel):
    """Step 1 output -- where to look. No judgement yet."""

    domain: str = Field(description="Exact domain name, or '' if none fits.")
    sources: List[str] = Field(
        default_factory=list,
        description="Exact keys of the primary sources to open. At most two.",
    )
    invoked_measure: str = Field(
        description="The exact quantity the speaker refers to, with its unit."
    )
    reason: str = Field(description="One sentence.")


ROUTING_SYSTEM = """\
Tu orientes une vérification dans une base documentaire locale. Tu ne vérifies
rien à ce stade : tu désignes seulement où regarder.

Les fiches qu'on te montre servent à t'orienter. Elles ne prouvent rien et tu
ne dois jamais les citer comme preuve.

Point décisif : identifie si le locuteur invoque un TAUX (un pourcentage) ou un
EFFECTIF (un nombre de personnes). Ce sont deux grandeurs différentes, produites
par des organismes différents ; les confondre produit un verdict faux sur un
énoncé vrai.

Choisis au plus deux sources. Si aucun domaine ne convient, renvoie un domaine
vide et une liste de sources vide.
"""

VERDICT_SYSTEM = """\
Tu compares une valeur énoncée dans un débat politique à la valeur publiée par
une source primaire qu'on te fournit.

RÈGLE QUI PRIME SUR TOUTES LES AUTRES
Tes paramètres ne sont pas une source. Aucun chiffre ne peut venir de ce que tu
« sais ». Tu ne disposes QUE des extraits ci-dessous. S'ils ne permettent pas de
trancher, le verdict est `unverified`. Il n'existe aucun verdict de repli.

CE QUE TU NE FAIS PAS
Tu n'analyses pas la rhétorique, tu ne qualifies aucun procédé de discours, tu
ne mesures aucune intention. Un énoncé rigoureusement vrai est `exact`, même
s'il est incomplet ou orienté. Tu compares une valeur à une valeur.

VERDICTS
- exact                : la valeur correspond
- approximate          : bon ordre de grandeur et bon sens, mais s'écarte
- false                : contredite par la source
- too_vague            : l'énoncé n'est pas testable en l'état
- conflicting_sources  : définitions incompatibles, pas une faute du locuteur
- unverified           : les extraits ne permettent pas de trancher

NE DÉCIDE PAS DU SEUIL. Renseigne `stated_value`, `source_value` et
`relative_gap` (fraction : 0.107 pour 10,7 %). Le programme tranche selon des
seuils publiés.

VÉRIFIE LA GRANDEUR. Si le locuteur invoque un effectif et que la source donne
un taux — ou l'inverse — ne compare pas : pose `incomparable_definition` et
explique. Un taux BIT et un effectif de catégorie A ne se comparent jamais.

CITATION — POINT CRITIQUE
`quote` doit être une suite de mots RECOPIÉE CARACTÈRE POUR CARACTÈRE depuis un
extrait fourni. Choisis un fragment COURT (moins de 120 caractères) contenant le
chiffre. Ne reformule pas, ne reconstitue pas, ne complète pas. La chaîne sera
recherchée littéralement dans le document : si elle ne s'y trouve pas mot pour
mot, le verdict est annulé.

`context_note` : une à deux phrases factuelles — ce que dit la source et à
quelle date. Aucun commentaire sur le locuteur.
"""


def measured_gap(result: VerificationResult) -> Optional[tuple[float, str]]:
    """The gap between what was said and what the source publishes, in the
    unit that makes it meaningful.

    A percentage is compared IN POINTS, never relatively. Measured on 31/08:
    "45,3 % de prelevements" against an INSEE 43,6 % is a relative gap of
    3,4 %, which clears the 5 % bar and returns `exact` -- while being 1,7
    point of GDP, some fifty billion euros (D-039). The relative framing
    flattens exactly the error that matters.

    The point rule needs both values to be readable AS percentages. When the
    model reports a bare "45,3" we cannot tell a rate from a headcount, so we
    fall back on the relative gap it computed -- and the fallback is reported
    rather than silent, because it is the case where the published thresholds
    are known to be too generous.
    """
    stated = quantities(result.stated_value or "")
    source = quantities(result.source_value or "")

    if (stated and source
            and stated[0].kind is Kind.PERCENT
            and source[0].kind is Kind.PERCENT):
        return abs(stated[0].value - source[0].value), "points"

    if result.relative_gap is not None:
        return abs(result.relative_gap), "relative"
    return None


def apply_thresholds(
    result: VerificationResult, rank: Optional[int]
) -> VerificationResult:
    """Translate a measured gap into a verdict, using published thresholds.

    THE MODEL IS THE JUDGE. It reads the evidence and returns the verdict.
    This function is a veto, not a second opinion: it may only WEAKEN what the
    model returned, never strengthen it.

    Concretely, the program never manufactures a red the model did not return.
    If the model answered `exact` while reporting a 40% gap, that is an internal
    inconsistency in its own output -- and the safe reading of an inconsistency
    is abstention, not accusation. A red is the single most consequential
    output of this system; it must be something a judge asserted, not something
    arithmetic produced from a figure the same judge supplied.

    Abstention states are never rewritten.
    """
    if result.verdict in (
        Verdict.UNVERIFIED,
        Verdict.TOO_VAGUE,
        Verdict.CONFLICTING_SOURCES,
        Verdict.OUT_OF_SCOPE,
    ):
        return result

    measured = measured_gap(result)
    if measured is None:
        return result

    gap, unit = measured
    if unit == "points":
        exact_bar, approximate_bar = EXACT_POINTS, APPROXIMATE_POINTS
        written = f"{gap:.2f} point{'s' if gap >= 2 else ''}".replace(".", ",")
    else:
        exact_bar, approximate_bar = EXACT_THRESHOLD, APPROXIMATE_THRESHOLD
        written = f"{gap:.0%}"

    if gap <= exact_bar:
        # Downgrading a red or an orange to exact is a weakening: allowed.
        result.verdict = Verdict.EXACT
        if Tag.APPROXIMATE_MAGNITUDE not in result.tags:
            result.tags.append(Tag.APPROXIMATE_MAGNITUDE)

    elif gap <= approximate_bar:
        # Red -> orange weakens; exact -> orange is the one upgrade the
        # published threshold justifies, and it stops short of an accusation.
        result.verdict = Verdict.APPROXIMATE

    else:
        # Past the threshold the model's own verdict decides.
        if result.verdict == Verdict.FALSE:
            # Only a rank 1 source may support a red; otherwise weaken.
            if rank != 1:
                result.verdict = Verdict.APPROXIMATE
        elif result.verdict == Verdict.EXACT:
            # "exact" with a 40% gap contradicts itself. Abstain.
            result.verdict = Verdict.UNVERIFIED
            result.confidence = min(result.confidence, 0.3)
            result.context_note += (
                " (Verdict retire : le modele rend « exact » tout en rapportant "
                f"un ecart de {written}. Incoherence interne, pas une refutation.)"
            )
        else:
            result.verdict = Verdict.APPROXIMATE

    if unit == "points":
        result.context_note += f" (Ecart mesure en points : {written}.)"

    return result


def _abstain(note: str, reasoning: str, confidence: float = 0.0) -> VerificationResult:
    return VerificationResult(
        verdict=Verdict.UNVERIFIED,
        confidence=confidence,
        context_note=note,
        reasoning=reasoning,
        # Explicit: an abstention cites nothing, and now says so rather than
        # relying on a default that no longer exists.
        sources=[],
    )


def verify(
    backend: LocalBackend,
    base: LocalBase,
    statement: Statement,
    trace: bool = False,
) -> VerificationResult:
    log = print if trace else (lambda *a, **k: None)

    # --- 1. routing -------------------------------------------------------
    reply = backend.json_struct(
        system=ROUTING_SYSTEM,
        message=(
            f"{base.summary()}\n\n"
            + "\n\n".join(base.orient(d) for d in base.domains)
            + f"\n\nEnonce a situer : « {statement.text} »"
        ),
        schema=Routing,
        max_tokens=2048,
    )
    if not reply.data:
        return _abstain(
            "Routage impossible.",
            f"routing output invalid (truncated={reply.truncated})",
        )

    routing = Routing.model_validate(reply.data)
    log(f"  routing: domain={routing.domain!r} sources={routing.sources}")
    log(f"           measure={routing.invoked_measure!r}")

    keys = [k for k in routing.sources if base.read(routing.domain, k)]
    if not keys:
        return _abstain(
            "Aucune source primaire correspondante dans la base locale.",
            f"routed to {routing.domain!r} with no usable source",
        )

    # --- 2. verdict -------------------------------------------------------
    context = context_for_verification(base, routing.domain, keys)
    reply = backend.json_struct(
        system=VERDICT_SYSTEM,
        message=(
            f"EXTRAITS FOURNIS (tu ne disposes de rien d'autre) :\n\n{context}\n\n"
            f"Grandeur invoquee par le locuteur : {routing.invoked_measure}\n"
            f"Enonce a verifier : « {statement.text} »"
        ),
        schema=VerificationResult,
        max_tokens=6144,
    )
    if not reply.data:
        return _abstain(
            "Sortie de verification non conforme au schema.",
            f"verdict output invalid (truncated={reply.truncated})",
        )

    result = VerificationResult.model_validate(reply.data)

    # --- 3. program guardrails -------------------------------------------
    kept: List[Source] = []
    for source in result.sources:
        ok, primary, reason = validate_provenance(source.quote, base, routing.domain)
        source.quote_verified = ok
        if ok and primary:
            source.url = primary.origin_url
            source.domain = primary.producer
            source.rank = primary.rank
            source.data_date = source.data_date or primary.vintage
            kept.append(source)
        else:
            log(f"  quote rejected - {reason}")
            log(f"    << {source.quote[:110]} >>")
    result.sources = kept

    if not kept:
        result.verdict = Verdict.UNVERIFIED
        result.confidence = min(result.confidence, 0.3)
        result.context_note = (
            "Aucune citation retrouvee litteralement dans une source primaire. "
            "Verdict retire par precaution."
        )
        return result

    rank = min(s.rank for s in kept)
    if result.verdict == Verdict.FALSE and rank != 1:
        result.verdict = Verdict.UNVERIFIED
        result.context_note += (
            f" (Verdict plafonne : rang {rank}, rang 1 exige pour un faux.)"
        )

    return apply_thresholds(result, rank)
