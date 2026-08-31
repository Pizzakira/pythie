#!/usr/bin/env python
"""Run the pipeline over a transcript and produce both renderings.

    python scripts/run_poc.py data/debate.json --degree 2 --out data/debate

On an archived debate whose press fact-checks already exist, the numbers to
read first, in this order:

  1. RED COUNT        -- each one is a potential lawsuit
  2. ABSTENTION RATE  -- a system that never admits ignorance is lying
  3. UNVERIFIED QUOTES -- a direct measure of hallucination
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pythie import corpus as corpus_module  # noqa: E402
from pythie import pipeline, render, retrieval, triggers  # noqa: E402
from pythie.backend import LocalBackend  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcript", help="JSON produced by fetch_transcript.py")
    parser.add_argument("--degree", type=int, choices=(1, 2), default=2)
    parser.add_argument("--out", default="data/analysis")
    parser.add_argument("--limit", type=int, default=0, help="first N blocks only")
    parser.add_argument(
        "--dry",
        action="store_true",
        help="deterministic stages only, no model call",
    )
    args = parser.parse_args()

    payload = json.loads(Path(args.transcript).read_text(encoding="utf-8"))
    blocks = payload["blocs"][: args.limit] if args.limit else payload["blocs"]

    statements = []
    for block in blocks:
        statements.extend(
            pipeline.split(
                block["texte"],
                block.get("locuteur", "inconnu"),
                start_time=block["debut"],
                duration=block["fin"] - block["debut"],
            )
        )

    minutes = (blocks[-1]["fin"] - blocks[0]["debut"]) / 60 if blocks else 0
    whole_text = " ".join(b["texte"] for b in blocks)
    density = triggers.density(whole_text, minutes)

    print(f"{len(statements)} statements over {minutes:.0f} min", file=sys.stderr)
    print(
        f"stage 0 -- {density['total']} triggers "
        f"({density['per_minute']}/min): {density['by_type']}",
        file=sys.stderr,
    )

    if args.dry:
        print("\n(--dry: stopping before any model call)", file=sys.stderr)
        return

    web_corpus = corpus_module.load()
    base = retrieval.load()
    backend = LocalBackend()

    ok, detail = backend.available()
    if not ok:
        print(f"model backend unavailable: {detail}", file=sys.stderr)
        sys.exit(1)
    print(f"backend: {detail}", file=sys.stderr)
    print(
        f"local base: {len(base.domains)} domain(s), "
        f"{len(base.all_sources())} primary source(s)",
        file=sys.stderr,
    )

    statements, stats = pipeline.analyze(
        statements,
        base,
        backend=backend,
        degree=args.degree,
        on_progress=lambda message: print(message, file=sys.stderr),
    )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    for degree in ((1, 2) if args.degree == 2 else (1,)):
        html = render.render(
            statements,
            title=payload.get("titre", out.stem),
            degree=degree,
            corpus_version=web_corpus.version,
        )
        (out.parent / f"{out.name}_degree{degree}.html").write_text(html, encoding="utf-8")
    render.export_json(statements, str(out.parent / f"{out.name}.json"))

    print(
        f"""
--- results ---------------------------------------------------
statements              {stats.statements}
triggered  (stage 0)    {stats.triggered}
relevant   (stage 1)    {stats.relevant}
verified   (stage 2)    {stats.verified}
by category             {stats.by_category}
by verdict              {stats.by_verdict}

REDS                    {stats.reds()}   <- each is a potential lawsuit
abstention rate         {stats.abstention_rate():.1%}
unverified quotes       {stats.unverified_quotes}   <- hallucination measure
---------------------------------------------------------------
output: {out.parent / out.name}_degree*.html""",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
