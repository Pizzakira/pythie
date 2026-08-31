"""HTML rendering for the two degrees of restitution.

DEGREE 1 -- during the debate. Single column, green / orange / red plus the
abstention states, timecode closing each block. No framing judgement: it needs
time we do not have here.

DEGREE 2 -- afterwards. Same material, higher precision: compared values with
their gap, data vintage, manifesto coherence, expandable sources.

ACCESSIBILITY -- colour is NEVER the only channel. Acceptance criterion: render
the page in greyscale; if everything stays legible, it passes. The wavy
underline for an error reuses the spell-checker idiom, already installed in the
reader's head and legible without any colour. Luminances are separated (very
pale green, dark red) so they stay distinguishable under deuteranopia.

A withdrawn block keeps its text and loses its analysis: that is the human
reviewer's kill switch, rendered.
"""

from __future__ import annotations

import html
import json
from typing import List, Optional

from .schema import Coherence, Statement, Tag, Verdict

# (css class, glyph, label) -- glyph and label carry the meaning when colour cannot
VERDICT_STYLE = {
    Verdict.EXACT: ("v-exact", "✓", "sourcé"),
    Verdict.APPROXIMATE: ("v-approx", "≈", "approximation"),
    Verdict.FALSE: ("v-false", "✗", "erreur"),
    Verdict.TOO_VAGUE: ("v-vague", "?", "trop vague pour être testé"),
    Verdict.CONFLICTING_SOURCES: ("v-conflict", "⇄", "sources divergentes"),
    Verdict.UNVERIFIED: ("v-unverified", "○", "non vérifié"),
    Verdict.OUT_OF_SCOPE: ("v-out", "—", "hors périmètre"),
    Verdict.PENDING: ("v-pending", "⋯", "vérification en cours"),
}

TAG_LABEL = {
    Tag.APPROXIMATE_MAGNITUDE: "ordre de grandeur approximatif",
    Tag.OUTDATED_DATA: "donnée d'une autre date",
    Tag.INCOMPARABLE_DEFINITION: "définition non comparable",
}

COHERENCE_LABEL = {
    Coherence.CONSISTENT: ("≡", "conforme au programme"),
    Coherence.DIVERGENT: ("≠", "écart avec le programme"),
    Coherence.ABSENT: ("∅", "absent du programme"),
    Coherence.CONTRADICTED: ("⚡", "contredit le programme"),
    Coherence.NOT_APPLICABLE: ("", ""),
}

# States that stay unmarked at degree 1. Emphasis, figures of speech and
# personal attacks are out of scope, so they get no mark at all; if all text is
# marked, nothing stands out.
UNMARKED_AT_DEGREE1 = {Verdict.OUT_OF_SCOPE, Verdict.TOO_VAGUE}

CSS = """
:root{
  --ground:#f6f7f9;--surface:#fff;--sunken:#eef0f4;--ink:#14181f;--muted:#5c6470;
  --faint:#8b93a1;--rule:#dfe3ea;--accent:#3b5878;
  --exact-bg:#e9f2e8;--exact-fg:#2c6430;--exact-line:#4e8a52;
  --approx-bg:#fbf2df;--approx-fg:#8a5a00;--approx-line:#b98511;
  --false-bg:#fbe6e3;--false-fg:#a3170d;--false-line:#c8352a;--wait-fg:#7b8492;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --ground:#101319;--surface:#171b23;--sunken:#1e232c;--ink:#e7eaef;--muted:#9aa3b2;
  --faint:#6b7484;--rule:#2a3038;--accent:#8fb0d0;
  --exact-bg:#18271a;--exact-fg:#8fcb94;--approx-bg:#2b2312;--approx-fg:#e0b45f;
  --false-bg:#2e1614;--false-fg:#f0958b;--wait-fg:#798391;
}}
:root[data-theme="dark"]{
  --ground:#101319;--surface:#171b23;--sunken:#1e232c;--ink:#e7eaef;--muted:#9aa3b2;
  --faint:#6b7484;--rule:#2a3038;--accent:#8fb0d0;
  --exact-bg:#18271a;--exact-fg:#8fcb94;--approx-bg:#2b2312;--approx-fg:#e0b45f;
  --false-bg:#2e1614;--false-fg:#f0958b;--wait-fg:#798391;
}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);
  font:16px/1.75 Spectral,Georgia,serif}
.page{max-width:46rem;margin:0 auto;padding:2.5rem 1.25rem 6rem}
h1{font-size:1.4rem;margin:0 0 .25rem;letter-spacing:-.015em}
.sub{color:var(--muted);font-size:.8rem;margin:0 0 2rem;
  font-family:ui-sans-serif,system-ui,sans-serif}
.method{border:1px solid var(--rule);border-radius:.5rem;padding:.9rem 1.1rem;
  margin-bottom:2rem;font:.8rem/1.6 ui-sans-serif,system-ui,sans-serif;color:var(--muted)}
.method b{color:var(--ink)}
.block{margin:0 0 1.6rem;padding-left:.9rem;border-left:2px solid var(--rule)}
.speaker{font:600 .72rem/1 ui-sans-serif,system-ui,sans-serif;letter-spacing:.06em;
  text-transform:uppercase;color:var(--accent);margin-bottom:.4rem}
.timecode{display:block;text-align:right;margin-top:.35rem;
  font:.7rem/1 ui-monospace,Menlo,monospace;color:var(--faint)}
mark{background:none;color:inherit;padding:0 .1em;border-radius:.15em;
  text-decoration-thickness:2px;text-underline-offset:3px;cursor:pointer}
mark .g{font:.75em/1 ui-sans-serif,system-ui,sans-serif;vertical-align:.15em;
  margin-left:.15em;opacity:.85}
.v-exact{background:var(--exact-bg);color:var(--exact-fg);
  text-decoration:underline solid var(--exact-line)}
.v-approx{background:var(--approx-bg);color:var(--approx-fg);
  text-decoration:underline dashed var(--approx-line)}
.v-false{background:var(--false-bg);color:var(--false-fg);font-weight:600;
  text-decoration:underline wavy var(--false-line)}
.v-vague,.v-unverified,.v-conflict{background:var(--sunken);color:var(--muted);
  text-decoration:underline dotted var(--muted)}
.v-pending{color:var(--wait-fg);text-decoration:underline dashed var(--wait-fg)}
.withdrawn p{color:var(--muted)}
.withdrawn mark{background:none!important;color:inherit!important;
  text-decoration:none!important;font-weight:400!important;cursor:default}
.withdrawn mark .g{display:none}
.withdrawn .detail{display:none!important}
.notice{display:flex;gap:.5rem;margin:.55rem 0 0;padding:.45rem .7rem;
  background:var(--sunken);border-left:3px solid var(--faint);
  border-radius:0 .3rem .3rem 0;
  font:.74rem/1.5 ui-sans-serif,system-ui,sans-serif;color:var(--muted)}
.detail{margin:.5rem 0 .9rem;padding:.75rem .9rem;border-left:3px solid var(--accent);
  background:var(--sunken);font:.82rem/1.6 ui-sans-serif,system-ui,sans-serif;
  border-radius:0 .3rem .3rem 0}
.detail dt{font-weight:600;font-size:.66rem;letter-spacing:.06em;
  text-transform:uppercase;color:var(--faint);margin-top:.6rem}
.detail dd{margin:.15rem 0 0}
.detail dl{margin:0}
.cmp{font-family:ui-monospace,Menlo,monospace;font-size:.78rem;
  font-variant-numeric:tabular-nums}
.tag{display:inline-block;font-size:.7rem;padding:.1rem .45rem;margin:.15rem .2rem 0 0;
  border:1px solid var(--rule);border-radius:1rem;color:var(--muted)}
.src{font-size:.78rem;margin-top:.2rem;word-break:break-word}
.src a{color:var(--accent)}
.rank{font-family:ui-monospace,monospace;font-size:.66rem;padding:.05rem .3rem;
  border-radius:.2rem;background:var(--exact-bg);color:var(--exact-fg);margin-right:.3rem}
.quote{color:var(--muted);font-style:italic}
.ok{color:var(--exact-fg);font-size:.7rem}
.bad{color:var(--false-fg);font-weight:600}
.legend{margin-top:3rem;padding-top:1.2rem;border-top:1px solid var(--rule);
  font:.78rem/1.7 ui-sans-serif,system-ui,sans-serif;color:var(--muted)}
.legend span{display:inline-block;margin-right:1.1rem}
"""

METHOD_COMMON = (
    "<b>Ce que fait l'outil :</b> il compare une valeur énoncée à celle "
    "publiée par une source primaire. <b>Ce qu'il ne fait pas :</b> analyser la "
    "rhétorique, qualifier un procédé, mesurer une intention. Les emphases, "
    "figures de style et attaques ne sont pas prises en compte. Un énoncé "
    "rigoureusement vrai est vert, qu'il soit ou non incomplet."
)

METHOD_BY_DEGREE = {
    1: METHOD_COMMON + (
        "<br><br><b>Degré 1 — pendant.</b> Vert : valeur confirmée. "
        "Orange : écart de 5 à 25 %. Rouge : contredite par une source de "
        "rang 1. Seuils fixés à l'avance et appliqués par le programme."
    ),
    2: METHOD_COMMON + (
        "<br><br><b>Degré 2 — après.</b> Valeurs comparées, écart, "
        "millésime et sources dépliables. Une citation non retrouvée "
        "littéralement dans le document invalide le verdict."
    ),
}


def _format_timecode(seconds: Optional[float]) -> str:
    if seconds is None:
        return ""
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:d}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:d}:{secs:02d}"


def _detail_panel(statement: Statement) -> str:
    parts: List[str] = ['<div class="detail"><dl>']

    if statement.stated_value or statement.source_value:
        gap = (
            f" · écart {abs(statement.relative_gap):.1%}"
            if statement.relative_gap is not None
            else ""
        )
        parts.append(
            "<dt>Valeurs</dt><dd class='cmp'>"
            f"énoncé <b>{html.escape(str(statement.stated_value or '—'))}</b>"
            f" · source <b>{html.escape(str(statement.source_value or '—'))}</b>"
            f"{gap}</dd>"
        )

    if statement.context_note:
        parts.append(
            f"<dt>Ce que dit la source</dt><dd>{html.escape(statement.context_note)}</dd>"
        )

    if statement.tags:
        chips = "".join(
            f'<span class="tag">{html.escape(TAG_LABEL[t])}</span>' for t in statement.tags
        )
        parts.append(f"<dt>Comparaison</dt><dd>{chips}</dd>")

    if statement.coherence and statement.coherence != Coherence.NOT_APPLICABLE:
        glyph, label = COHERENCE_LABEL[statement.coherence]
        parts.append(f"<dt>Programme</dt><dd>{glyph} {html.escape(label)}</dd>")

    if statement.sources:
        parts.append("<dt>Sources</dt><dd>")
        for src in statement.sources:
            flag = (
                ' <span class="ok">✓ citation retrouvée</span>'
                if src.quote_verified
                else ' <span class="bad">citation non retrouvée</span>'
            )
            vintage = f" · {html.escape(src.data_date)}" if src.data_date else ""
            parts.append(
                f'<div class="src"><span class="rank">rang {src.rank}</span>'
                f'<a href="{html.escape(src.url)}">{html.escape(src.domain)}</a>'
                f"{vintage}{flag}<br>"
                f'<span class="quote">« {html.escape(src.quote[:280])} »</span></div>'
            )
        parts.append("</dd>")
    else:
        parts.append('<dt>Sources</dt><dd class="bad">Aucune source récupérée.</dd>')

    if statement.revision_note:
        parts.append(f"<dt>Révision</dt><dd>↻ {html.escape(statement.revision_note)}</dd>")

    if statement.confidence is not None:
        parts.append(f"<dt>Confiance</dt><dd class='cmp'>{statement.confidence:.0%}</dd>")

    parts.append("</dl></div>")
    return "".join(parts)


def _mark(statement: Statement, degree: int) -> str:
    verdict = statement.verdict or Verdict.PENDING
    text = html.escape(statement.text)

    if degree == 1 and verdict in UNMARKED_AT_DEGREE1:
        return text

    css_class, glyph, label = VERDICT_STYLE[verdict]
    title = label + (
        f" · confiance {statement.confidence:.0%}" if statement.confidence else ""
    )
    mark = (
        f'<mark class="{css_class}" tabindex="0" role="button" '
        f'aria-label="{html.escape(title)}" title="{html.escape(title)}">{text}'
        f'<span class="g" aria-hidden="true">{glyph}</span></mark>'
    )
    return mark if degree == 1 else mark + _detail_panel(statement)


def render(
    statements: List[Statement],
    *,
    title: str,
    degree: int = 2,
    corpus_version: str = "",
) -> str:
    """Produce the page. `degree` is 1 (during) or 2 (after)."""
    blocks: List[str] = []
    current_speaker: Optional[str] = None
    buffer: List[str] = []
    block_end: Optional[float] = None
    withdrawn = False

    def flush() -> None:
        if not buffer:
            return
        notice = (
            '<div class="notice">Analyse retirée — en attente de relecture. '
            "Le texte reste affiché.</div>"
            if withdrawn
            else ""
        )
        blocks.append(
            f'<div class="block{" withdrawn" if withdrawn else ""}">'
            f'<div class="speaker">{html.escape(current_speaker or "")}</div>'
            f'<p>{"".join(buffer)}</p>{notice}'
            f'<span class="timecode">{_format_timecode(block_end)}</span></div>'
        )
        buffer.clear()

    for statement in statements:
        if statement.speaker != current_speaker:
            flush()
            current_speaker = statement.speaker
            withdrawn = statement.withdrawn
        withdrawn = withdrawn or statement.withdrawn
        buffer.append(_mark(statement, degree) + " ")
        block_end = statement.timestamp
    flush()

    legend = "".join(
        f'<span><b class="{VERDICT_STYLE[v][0]}">&nbsp;{VERDICT_STYLE[v][1]}&nbsp;</b> '
        f"{VERDICT_STYLE[v][2]}</span>"
        for v in (
            Verdict.EXACT,
            Verdict.APPROXIMATE,
            Verdict.FALSE,
            Verdict.UNVERIFIED,
            Verdict.PENDING,
        )
    )

    return f"""<title>{html.escape(title)}</title>
<style>{CSS}</style>
<div class="page">
<h1>{html.escape(title)}</h1>
<p class="sub">Degré {degree} de restitution · corpus {html.escape(corpus_version)}</p>
<div class="method">{METHOD_BY_DEGREE[degree]}</div>
{"".join(blocks)}
<div class="legend">{legend}</div>
</div>
"""


def export_json(statements: List[Statement], path: str) -> None:
    """State must live in the data, not only in the pixel.

    This is what makes the output auditable, quotable and readable by a screen
    reader, and what lets degree 2 be replayed from the same material.
    """
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(
            [s.model_dump(mode="json") for s in statements],
            handle,
            ensure_ascii=False,
            indent=2,
        )
