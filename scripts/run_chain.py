#!/usr/bin/env python
"""End-to-end chain, with explicit stubs where a stage is not ready.

    python scripts/run_chain.py data/laref2026.json --plateau data/laref2026.plateau.yaml

Stages, and what each does today:

  0  triggers      REAL      regex, no model, tested
  0.5 agreement    REAL      needs --temoin; without one, no red can be published
  1  speakers      STUB      no voice prints enrolled yet -> everyone unknown
  2  triage        REAL      local model, or --no-model to skip
  3  verification  REAL      local base, currently one domain
  4  render        REAL      two degrees

A STUBBED STAGE NEVER PRODUCES A COLOURED VERDICT. Stubs mark spans as
`pending` or `unverified` -- the neutral states -- so a page produced by an
incomplete chain can never be mistaken for a fact-check. That is the whole
point of running the chain before it is finished.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pythie import brief as brief_mod  # noqa: E402
from pythie import corpus as corpus_mod  # noqa: E402
from pythie import pipeline, render, retrieval, triggers  # noqa: E402
from pythie.backend import BackendError, LocalBackend  # noqa: E402
from pythie.media import transcripts  # noqa: E402
from pythie.media.voiceprint import UNKNOWN  # noqa: E402
from pythie.memory import ClaimLedger, Groundwork  # noqa: E402
from pythie.schema import Statement, TriageResult, Verdict  # noqa: E402
from pythie.verify import verify  # noqa: E402


def load_panel(path: Path | None) -> dict:
    if not path or not path.exists():
        return {"analyse_debut_s": 0.0, "intervenants": []}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def analysed_speakers(panel: dict) -> set[str]:
    """Only candidates are fact-checked -- see voiceprint.ANALYSED_ROLES."""
    return {p["nom"] for p in panel.get("intervenants", []) if p.get("analyse")}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcript")
    parser.add_argument("--plateau", default=None)
    parser.add_argument("--out", default="data/chaine")
    parser.add_argument("--limit", type=int, default=0,
                        help="stop after N claims verified (cost control)")
    parser.add_argument("--no-model", action="store_true",
                        help="stages 0 and 4 only -- no model call at all")
    parser.add_argument("--depuis", type=float, default=None,
                        help="start at minute N, overriding the panel manifest")
    parser.add_argument("--minutes", type=float, default=0.0,
                        help="analyse only N minutes from the start point")
    parser.add_argument("--temoin", action="append", default=[],
                        help="transcription independante du meme audio, pour "
                             "l'accord entre transcriptions. Repetable.")
    parser.add_argument("--famille", default="",
                        help="famille ASR de la transcription principale "
                             "(youtube, whisper, crisper...) si le fichier ne "
                             "la declare pas.")
    parser.add_argument("--accord", choices=["strict", "rouges"], default="strict",
                        help="strict : aucun verdict colore sur un chiffre non "
                             "corrobore. rouges : on verifie quand meme, mais "
                             "aucun rouge n'est publie.")
    parser.add_argument("--rejeu", type=float, default=0.0,
                        help="replay speed for degree 1 (e.g. 8 = eight times "
                             "faster). 0 renders a static page.")
    args = parser.parse_args()

    panel = load_panel(Path(args.plateau) if args.plateau else None)
    start_at = (args.depuis * 60 if args.depuis is not None
                else float(panel.get("analyse_debut_s", 0.0)))
    payload = json.loads(Path(args.transcript).read_text(encoding="utf-8"))
    blocks = [b for b in payload["blocs"] if b["fin"] > start_at]
    if args.minutes:
        # A window, not the whole debate. The experience we are testing is what
        # a viewer sees unfold, and that does not require three hours.
        stop_at = start_at + args.minutes * 60
        blocks = [b for b in blocks if b["debut"] < stop_at]

    print(f"=== {payload.get('titre', args.transcript)} ===", file=sys.stderr)
    if start_at:
        print(f"analyse a partir de {int(start_at)//60}:{int(start_at)%60:02d} "
              f"-- {panel.get('analyse_debut_note', '')}", file=sys.stderr)

    # --- stage 1 (STUB): speaker attribution ------------------------------
    # No voice prints are enrolled, so nobody is identified. Under the project
    # rule, an unattributed passage is not judged against anyone -- but here
    # that would verify nothing at all, so the stub names the whole debate as
    # one unidentified speaker and lets verification proceed. The rendered
    # page says so.
    speakers_ok = analysed_speakers(panel)
    print(f"etage 1 STUB -- aucune empreinte enrolee, locuteur = « {UNKNOWN} »",
          file=sys.stderr)
    print(f"             ({len(speakers_ok)} candidats seraient analyses)", file=sys.stderr)

    statements: list[Statement] = []
    spans: dict[str, tuple[float, float]] = {}
    for block in blocks:
        produced = pipeline.split(block["texte"], UNKNOWN,
                                  start_time=block["debut"],
                                  duration=block["fin"] - block["debut"])
        # The block's real boundaries, not the interpolated timestamp: the
        # agreement layer aligns two transcriptions on time, and interpolation
        # inside a 25-second block is exactly the drift that made the 01/09
        # figure bench measure nothing (METHODE.md §11).
        for statement in produced:
            spans[statement.id] = (block["debut"], block["fin"])
        statements.extend(produced)

    # --- stage 0 (REAL) ---------------------------------------------------
    minutes = (blocks[-1]["fin"] - blocks[0]["debut"]) / 60
    whole = " ".join(b["texte"] for b in blocks)
    density = triggers.density(whole, minutes)
    candidates = [s for s in statements if triggers.deserves_verification(s.triggers)]
    print(f"etage 0 REEL -- {len(statements)} enonces, {density['total']} declencheurs "
          f"({density['per_minute']}/min), {len(candidates)} a verifier", file=sys.stderr)

    # --- stage 0.5 (REAL): agreement between transcriptions ---------------
    primary = transcripts.Transcript(
        name=Path(args.transcript).stem,
        family=args.famille or payload.get("transcription", {}).get("famille", ""),
        blocks=[transcripts.Block(b["debut"], b["fin"], b["texte"]) for b in blocks],
    )
    if args.temoin and not primary.family:
        # Without a declared family we cannot tell a second reading from a
        # sibling of the first, and counting a fine-tune as a witness would
        # void the whole layer. Refuse rather than guess.
        sys.exit("famille de la transcription principale non declaree : "
                 "impossible d'ecarter un temoin de la meme famille (--famille).")
    loaded = [transcripts.Transcript.load(path) for path in args.temoin]
    witnesses = transcripts.independent(primary, loaded)
    if len(loaded) != len(witnesses):
        same = [t.name for t in loaded if t not in witnesses]
        print(f"etage 0.5   -- temoin(s) ecarte(s), meme famille que la source : "
              f"{', '.join(same)}", file=sys.stderr)

    strictness = pipeline.Strictness(args.accord)
    candidates, agreements = pipeline.gate(
        candidates, spans, witnesses, strictness=strictness
    )
    accord = transcripts.report(list(agreements.values()))
    if witnesses:
        print(f"etage 0.5 REEL -- temoins : "
              f"{', '.join(f'{t.name} ({t.family})' for t in witnesses)}",
              file=sys.stderr)
        print(f"             {accord['corroborated']}/{accord['with_figures']} "
              f"chiffres corrobores, {accord['blocked_share']:.0%} bloques "
              f"({strictness.value}) -- {accord['by_status']}", file=sys.stderr)
    else:
        print("etage 0.5   -- aucune transcription temoin : aucun chiffre n'est "
              "corrobore, aucun rouge ne sera publie", file=sys.stderr)

    web_corpus = corpus_mod.load()
    base = retrieval.load()
    glossary = brief_mod.load_glossary()

    if args.no_model:
        for statement in candidates:
            statement.verdict = Verdict.PENDING
        for statement in statements:
            if statement.verdict is None:
                statement.verdict = Verdict.OUT_OF_SCOPE
        write(statements, args, web_corpus, payload, note="--no-model",
              witnesses=witnesses, accord=accord)
        return

    backend = LocalBackend()
    ok, detail = backend.available()
    if not ok:
        print(f"backend indisponible: {detail}", file=sys.stderr)
        sys.exit(1)
    print(f"backend      -- {detail}", file=sys.stderr)

    # --- stage 2 + 3 (REAL) -----------------------------------------------
    ledger = ClaimLedger()
    counts = {"triage_fail": 0, "no_source": 0, "verified": 0, "reds_withdrawn": 0}
    todo = candidates[: args.limit] if args.limit else candidates

    for index, statement in enumerate(todo, 1):
        composed = brief_mod.compose(statement.text, glossary, base)
        if composed.is_empty():
            # No domain covers this claim. An honest abstention, and the most
            # common outcome while the corpus holds a single domain.
            statement.verdict = Verdict.UNVERIFIED
            statement.confidence = 0.0
            statement.context_note = (
                "Aucun domaine du corpus ne couvre cette affirmation. "
                "Defaut de notre base, pas une refutation."
            )
            counts["no_source"] += 1
            continue

        try:
            result = verify(backend, base, statement)
        except BackendError as error:
            print(f"  [{index}] backend: {error}", file=sys.stderr)
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
        counts["verified"] += 1
        if pipeline.guard_red(statement, agreements.get(statement.id)):
            counts["reds_withdrawn"] += 1

        for revision in ledger.record(
            statement.id, statement.text, result,
            Groundwork(composed.domains[0] if composed.domains else "",
                       composed.source_keys, ", ".join(composed.terms)),
        ):
            for other in statements:
                if other.id == revision.statement_id:
                    other.verdict = revision.new
                    other.revision_note = revision.note

        print(f"  [{index}/{len(todo)}] {result.verdict.value:12} "
              f"{statement.text[:64]}", file=sys.stderr)

    for statement in statements:
        if statement.verdict is None:
            statement.verdict = Verdict.OUT_OF_SCOPE

    print(f"\netage 2/3    -- {counts['verified']} verifiees, "
          f"{counts['no_source']} hors corpus, "
          f"{ledger.reverifications} reverifications", file=sys.stderr)
    write(statements, args, web_corpus, payload, ledger=ledger)


def write(statements, args, web_corpus, payload, ledger=None, note="",
          witnesses=(), accord=None) -> None:
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    # The banner states what the chain actually did, not what it is meant to do
    # one day. A page produced without a witness transcription must say that no
    # figure was corroborated -- otherwise the reader cannot tell an abstention
    # caused by our chain from a claim the sources failed to support.
    warning = ("Aucune empreinte vocale enrolee : les prises de parole ne sont "
               "pas attribuees. ")
    if witnesses:
        heard = ", ".join(f"{t.name} ({t.family})" for t in witnesses)
        share = f"{accord['corroborated']}/{accord['with_figures']}" if accord else "?"
        warning += (f"Accord entre transcriptions actif — temoin(s) : {heard}. "
                    f"{share} chiffres corrobores ; les autres ne sont pas juges.")
    else:
        warning += ("Une seule source de transcription : aucun chiffre n'est "
                    "corrobore et aucun rouge n'est publie.")
    for degree in (1, 2):
        html = render.render(
            statements,
            title=payload.get("titre", out.stem),
            degree=degree,
            corpus_version=web_corpus.version,
            subtitle=f"{len(statements)} enonces",
            warning=warning,
            # Only degree 1 unfolds. Degree 2 is the consolidation, read at
            # leisure afterwards -- replaying it would make no sense.
            replay=args.rejeu if degree == 1 else 0.0,
        )
        (out.parent / f"{out.name}_degre{degree}.html").write_text(html, encoding="utf-8")
    render.export_json(statements, str(out.parent / f"{out.name}.json"))
    if ledger:
        ledger.write_audit(out.parent / f"{out.name}_audit.json")

    tally: dict[str, int] = {}
    for statement in statements:
        key = statement.verdict.value if statement.verdict else "none"
        tally[key] = tally.get(key, 0) + 1

    print(f"\n--- verdicts {note} ---", file=sys.stderr)
    for key, value in sorted(tally.items(), key=lambda kv: -kv[1]):
        print(f"  {key:20} {value}", file=sys.stderr)
    print(f"\nsortie: {out.parent / out.name}_degre*.html", file=sys.stderr)


if __name__ == "__main__":
    main()
