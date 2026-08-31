"""Pythie data models.

Two independent axes, never conflated:
  - VERDICT : does the stated value hold? (carries the colour)
  - TAGS    : what was the comparison made against? (factual qualifiers only)

CONFIDENCE is a third axis and is never encoded in the colour.

Scope note: this tool compares a stated value against a primary source. It does
not analyse rhetoric, does not qualify discursive devices, and never infers
intent. "False" means the statement does not match the source -- never that the
speaker lied.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class Category(str, Enum):
    """What the utterance IS. Decided at stage 1 (triage)."""

    FACT = "fact"              # claim about past/present -> checkable
    PLEDGE = "pledge"          # promise or intent -> OUTSIDE the truth scale
    OPINION = "opinion"        # value judgement -> not checkable by nature
    RHETORIC = "rhetoric"      # attack, question, figure of speech -> ignored
    TRIVIAL = "trivial"        # true but carries no informational stake


class Verdict(str, Enum):
    """Does the value hold? This alone carries the colour."""

    EXACT = "exact"                    # green
    APPROXIMATE = "approximate"        # orange -- measured NUMERIC gap
    FALSE = "false"                    # red -- requires a rank 1 source
    TOO_VAGUE = "too_vague"            # defect of the STATEMENT
    CONFLICTING_SOURCES = "conflicting_sources"  # NOT the speaker's fault
    UNVERIFIED = "unverified"          # defect of OUR system, shown as such
    OUT_OF_SCOPE = "out_of_scope"      # rhetoric, opinion, pledge
    PENDING = "pending"                # triggered, verdict not yet returned


# Published thresholds. The published rule is what protects, not caution.
#
# Orange is reserved for a MEASURABLE NUMERIC gap. It never means "a liberty was
# taken" -- that framing judgement requires time and inference we refuse to make.
# A gap, by contrast, is computed and defended with a number.
#
# NOT YET CALIBRATED. These values are estimates, not measurements -- see
# METHODE.md §2. They must be swept against the gold set, not defended.
EXACT_THRESHOLD = 0.05        # relative gap <= 5%  -> exact, tagged approximate
APPROXIMATE_THRESHOLD = 0.25  # 5% < gap <= 25%     -> approximate (orange)
# beyond 25%, or wrong direction, or wrong order of magnitude -> false (red)

# A RELATIVE gap is the wrong instrument when the value is itself a percentage.
#
# Found empirically: "45,3 % de prélèvements" against an INSEE 43,8 % is a
# relative gap of 3.4%, which clears the 5% bar and returns `exact`. But it is
# 1.5 points of GDP -- roughly 45 billion euros, and a substantial error in a
# debate about taxation. The relative framing flattens it.
#
# So for a quantity expressed in points (tax-to-GDP ratio, unemployment rate,
# public spending, debt ratio, inflation), the gap is measured IN POINTS.
EXACT_POINTS = 0.3            # <= 0.3 point -> exact
APPROXIMATE_POINTS = 1.0      # 0.3 to 1.0 point -> approximate
# beyond 1 point, or wrong direction -> false

# Units whose values are compared in points rather than relatively.
POINT_UNITS = {"%", "point", "points", "pp", "% du PIB", "point de PIB"}


class Coherence(str, Enum):
    """THIRD AXIS, independent of verdict and tags.

    Says nothing about true or false: says whether the utterance matches what
    the speaker themselves published or voted. This is what makes PLEDGES
    analysable -- a promise is neither true nor false, but it either matches
    the published manifesto or it does not.
    """

    CONSISTENT = "consistent"        # matches the published manifesto
    DIVERGENT = "divergent"          # manifesto says otherwise (figure, timing)
    ABSENT = "absent"                # manifesto does not mention it
    CONTRADICTED = "contradicted"    # contradicts manifesto, vote or dated statement
    NOT_APPLICABLE = "not_applicable"


class Tag(str, Enum):
    """FACTUAL qualifiers of the comparison. Closed and deliberately short.

    These are not judgements about the speaker or their intent. They state what
    the comparison was made against. They are kept because without them the
    verdict would be mechanically wrong.
    """

    APPROXIMATE_MAGNITUDE = "approximate_magnitude"
    OUTDATED_DATA = "outdated_data"              # source carries another date
    INCOMPARABLE_DEFINITION = "incomparable_definition"  # not the source's measure


class TriggerType(str, Enum):
    """Stage 0. Deterministic, no model involved."""

    PERCENTAGE = "percentage"
    AMOUNT = "amount"
    DATE_OR_PERIOD = "date_or_period"
    SUPERLATIVE = "superlative"
    COMPARATIVE = "comparative"
    VAGUE_QUANTIFIER = "vague_quantifier"
    CAUSALITY = "causality"
    PLEDGE = "pledge"
    ATTRIBUTION = "attribution"      # "you voted", "he said"
    NUMBER = "number"


class Trigger(BaseModel):
    """A pattern matched at stage 0, with no model call."""

    type: TriggerType
    text: str
    start: int
    end: int


class Source(BaseModel):
    """A source actually retrieved. Never a source recalled from memory."""

    url: str = ""
    domain: str = ""
    rank: int = Field(default=1, description="1, 2 or 3 -- caps verdict strength")
    title: Optional[str] = None
    quote: str = Field(
        description="Verbatim span copied from the retrieved document. Checked "
        "by literal comparison, never taken on trust. Keep it under 120 "
        "characters so it can be copied exactly."
    )
    quote_verified: bool = False
    extracted_value: Optional[str] = None
    data_date: Optional[str] = Field(
        default=None,
        description="Vintage of the figure -- statistics are revised, a verdict "
        "without a vintage cannot be defended.",
    )


class Statement(BaseModel):
    """An analysed span of text.

    The unit is not the sentence: one sentence may carry three claims with
    different statuses.
    """

    id: str
    speaker: str
    text: str
    start: int
    end: int
    timestamp: Optional[float] = None

    triggers: List[Trigger] = Field(default_factory=list)

    # stage 1
    category: Optional[Category] = None
    relevant: bool = False
    rejection_reason: Optional[str] = None

    # stage 2
    verdict: Optional[Verdict] = None
    confidence: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="Axis INDEPENDENT of the verdict. A red at 0.55 and a red "
        "at 0.97 must not be displayed the same way.",
    )
    tags: List[Tag] = Field(default_factory=list)
    coherence: Optional[Coherence] = None
    sources: List[Source] = Field(default_factory=list)

    stated_value: Optional[str] = None
    source_value: Optional[str] = None
    relative_gap: Optional[float] = Field(
        default=None,
        description="Drives green/orange/red through the published thresholds.",
    )

    context_note: Optional[str] = Field(
        default=None,
        description="One or two FACTUAL sentences: what the source says and as "
        "of when. No commentary about the speaker.",
    )

    # editorial control
    withdrawn: bool = Field(
        default=False,
        description="A human reviewer unpublished this analysis. The text stays "
        "visible, the analysis is disconnected pending review.",
    )
    revision_note: Optional[str] = Field(
        default=None, description="Set when a verdict was revised after the fact."
    )


# --- structured outputs expected from the model ----------------------------

class TriageResult(BaseModel):
    """Stage 1. Short, cheap, early exit for the majority."""

    category: Category
    relevant: bool = Field(
        description="True only if category == fact AND the statement is "
        "testable as stated against a primary source."
    )
    reason: str = Field(description="One sentence. Why kept or dropped.")
    invoked_measure: Optional[str] = Field(
        default=None,
        description="The exact measure the speaker refers to (e.g. 'headcount "
        "of category A jobseekers', not 'unemployment'). Used to catch "
        "definition mismatches.",
    )


class VerificationResult(BaseModel):
    """Stage 2. Produced after reading the supplied primary sources."""

    verdict: Verdict
    confidence: float = Field(ge=0.0, le=1.0)
    tags: List[Tag] = Field(default_factory=list)
    context_note: str
    sources: List[Source] = Field(default_factory=list)

    stated_value: Optional[str] = None
    source_value: Optional[str] = None
    relative_gap: Optional[float] = Field(
        default=None,
        description="|stated - source| / source as a fraction (0.107 for 10.7%). "
        "Leave empty when the claim carries no figure.",
    )

    reasoning: str = Field(
        default="", description="Two sentences max, for the audit log, not for display."
    )


class CoherenceResult(BaseModel):
    """Stage 2b. Confronts a PLEDGE with the speaker's published manifesto.

    Never issues a truth verdict: a pledge missing from the manifesto is not
    "false", it is absent.
    """

    coherence: Coherence
    confidence: float = Field(ge=0.0, le=1.0)
    context_note: str = Field(
        description="What the manifesto says, verbatim. Not a commentary."
    )
    sources: List[Source] = Field(default_factory=list)
