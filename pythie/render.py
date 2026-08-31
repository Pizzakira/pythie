"""The finished page.

Not a debug dump: the thing a reader actually opens. Same interface as the
validated mockup -- counters, filters, search, two degrees -- driven by real
verdicts.

DEGREE 1 -- during. Colour, tag, timecode. Filters and counters from the start.
DEGREE 2 -- after. Compared values, gap, vintage, expandable sources.

ACCESSIBILITY -- colour is NEVER the only channel. Every state carries its own
underline style and glyph, and the state lives in the JSON and the aria-label,
not only in the pixel. Acceptance criterion: the page in greyscale stays fully
legible, and a button in the interface runs that test.

A withdrawn block keeps its text and loses its analysis -- the human reviewer's
kill switch, rendered.
"""

from __future__ import annotations

import html
import json
from typing import Dict, List, Optional

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

# Never marked at degree 1: rhetoric, opinion and pledges are out of scope, and
# a claim too vague to test is noise during a debate. If everything is marked,
# nothing stands out.
UNMARKED_AT_DEGREE1 = {Verdict.OUT_OF_SCOPE, Verdict.TOO_VAGUE}

# Counted and filterable.
COUNTED = [Verdict.EXACT, Verdict.APPROXIMATE, Verdict.FALSE,
           Verdict.UNVERIFIED, Verdict.CONFLICTING_SOURCES, Verdict.PENDING]

CSS = """
:root{
  --ground:#f6f7f9;--surface:#fff;--sunken:#eef0f4;--ink:#14181f;--muted:#5c6470;
  --faint:#8b93a1;--rule:#dfe3ea;--accent:#3b5878;--accent-ink:#fff;
  --exact-bg:#e9f2e8;--exact-fg:#2c6430;--exact-line:#4e8a52;
  --approx-bg:#fbf2df;--approx-fg:#8a5a00;--approx-line:#b98511;
  --false-bg:#fbe6e3;--false-fg:#a3170d;--false-line:#c8352a;--wait-fg:#7b8492;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --ground:#101319;--surface:#171b23;--sunken:#1e232c;--ink:#e7eaef;--muted:#9aa3b2;
  --faint:#6b7484;--rule:#2a3038;--accent:#8fb0d0;--accent-ink:#0d1017;
  --exact-bg:#18271a;--exact-fg:#8fcb94;--approx-bg:#2b2312;--approx-fg:#e0b45f;
  --false-bg:#2e1614;--false-fg:#f0958b;--wait-fg:#798391;
}}
:root[data-theme="dark"]{
  --ground:#101319;--surface:#171b23;--sunken:#1e232c;--ink:#e7eaef;--muted:#9aa3b2;
  --faint:#6b7484;--rule:#2a3038;--accent:#8fb0d0;--accent-ink:#0d1017;
  --exact-bg:#18271a;--exact-fg:#8fcb94;--approx-bg:#2b2312;--approx-fg:#e0b45f;
  --false-bg:#2e1614;--false-fg:#f0958b;--wait-fg:#798391;
}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);
  font:16px/1.6 ui-sans-serif,system-ui,-apple-system,sans-serif}
.gris{filter:grayscale(1)}
.avis{background:var(--accent);color:var(--accent-ink);font-size:.72rem;
  padding:.5rem 1rem;text-align:center;letter-spacing:.03em}
header{border-bottom:1px solid var(--rule);background:var(--surface)}
.hwrap{max-width:80rem;margin:0 auto;padding:1.1rem 1.25rem;display:flex;
  align-items:baseline;gap:1rem;flex-wrap:wrap}
h1{font:600 1.4rem/1.2 Georgia,serif;margin:0;letter-spacing:-.015em}
.ctx{color:var(--muted);font-size:.8rem;margin:0}
.shell{max-width:80rem;margin:0 auto;padding:1.25rem;display:grid;gap:1.25rem;
  grid-template-columns:1fr}
@media(min-width:64rem){.shell{grid-template-columns:18rem 1fr;align-items:start}}
.rail{position:sticky;top:.75rem;display:flex;flex-direction:column;gap:.95rem;
  background:var(--surface);border:1px solid var(--rule);border-radius:.6rem;
  padding:1rem;max-height:calc(100vh - 1.5rem);overflow-y:auto}
.lab{font-size:.66rem;font-weight:600;letter-spacing:.09em;text-transform:uppercase;
  color:var(--faint);margin:0 0 .5rem}
.kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:.4rem}
.kpi{background:var(--sunken);border-radius:.4rem;padding:.5rem .3rem;text-align:center}
.kpi b{display:block;font:500 1.3rem/1.1 ui-monospace,monospace;
  font-variant-numeric:tabular-nums}
.kpi span{font-size:.6rem;letter-spacing:.05em;text-transform:uppercase;color:var(--muted)}
.kpi.e b{color:var(--exact-fg)}.kpi.a b{color:var(--approx-fg)}.kpi.f b{color:var(--false-fg)}
.reste{font-size:.72rem;color:var(--muted);margin:.5rem 0 0}
.chips{display:flex;flex-wrap:wrap;gap:.35rem}
.chip{font:inherit;font-size:.74rem;padding:.28rem .6rem;border-radius:1rem;cursor:pointer;
  border:1px solid var(--rule);background:var(--surface);color:var(--muted);
  display:inline-flex;gap:.3rem;align-items:center}
.chip[aria-pressed="true"]{background:var(--ink);border-color:var(--ink);color:var(--ground)}
.chip .n{font:.68rem ui-monospace,monospace;opacity:.75;font-variant-numeric:tabular-nums}
.rech input{width:100%;font:inherit;font-size:.82rem;padding:.5rem .6rem;
  border:1px solid var(--rule);border-radius:.4rem;background:var(--sunken);color:var(--ink)}
.seg{display:flex;border:1px solid var(--rule);border-radius:.4rem;overflow:hidden}
.seg button{flex:1;font:inherit;font-size:.74rem;padding:.4rem;cursor:pointer;
  background:var(--surface);color:var(--muted);border:0}
.seg button[aria-pressed="true"]{background:var(--accent);color:var(--accent-ink)}
.note-s{font-size:.7rem;line-height:1.5;color:var(--muted);margin:.45rem 0 0}
.outil{font:inherit;font-size:.72rem;color:var(--muted);background:none;
  border:1px dashed var(--rule);border-radius:.4rem;padding:.4rem;cursor:pointer;width:100%}
.outil[aria-pressed="true"]{border-style:solid;border-color:var(--accent);color:var(--accent)}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.flux{background:var(--surface);border:1px solid var(--rule);border-radius:.6rem;
  padding:1.6rem 1.5rem 2rem;min-height:26rem}
.bloc{padding:0 0 1.3rem;margin:0 0 1.3rem;border-bottom:1px solid var(--rule)}
.bloc:last-child{border-bottom:0;margin-bottom:0}
.tete{display:flex;align-items:center;gap:.5rem;margin:0 0 .45rem}
.qui{font:600 .68rem/1 ui-sans-serif;letter-spacing:.09em;text-transform:uppercase;
  color:var(--accent);margin:0}
.badge{font-size:.6rem;letter-spacing:.05em;text-transform:uppercase;color:var(--faint);
  border:1px solid var(--rule);border-radius:1rem;padding:.05rem .4rem}
.bloc p{font:1.05rem/1.75 Georgia,serif;margin:0;max-width:64ch}
.tc{display:block;text-align:right;margin-top:.5rem;font:.7rem ui-monospace,monospace;
  color:var(--faint);font-variant-numeric:tabular-nums}
mark{background:none;color:inherit;padding:.02em .12em;border-radius:.16em;cursor:pointer;
  text-decoration-thickness:2px;text-underline-offset:.22em}
mark .g{font:600 .7em ui-sans-serif;margin-left:.18em;vertical-align:.12em;opacity:.9}
.v-exact{background:var(--exact-bg);color:var(--exact-fg);text-decoration:underline solid var(--exact-line)}
.v-approx{background:var(--approx-bg);color:var(--approx-fg);text-decoration:underline dashed var(--approx-line)}
.v-false{background:var(--false-bg);color:var(--false-fg);font-weight:600;text-decoration:underline wavy var(--false-line)}
.v-vague,.v-unverified,.v-conflict{background:var(--sunken);color:var(--muted);
  text-decoration:underline dotted var(--muted)}
.v-pending{color:var(--wait-fg);text-decoration:underline dashed var(--wait-fg)}
mark.eteint{opacity:.2}
.withdrawn p{color:var(--muted)}
.withdrawn mark{background:none!important;color:inherit!important;
  text-decoration:none!important;font-weight:400!important;cursor:default}
.withdrawn mark .g,.withdrawn .detail{display:none!important}
.notice{margin:.55rem 0 0;padding:.45rem .7rem;background:var(--sunken);
  border-left:3px solid var(--faint);border-radius:0 .3rem .3rem 0;
  font-size:.74rem;color:var(--muted)}
.detail{display:none;margin:.5rem 0 .9rem;padding:.75rem .9rem;border-left:3px solid var(--accent);
  background:var(--sunken);font-size:.82rem;line-height:1.6;border-radius:0 .3rem .3rem 0;
  max-width:64ch}
.detail.ouvert{display:block}
.detail dl{display:grid;grid-template-columns:auto 1fr;gap:.3rem .9rem;margin:0}
.detail dt{font:600 .64rem ui-sans-serif;letter-spacing:.07em;text-transform:uppercase;
  color:var(--faint);padding-top:.15rem}
.detail dd{margin:0}
.cmp{font:.78rem ui-monospace,monospace;font-variant-numeric:tabular-nums}
.tag{display:inline-block;font-size:.68rem;padding:.1rem .45rem;margin:.15rem .2rem 0 0;
  border:1px solid var(--rule);border-radius:1rem;color:var(--muted)}
.src{font-size:.78rem;margin-top:.2rem;word-break:break-word}
.src a{color:var(--accent)}
.rank{font:.66rem ui-monospace,monospace;padding:.05rem .3rem;border-radius:.2rem;
  background:var(--exact-bg);color:var(--exact-fg);margin-right:.3rem}
.quote{color:var(--muted);font-style:italic}
.ok{color:var(--exact-fg);font-size:.7rem}.bad{color:var(--false-fg);font-weight:600}
.vide{color:var(--muted);font-size:.85rem;text-align:center;padding:2.5rem 0}
footer{max-width:80rem;margin:0 auto;padding:.5rem 1.25rem 3rem}
.legend{display:flex;flex-wrap:wrap;gap:.4rem 1.2rem;padding-top:1rem;
  border-top:1px solid var(--rule);font-size:.74rem;color:var(--muted)}
.metho{font-size:.76rem;line-height:1.65;color:var(--muted);margin:1rem 0 0;max-width:64ch}
.metho b{color:var(--ink)}
"""

METHOD = (
    "<b>Ce que fait l'outil :</b> il compare une valeur énoncée à celle publiée "
    "par une source primaire. <b>Ce qu'il ne fait pas :</b> analyser la "
    "rhétorique, qualifier un procédé, mesurer une intention. Un énoncé "
    "rigoureusement vrai est vert, qu'il soit ou non incomplet. "
    "Seuils publiés : écart ≤ 5 % exact · 5–25 % approximatif · > 25 % faux."
)


def _timecode(seconds: Optional[float]) -> str:
    if seconds is None:
        return ""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _detail(st: Statement) -> str:
    p: List[str] = ['<div class="detail"><dl>']
    if st.stated_value or st.source_value:
        gap = f" · écart {abs(st.relative_gap):.1%}" if st.relative_gap is not None else ""
        p.append("<dt>Valeurs</dt><dd class='cmp'>"
                 f"énoncé <b>{html.escape(str(st.stated_value or '—'))}</b> · "
                 f"source <b>{html.escape(str(st.source_value or '—'))}</b>{gap}</dd>")
    if st.context_note:
        p.append(f"<dt>Ce que dit la source</dt><dd>{html.escape(st.context_note)}</dd>")
    if st.tags:
        chips = "".join(f'<span class="tag">{html.escape(TAG_LABEL[t])}</span>' for t in st.tags)
        p.append(f"<dt>Comparaison</dt><dd>{chips}</dd>")
    if st.coherence and st.coherence != Coherence.NOT_APPLICABLE:
        g, lab = COHERENCE_LABEL[st.coherence]
        p.append(f"<dt>Programme</dt><dd>{g} {html.escape(lab)}</dd>")
    if st.sources:
        p.append("<dt>Sources</dt><dd>")
        for s in st.sources:
            flag = ('<span class="ok">✓ citation retrouvée</span>' if s.quote_verified
                    else '<span class="bad">citation non retrouvée</span>')
            vintage = f" · {html.escape(s.data_date)}" if s.data_date else ""
            p.append(f'<div class="src"><span class="rank">rang {s.rank}</span>'
                     f'<a href="{html.escape(s.url)}" target="_blank" rel="noopener">'
                     f'{html.escape(s.domain)}</a>{vintage} {flag}<br>'
                     f'<span class="quote">« {html.escape(s.quote[:260])} »</span></div>')
        p.append("</dd>")
    else:
        p.append('<dt>Sources</dt><dd class="bad">Aucune source récupérée.</dd>')
    if st.revision_note:
        p.append(f"<dt>Révision</dt><dd>↻ {html.escape(st.revision_note)}</dd>")
    if st.confidence is not None:
        p.append(f"<dt>Confiance</dt><dd class='cmp'>{st.confidence:.0%}</dd>")
    p.append("</dl></div>")
    return "".join(p)


def _mark(st: Statement, degree: int) -> str:
    verdict = st.verdict or Verdict.PENDING
    text = html.escape(st.text)
    if degree == 1 and verdict in UNMARKED_AT_DEGREE1:
        return text
    if verdict == Verdict.OUT_OF_SCOPE:
        return text
    cls, glyph, label = VERDICT_STYLE[verdict]
    title = label + (f" · confiance {st.confidence:.0%}" if st.confidence else "")
    mark = (f'<mark class="{cls}" data-v="{verdict.value}" tabindex="0" role="button" '
            f'aria-label="{html.escape(title)}" title="{html.escape(title)}">{text}'
            f'<span class="g" aria-hidden="true">{glyph}</span></mark>')
    return mark + (_detail(st) if degree == 2 else "")


def render(statements: List[Statement], *, title: str, degree: int = 2,
           corpus_version: str = "", subtitle: str = "", warning: str = "",
           replay: float = 0.0) -> str:
    """The page a reader opens.

    `replay` > 0 turns degree 1 into what it is meant to be: an experience that
    unfolds. Blocks appear at their own timecode, marks land in `pending`, and
    the verdict resolves a few seconds later -- the real arrival order, at
    `replay` times normal speed.

    That lag is not a defect being hidden. It is the honest shape of the thing:
    a verdict cannot precede the evidence it rests on. Consolidation comes
    afterwards, at degree 2, when there is time to be precise.
    """
    blocks: List[str] = []
    speaker: Optional[str] = None
    buffer: List[str] = []
    start: Optional[float] = None
    end: Optional[float] = None
    withdrawn = False

    def flush() -> None:
        if not buffer:
            return
        note = ('<div class="notice">Analyse retirée — en attente de relecture. '
                'Le texte reste affiché.</div>' if withdrawn else "")
        blocks.append(
            f'<div class="bloc{" withdrawn" if withdrawn else ""}" data-qui="{html.escape(speaker or "")}">'
            f'<div class="tete"><p class="qui">{html.escape(speaker or "")}</p></div>'
            f'<p>{"".join(buffer)}</p>{note}'
            f'<span class="tc">{_timecode(end)}</span></div>')
        buffer.clear()
        start = None

    for st in statements:
        if st.speaker != speaker:
            flush()
            speaker, withdrawn = st.speaker, st.withdrawn
            start = st.timestamp
        if start is None:
            start = st.timestamp
        withdrawn = withdrawn or st.withdrawn
        buffer.append(_mark(st, degree) + " ")
        end = st.timestamp
    flush()

    counts: Dict[str, int] = {}
    for st in statements:
        if st.verdict:
            counts[st.verdict.value] = counts.get(st.verdict.value, 0) + 1

    chips = "".join(
        f'<button class="chip" aria-pressed="false" data-f="{v.value}">'
        f'{VERDICT_STYLE[v][1]} {VERDICT_STYLE[v][2]} '
        f'<span class="n">{counts.get(v.value, 0)}</span></button>'
        for v in COUNTED if counts.get(v.value))

    legend = "".join(
        f'<span><b class="{VERDICT_STYLE[v][0]}">&nbsp;{VERDICT_STYLE[v][1]}&nbsp;</b> '
        f'{VERDICT_STYLE[v][2]}</span>' for v in COUNTED)

    banner = f'<div class="avis">{html.escape(warning)}</div>' if warning else ""

    return f"""<title>{html.escape(title)}</title>
<style>{CSS}</style>
{banner}
<header><div class="hwrap">
  <h1>Pythie</h1>
  <p class="ctx">{html.escape(title)}{' · ' + html.escape(subtitle) if subtitle else ''}</p>
  <span id="etat" style="margin-left:auto;font:600 .72rem ui-sans-serif;letter-spacing:.07em;
    text-transform:uppercase;color:var(--false-fg)">{'en direct' if replay else ''}</span>
</div></header>
<div class="shell">
  <aside class="rail">
    <div><p class="lab">Vérifications</p>
      <div class="kpis">
        <div class="kpi e"><b id="k-e">{counts.get('exact', 0)}</b><span>exact</span></div>
        <div class="kpi a"><b id="k-a">{counts.get('approximate', 0)}</b><span>approx.</span></div>
        <div class="kpi f"><b id="k-f">{counts.get('false', 0)}</b><span>faux</span></div>
      </div>
      <p class="reste">{counts.get('unverified', 0)} non vérifiées ·
         {counts.get('out_of_scope', 0)} hors périmètre</p></div>
    <div><p class="lab">Filtres</p><div class="chips" id="filtres">{chips}</div></div>
    <div><p class="lab">Recherche</p><label class="rech">
      <input id="q" type="search" placeholder="chômage, dette, 43,6 %…"
             aria-label="Rechercher dans la transcription"></label></div>
    <div><p class="lab">Degré</p><div class="seg">
      <button aria-pressed="{str(degree == 1).lower()}" onclick="location.href='?d=1'">1 — pendant</button>
      <button aria-pressed="{str(degree == 2).lower()}" onclick="location.href='?d=2'">2 — après</button>
      </div><p class="note-s">Degré {degree} · corpus {html.escape(corpus_version)}</p></div>
    <button class="outil" id="gris" aria-pressed="false">Test niveaux de gris</button>
  </aside>
  <main class="flux" id="flux">{"".join(blocks)}</main>
</div>
<footer>
  <div class="legend">{legend}</div>
  <p class="metho">{METHOD}</p>
</footer>
<script>
const REPLAY={replay};
const F=new Set(); let Q="";

// --- rejeu : le texte arrive, le verdict le rejoint --------------------
// Le decalage est la forme honnete de la chose : un verdict ne peut pas
// preceder la preuve sur laquelle il repose.
if(REPLAY>0){{
  const blocs=[...document.querySelectorAll('.bloc')];
  const t0=blocs.length?parseFloat(blocs[0].dataset.t||0):0;
  blocs.forEach(b=>{{
    b.style.display='none';
    b.querySelectorAll('mark').forEach(m=>{{
      m.dataset.final=m.className; m.dataset.finalG=m.querySelector('.g')?.textContent||'';
      m.className='v-pending'; const g=m.querySelector('.g'); if(g)g.textContent='⋯';
    }});
  }});
  const etat=document.getElementById('etat');
  blocs.forEach(b=>{{
    const dt=(parseFloat(b.dataset.t||0)-t0)*1000/REPLAY;
    setTimeout(()=>{{
      b.style.display='';
      b.scrollIntoView({{behavior:'smooth',block:'end'}});
      // Le verdict arrive apres le texte, comme en vrai.
      b.querySelectorAll('mark').forEach((m,i)=>setTimeout(()=>{{
        m.className=m.dataset.final;
        const g=m.querySelector('.g'); if(g)g.textContent=m.dataset.finalG;
        m.animate([{{boxShadow:'0 0 0 3px var(--accent)'}},{{boxShadow:'0 0 0 0 transparent'}}],
                  {{duration:900,easing:'ease-out'}});
        maj();
      }}, 2500+i*700));
    }}, dt);
  }});
  const fin=blocs.length?(parseFloat(blocs[blocs.length-1].dataset.t||0)-t0)*1000/REPLAY:0;
  setTimeout(()=>{{if(etat)etat.textContent='flux termine';}}, fin+4000);
}}

function maj(){{
  const c={{}};
  document.querySelectorAll('.bloc:not([style*="none"]) mark').forEach(m=>{{
    const v=m.dataset.v; if(m.className!=='v-pending')c[v]=(c[v]||0)+1;}});
  const set=(id,v)=>{{const e=document.getElementById(id); if(e)e.textContent=v||0;}};
  set('k-e',c['exact']); set('k-a',c['approximate']); set('k-f',c['false']);
}}
document.querySelectorAll('#filtres .chip').forEach(c=>c.onclick=()=>{{
  const v=c.dataset.f, on=c.getAttribute('aria-pressed')==='true';
  c.setAttribute('aria-pressed',!on); on?F.delete(v):F.add(v); filtrer();}});
document.getElementById('q').oninput=e=>{{Q=e.target.value.toLowerCase();filtrer();}};
document.getElementById('gris').onclick=e=>{{
  const on=e.currentTarget.getAttribute('aria-pressed')==='true';
  e.currentTarget.setAttribute('aria-pressed',!on);
  document.body.classList.toggle('gris',!on);}};
document.querySelectorAll('mark').forEach(m=>m.onclick=()=>{{
  const d=m.nextElementSibling;
  if(d&&d.classList.contains('detail'))d.classList.toggle('ouvert');}});
function filtrer(){{
  let vus=0;
  document.querySelectorAll('.bloc').forEach(b=>{{
    const okQ=!Q||b.textContent.toLowerCase().includes(Q);
    let okF=!F.size;
    b.querySelectorAll('mark').forEach(m=>{{
      const hit=F.has(m.dataset.v); if(hit)okF=true;
      m.classList.toggle('eteint',F.size>0&&!hit);}});
    const v=okQ&&okF; b.hidden=!v; if(v)vus++;}});
  let e=document.getElementById('vide');
  if(!vus){{if(!e){{e=document.createElement('p');e.id='vide';e.className='vide';
    e.textContent='Aucun passage ne correspond.';flux.append(e);}}}}
  else if(e)e.remove();}}
</script>
"""


def export_json(statements: List[Statement], path: str) -> None:
    """State lives in the data, not only in the pixel: auditable, quotable, and
    readable by a screen reader."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump([s.model_dump(mode="json") for s in statements], f,
                  ensure_ascii=False, indent=2)
