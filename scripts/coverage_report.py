#!/usr/bin/env python
"""State what each candidate dossier actually contains.

A declaration, not a gate. Dossiers are uneven because the available material
is uneven, and that is fine.

What it does report is the consequence, because two of them are hard limits on
what Pythie can say:

  - below three recordings a voice print captures the microphone rather than
    the voice, so it yields confident wrong attributions. No print means no
    attribution, which means no verdict imputed to anyone.
  - with no stored manifesto, the coherence axis simply does not apply.

Run it before a debate and publish the output next to the verdicts.

    python scripts/coverage_report.py
    python scripts/coverage_report.py --json
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CANDIDATES = ROOT / "corpus" / "candidats"

SECTIONS = ("programme", "discours", "ecrits", "votes")

# Enrolment floor. Not a fairness rule -- a validity one.
MIN_RECORDINGS = 3


def count_files(directory: Path) -> int:
    if not directory.is_dir():
        return 0
    return sum(1 for p in directory.iterdir() if p.is_file() and p.name != ".gitkeep")


def read_profile(folder: Path) -> dict:
    path = folder / "profil.yaml"
    if not path.exists():
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return {}


def collect() -> list[dict]:
    folders = sorted(
        p for p in CANDIDATES.iterdir()
        if p.is_dir() and not p.name.startswith("_")
    )
    rows = []
    for folder in folders:
        profile = read_profile(folder)
        counts = {section: count_files(folder / section) for section in SECTIONS}
        rows.append({
            "id": folder.name,
            "nom": profile.get("nom_affiche", folder.name),
            "parti": profile.get("parti", ""),
            "counts": counts,
            "total": sum(counts.values()),
            "recordings": counts["discours"],
            "voice_enrolable": counts["discours"] >= MIN_RECORDINGS,
            "coherence_available": counts["programme"] > 0,
        })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true",
                        help="machine-readable, to publish alongside verdicts")
    args = parser.parse_args()

    rows = collect()
    if not rows:
        print("aucun dossier candidat", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps({
            "generated_on": date.today().isoformat(),
            "min_recordings": MIN_RECORDINGS,
            "candidates": rows,
        }, ensure_ascii=False, indent=2))
        return

    width = max(len(r["nom"]) for r in rows)
    header = f"{'candidat'.ljust(width)}  " + "  ".join(s[:4].rjust(5) for s in SECTIONS)
    print(header + "   total   voix   coherence")
    print("-" * (len(header) + 26))

    for row in sorted(rows, key=lambda r: -r["total"]):
        cells = "  ".join(str(row["counts"][s]).rjust(5) for s in SECTIONS)
        voice = "ok" if row["voice_enrolable"] else f"-{MIN_RECORDINGS - row['recordings']}"
        coherence = "ok" if row["coherence_available"] else "non"
        print(f"{row['nom'].ljust(width)}  {cells}  {str(row['total']).rjust(6)}"
              f"   {voice.rjust(4)}   {coherence.rjust(9)}")

    totals = [r["total"] for r in rows]
    print()
    print(f"dossiers            : {len(rows)}")
    print(f"pieces au total     : {sum(totals)}")
    print(f"mediane par dossier : {statistics.median(totals):.0f}")

    no_voice = [r["nom"] for r in rows if not r["voice_enrolable"]]
    no_coherence = [r["nom"] for r in rows if not r["coherence_available"]]

    print()
    if no_voice:
        print(f"Pas d'empreinte vocale possible ({MIN_RECORDINGS} enregistrements requis) :")
        print("  " + ", ".join(no_voice))
        print("  -> leurs prises de parole ne seront pas attribuees, donc pas jugees.")
    if no_coherence:
        print("Pas de programme stocke :")
        print("  " + ", ".join(no_coherence))
        print("  -> l'axe coherence ne s'applique pas a leurs engagements.")
    if not no_voice and not no_coherence:
        print("Tous les dossiers permettent attribution et coherence.")


if __name__ == "__main__":
    main()
