#!/usr/bin/env python
"""Banc de la couche d'accord entre transcriptions.

    python ETUDES/banc_accord.py data/laref2026.json data/laref2026.whisper.json \\
        --famille youtube --depuis 22 --minutes 10

Protocole écrit AVANT exécution : `ETUDES/preinscription-accord.md`. Les deux
cas témoins, les valeurs balayées, les seuils de succès et la règle de décision
y sont figés. Ce script les applique, il ne les choisit pas.

Deux témoins, parce qu'une métrique qui rend zéro n'est pas une preuve
d'absence (METHODE.md §11) :

  T+  « de au feu 600 millions de dettes françaises »  → doit être bloqué
  T-  « 45,3 % de prélèvement / 57,3 % de dépenses »   → doit être confirmé

Sortie : `data/banc_accord/resultat.json`, plus un tableau lisible.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pythie import numbers, pipeline, triggers  # noqa: E402
from pythie.media import transcripts  # noqa: E402

# Pré-inscrit. Ne pas modifier après avoir vu un résultat.
PADS = [5.0, 10.0, 20.0, 30.0, 45.0]
ANCHORS = [0.0, 0.10, 0.20, 0.35, 0.50]
MIN_COVERAGE = 0.30
MIN_STATEMENTS = 20

WITNESS_POSITIVE = "au feu"        # doit être bloqué
WITNESS_NEGATIVE = ("45,3", "57,3")  # doivent être confirmés


def load_blocks(path: Path, start: float, minutes: float) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    blocks = [b for b in payload["blocs"] if b["fin"] > start]
    if minutes:
        blocks = [b for b in blocks if b["debut"] < start + minutes * 60]
    return blocks


def statements_of(blocks: list[dict]) -> tuple[list, dict]:
    """Mêmes énoncés que la chaîne réelle : le banc ne doit pas mesurer un
    découpage qui lui serait propre."""
    produced, spans = [], {}
    for block in blocks:
        made = pipeline.split(block["texte"], "inconnu",
                              start_time=block["debut"],
                              duration=block["fin"] - block["debut"])
        for statement in made:
            spans[statement.id] = (block["debut"], block["fin"])
        produced.extend(made)
    return produced, spans


def diagnose(candidates, spans, witnesses, settings) -> dict:
    """Un taux de blocage ne dit pas SA CAUSE.

    Deux causes possibles et deux remèdes opposés : soit les deux ASR entendent
    des chiffres différents — c'est le phénomène, et bloquer est juste — soit
    elles entendent la même chose à des instants différents et c'est ma fenêtre
    qui est fausse — c'est une erreur de mesure, et bloquer est un faux positif.
    Le banc du 01/09 avait rendu « 6 % de part jugeable » pour n'avoir pas posé
    cette question (METHODE.md §11).

    On cherche donc chaque chiffre bloqué dans TOUTE la transcription témoin, et
    on regarde à quelle distance temporelle il se trouve. Près : dérive
    d'alignement. Loin ou nulle part : désaccord réel.
    """
    positions = [(block.start, quantity)
                 for witness in witnesses for block in witness.blocks
                 for quantity in transcripts.quantities(block.text)
                 if quantity.kind is not numbers.Kind.YEAR]

    buckets = {"moins de 60 s": 0, "1 a 5 min": 0, "plus de 5 min": 0,
               "absent partout": 0}
    blocked = 0
    for statement in candidates:
        agreement = transcripts.corroborate(
            statement.text, *spans[statement.id], witnesses, settings)
        if agreement.status not in (transcripts.Status.DIVERGENT,
                                    transcripts.Status.ABSENT):
            continue
        blocked += 1
        start = spans[statement.id][0]
        for raw in agreement.missing:
            wanted = next((q for q in transcripts.quantities(statement.text)
                           if q.raw == raw), None)
            if wanted is None:
                continue
            elsewhere = [t for t, q in positions if wanted.matches(q)]
            if not elsewhere:
                buckets["absent partout"] += 1
                continue
            gap = abs(min(elsewhere, key=lambda t: abs(t - start)) - start)
            key = ("moins de 60 s" if gap < 60
                   else "1 a 5 min" if gap < 300 else "plus de 5 min")
            buckets[key] += 1
    return {"enonces_bloques": blocked, "chiffres_bloques": buckets}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("principale")
    ap.add_argument("temoin", nargs="+")
    ap.add_argument("--famille", default="youtube")
    ap.add_argument("--depuis", type=float, default=22.0)
    ap.add_argument("--minutes", type=float, default=10.0)
    ap.add_argument("--sortie", default="data/banc_accord/resultat.json")
    args = ap.parse_args()

    start = args.depuis * 60
    blocks = load_blocks(Path(args.principale), start, args.minutes)
    statements, spans = statements_of(blocks)
    candidates = [s for s in statements
                  if triggers.deserves_verification(s.triggers)]

    primary = transcripts.Transcript(
        name=Path(args.principale).stem, family=args.famille,
        blocks=[transcripts.Block(b["debut"], b["fin"], b["texte"]) for b in blocks],
    )
    loaded = [transcripts.Transcript.load(p) for p in args.temoin]
    witnesses = transcripts.independent(primary, loaded)
    if not witnesses:
        sys.exit("Aucun temoin d'une famille differente : rien a mesurer.")

    # Non-year figures only -- the same population the layer requires a witness
    # for. Counting years here would inflate the denominator with statements the
    # layer never asks anyone to corroborate.
    with_figures = [s for s in candidates
                    if any(q.kind is not numbers.Kind.YEAR
                           for q in transcripts.quantities(s.text))]
    print(f"fenetre {args.depuis:.0f}–{args.depuis + args.minutes:.0f} min · "
          f"{len(statements)} enonces · {len(candidates)} candidats · "
          f"{len(with_figures)} porteurs de chiffre", file=sys.stderr)
    print(f"temoins : {', '.join(f'{t.name} ({t.family})' for t in witnesses)}",
          file=sys.stderr)

    if len(with_figures) < MIN_STATEMENTS:
        print(f"\nMOINS DE {MIN_STATEMENTS} ENONCES PORTEURS DE CHIFFRE — "
              "banc declare non concluant (critere 3 de la pre-inscription).",
              file=sys.stderr)

    rows = []
    for pad in PADS:
        for anchor in ANCHORS:
            settings = transcripts.Settings(pad=pad, min_anchor=anchor)
            agreements = {
                s.id: transcripts.corroborate(
                    s.text, *spans[s.id], witnesses, settings)
                for s in candidates
            }
            summary = transcripts.report(list(agreements.values()))

            positive = [(s, agreements[s.id]) for s in candidates
                        if WITNESS_POSITIVE in s.text]
            negative = [(s, agreements[s.id]) for s in candidates
                        if any(w in s.text for w in WITNESS_NEGATIVE)]

            t_plus_blocked = all(not a.corroborated for _s, a in positive)
            t_minus_ok = bool(negative) and all(a.corroborated for _s, a in negative)
            coverage = float(summary["corroborated_share"])

            rows.append({
                "pad": pad,
                "min_anchor": anchor,
                "couverture": coverage,
                "corrobores": summary["corroborated"],
                "porteurs_de_chiffre": summary["with_figures"],
                "statuts": summary["by_status"],
                "T+_bloque": t_plus_blocked,
                "T-_confirme": t_minus_ok,
                "T+_statut": [a.status.value for _s, a in positive],
                "T-_statut": [a.status.value for _s, a in negative],
                "retenu": t_plus_blocked and coverage >= MIN_COVERAGE,
            })

    print(f"\n{'pad':>5} {'ancre':>6} {'couv.':>7} {'corrob.':>8}  T+ bloque  "
          f"T- confirme  retenu", file=sys.stderr)
    for row in rows:
        print(f"{row['pad']:5.0f} {row['min_anchor']:6.2f} "
              f"{row['couverture']:7.0%} "
              f"{row['corrobores']:3}/{row['porteurs_de_chiffre']:<4} "
              f"{'oui' if row['T+_bloque'] else 'NON':>9}  "
              f"{'oui' if row['T-_confirme'] else 'non':>11}  "
              f"{'oui' if row['retenu'] else '':>6}", file=sys.stderr)

    # Règle de décision pré-inscrite : parmi les réglages retenus, le plus
    # petit pad puis le plus grand ancrage. Le plus exigeant, jamais le plus
    # généreux à couverture égale.
    kept = [r for r in rows if r["retenu"]]
    decision = min(kept, key=lambda r: (r["pad"], -r["min_anchor"])) if kept else None

    if decision:
        print(f"\nRETENU (regle pre-inscrite) : pad={decision['pad']:.0f} s, "
              f"min_anchor={decision['min_anchor']:.2f} — couverture "
              f"{decision['couverture']:.0%}", file=sys.stderr)
        if not decision["T-_confirme"]:
            print("ATTENTION : le temoin negatif n'est PAS confirme a ce reglage. "
                  "Voir la reserve declaree dans la pre-inscription — les valeurs "
                  "du POC 1 n'ont alors jamais ete corroborees.", file=sys.stderr)
    else:
        print("\nAUCUN REGLAGE NE SATISFAIT LES DEUX CRITERES. "
              "La couche n'est pas branchee sur la publication ; D-044 reste "
              "en vigueur en bloc.", file=sys.stderr)

    # Cinq blocages, en clair : un taux ne se lit pas sans regarder ce qu'il
    # recouvre.
    settings = (transcripts.Settings(pad=decision["pad"],
                                     min_anchor=decision["min_anchor"])
                if decision else transcripts.Settings())
    examples = []
    for statement in candidates:
        agreement = transcripts.corroborate(
            statement.text, *spans[statement.id], witnesses, settings)
        if agreement.status in (transcripts.Status.DIVERGENT,
                                transcripts.Status.ABSENT):
            examples.append({
                "enonce": statement.text[:200],
                "statut": agreement.status.value,
                "manquant": agreement.missing,
                "entendu_par_le_temoin": agreement.heard_instead,
                "temoin": agreement.witness_text[:200],
            })

    cause = diagnose(candidates, spans, witnesses, settings)
    print(f"\n--- cause des blocages ({cause['enonces_bloques']} enonces) ---",
          file=sys.stderr)
    for key, value in cause["chiffres_bloques"].items():
        print(f"  chiffre retrouve ailleurs, {key:16} {value}", file=sys.stderr)

    print("\n--- cinq blocages, en clair ---", file=sys.stderr)
    for example in examples[:5]:
        print(f"\n  [{example['statut']}] {example['enonce'][:120]}", file=sys.stderr)
        print(f"    chiffre non retrouve : {example['manquant']}", file=sys.stderr)
        print(f"    temoin entend        : {example['entendu_par_le_temoin']}",
              file=sys.stderr)

    out = Path(args.sortie)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "fenetre_min": [args.depuis, args.depuis + args.minutes],
        "principale": {"fichier": args.principale, "famille": args.famille},
        "temoins": [{"nom": t.name, "famille": t.family} for t in witnesses],
        "enonces": len(statements),
        "candidats": len(candidates),
        "porteurs_de_chiffre": len(with_figures),
        "criteres": {"couverture_min": MIN_COVERAGE,
                     "enonces_min": MIN_STATEMENTS},
        "balayage": rows,
        "decision": decision,
        "cause_des_blocages": cause,
        "blocages": examples,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n→ {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
