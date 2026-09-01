#!/usr/bin/env python
"""Reporte dans `confirmation.yaml` ce que la page d'écoute a enregistré.

    python scripts/confirmation_merge.py data/empreintes/ecoute.json

`ecoute.json` est le document que la page écrit dans la base de l'artefact
après chaque geste (`ecoute/<debat>`) : l'état entier du découpage, indexé
par « grappe:extrait ». Il se relit depuis la session Claude Code qui a publié
la page (lecture de la base), ou se colle à la main depuis « Copier le
résultat » — les deux chemins mènent ici.

Ce script refait en Python ce que la page fait en JavaScript pour produire son
YAML : mêmes règles, mêmes noms. Il n'invente rien : `morceaux` sont les
segments nommés des extraits exploitables, `inutilisables` les extraits
écartés avec leur motif, `confirme` le nom unique quand trois extraits
exploitables s'accordent — sinon `plusieurs`, sinon vide.

Puis : scripts/enrol.py ... --confirmer data/empreintes/confirmation.yaml
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from confirmation_page import MAX_SECONDS, clip_start  # noqa: E402

SHOWN = 3            # extraits à écouter ; les suivants sont de réserve
REASONS = {"superposition": "voix melees", "applaudissements": "applaudissements",
           "inaudible": "son inaudible"}


def dominant(segments: list[dict]) -> str:
    """Le nom qui tient le plus de secondes dans l'extrait, ou ''."""
    held: dict[str, float] = {}
    for seg in segments or []:
        if seg.get("who") and not seg.get("bad"):
            held[seg["who"]] = held.get(seg["who"], 0.0) + float(seg["b"]) - float(seg["a"])
    return max(held, key=held.get) if held else ""


def active_clips(clips: list[dict], entries: dict[int, dict]) -> list[int]:
    """Les trois premiers exploitables, en puisant dans la réserve à chaque
    extrait écarté — la même règle que la page."""
    active, usable = [], 0
    for index in range(len(clips)):
        if usable >= SHOWN:
            break
        active.append(index)
        if not entries.get(index, {}).get("inutilisable"):
            usable += 1
    return active


def merge(confirmation: dict, state: dict) -> dict:
    for grappe in confirmation["grappes"]:
        clips = grappe["ecouter"]
        entries = {}
        for index in range(len(clips)):
            entry = state.get(f"{grappe['grappe']}:{index}")
            if entry:
                entries[index] = entry

        morceaux, ecartes, answers, usable = [], [], [], 0
        for index in active_clips(clips, entries):
            start = clip_start(clips[index])
            entry = entries.get(index, {})
            reason = entry.get("inutilisable") or ""
            if reason:
                ecartes.append([round(start, 1), round(start + MAX_SECONDS, 1), reason])
                continue
            usable += 1
            segments = entry.get("segments") or []
            for seg in segments:
                if seg.get("bad"):
                    ecartes.append([round(start + float(seg["a"]), 1),
                                    round(start + float(seg["b"]), 1), seg["bad"]])
                elif seg.get("who"):
                    morceaux.append([round(start + float(seg["a"]), 1),
                                     round(start + float(seg["b"]), 1), seg["who"]])
            who = dominant(segments)
            if who:
                answers.append(who)

        unique = sorted(set(answers))
        if not usable:
            confirme = ""
        elif len(unique) > 1:
            confirme = "plusieurs"
        elif len(answers) == usable and usable >= SHOWN:
            confirme = unique[0]
        else:
            confirme = ""

        grappe["confirme"] = confirme
        grappe["morceaux"] = morceaux
        grappe["inutilisables"] = ecartes
        if not morceaux:
            del grappe["morceaux"]
        if not ecartes:
            del grappe["inutilisables"]
    return confirmation


HEADER = (
    "# Une minute d'ecoute par voix, et l'attribution devient utilisable.\n"
    "#\n"
    "# Rempli par scripts/confirmation_merge.py depuis l'etat enregistre par la\n"
    "# page d'ecoute. `morceaux` : [debut, fin, qui] en secondes depuis le debut\n"
    "# du debat ; `inutilisables` : [debut, fin, motif] ; `confirme` : le nom\n"
    "# unique quand trois extraits exploitables s'accordent.\n"
    "#\n"
    "# Puis : scripts/enrol.py ... --confirmer data/empreintes/confirmation.yaml\n\n"
)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("etat", help="document JSON ecrit par la page (ecoute/<debat>)")
    ap.add_argument("--confirmation", default="data/empreintes/confirmation.yaml")
    ap.add_argument("--sortie", default="", help="par defaut, --confirmation est reecrit")
    args = ap.parse_args()

    document = json.loads(Path(args.etat).read_text(encoding="utf-8"))
    state = document.get("etat", document)
    if document.get("misAJour"):
        print(f"etat enregistre le {document['misAJour']}", file=sys.stderr)

    path = Path(args.confirmation)
    confirmation = merge(yaml.safe_load(path.read_text(encoding="utf-8")), state)

    for grappe in confirmation["grappes"]:
        print(f"  grappe {grappe['grappe']:3} {grappe['nom_suggere']:22} "
              f"-> {grappe['confirme'] or '(en cours)':12} "
              f"{len(grappe.get('morceaux', [])):2} morceaux, "
              f"{len(grappe.get('inutilisables', []))} ecarte(s)", file=sys.stderr)

    sortie = Path(args.sortie) if args.sortie else path
    sortie.write_text(
        HEADER + yaml.safe_dump(confirmation, allow_unicode=True, sort_keys=False),
        encoding="utf-8")
    print(f"-> {sortie}", file=sys.stderr)


if __name__ == "__main__":
    main()
