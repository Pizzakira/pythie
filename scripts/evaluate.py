#!/usr/bin/env python
"""Confronte la chaîne au jeu étalon.

    python scripts/evaluate.py ETUDES/etalon/laref2026.yaml            # chaîne complète
    python scripts/evaluate.py ETUDES/etalon/laref2026.yaml --seuils   # seuils seuls, sans modèle

Deux mesures, et elles ne demandent pas la même chose.

`--seuils` ne fait tourner AUCUN modèle : il part des couples de valeurs
étiquetés à la main — « 45,3 % » contre 43,6 % — et regarde quelle barre
reproduit les étiquettes. C'est ce que réclame METHODE §2, et cela ne dépend
d'aucune sortie de modèle, donc d'aucun aléa.

Le mode complet fait tourner routage et vérification sur chaque énoncé, puis
compare. Il exige `llama-server`.

ORDRE DE LECTURE DES MÉTRIQUES, imposé par METHODE §5 : la couverture d'abord.
Un système qui s'abstient sur tout ne se trompe jamais, et son taux d'accord
porte sur une population qu'il a choisie lui-même.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pythie import retrieval  # noqa: E402
from pythie.backend import BackendError, LocalBackend  # noqa: E402
from pythie.numbers import Kind, quantities  # noqa: E402
from pythie.schema import Statement, Verdict  # noqa: E402
from pythie.verify import verify  # noqa: E402

# En dessous, un taux ne se lit pas. Posé d'avance, et le banc refuse de
# conclure plutôt que de publier une courbe qui aurait l'air d'une mesure.
MIN_ITEMS_PAR_CLASSE = 10

# Barres balayées. Les valeurs actuellement publiées sont dans la liste, sans
# privilège.
BARRES_POINTS = [0.1, 0.2, 0.3, 0.5, 1.0, 2.0]
BARRES_RELATIVES = [0.01, 0.02, 0.05, 0.10, 0.25]


def charger(chemin: Path) -> list[dict]:
    return yaml.safe_load(chemin.read_text(encoding="utf-8"))["items"]


def couple(item: dict) -> tuple[float, float, str] | None:
    """Le couple (valeur énoncée, valeur source) et son unité de comparaison.

    Renvoie None dès qu'il manque une des deux : un item sans couple n'entre
    dans aucun balayage de seuil, et c'est le cas de la majorité — abstentions,
    définitions incompatibles, engagements.
    """
    dite = quantities(str(item.get("valeur_enoncee") or ""))
    source = quantities(str(item.get("valeur_source") or ""))
    if not dite or not source:
        return None
    a, b = dite[0], source[0]
    if a.kind is Kind.PERCENT and b.kind is Kind.PERCENT:
        return a.value, b.value, "points"
    if a.kind is Kind.YEAR or b.kind is Kind.YEAR:
        return None
    return a.value, b.value, "relatif"


def verdict_par_seuils(gap: float, unite: str, exact: float,
                       approx: float) -> str:
    """Ce que rendrait le programme pour cet écart, à ces barres.

    On ne modélise ici que la part mécanique : au-delà de la bande
    approximative, c'est le modèle qui tranche, et le balayage ne prétend pas
    le simuler — l'item est compté comme « au-delà », pas comme « faux ».
    """
    if gap <= exact:
        return "exact"
    if gap <= approx:
        return "approximate"
    return "au-dela"


def balayer(items: list[dict]) -> dict:
    """Quelle barre reproduit les étiquettes ? Sur les items qui en dépendent."""
    # Seuls entrent au balayage les items qu'une barre peut trancher. Un
    # `conflicting_sources` ou un `out_of_scope` ne se produit par aucun seuil :
    # les compter, c'est mesurer sur chaque barre un echec qui ne lui appartient
    # pas, et faire baisser toutes les barres de la meme quantite.
    tranchables = ("exact", "approximate", "false")
    couples = []
    for item in items:
        if str(item["verdict_attendu"]) not in tranchables:
            continue
        pair = couple(item)
        if pair is None:
            continue
        dite, source, unite = pair
        gap = abs(dite - source) if unite == "points" else (
            abs(dite - source) / abs(source) if source else 0.0)
        couples.append({
            "id": item["id"],
            "unite": unite,
            "ecart": gap,
            "attendu": str(item["verdict_attendu"]),
            "robustesse": item.get("robustesse", ""),
            "origine": item.get("origine", ""),
        })

    lignes = []
    for unite, barres in (("points", BARRES_POINTS), ("relatif", BARRES_RELATIVES)):
        concernes = [c for c in couples if c["unite"] == unite]
        for exact in barres:
            for approx in [b for b in barres if b > exact]:
                accords = 0
                for c in concernes:
                    rendu = verdict_par_seuils(c["ecart"], unite, exact, approx)
                    attendu = c["attendu"]
                    # « au-dela » ne peut valider qu'une étiquette qui n'est ni
                    # exacte ni approximative : le modèle a le dernier mot là.
                    if rendu == attendu or (
                            rendu == "au-dela" and attendu in ("false",)):
                        accords += 1
                lignes.append({
                    "unite": unite, "exact": exact, "approximatif": approx,
                    "items": len(concernes), "accords": accords,
                })
    return {"couples": couples, "balayage": lignes}


def mode_seuils(items: list[dict]) -> None:
    resultat = balayer(items)
    couples = resultat["couples"]

    ecartes = len(items) - len(couples)
    print(f"{len(couples)} couples de valeurs tranchables par un seuil "
          f"({ecartes} items ecartes : aucune barre ne les produit)",
          file=sys.stderr)
    for c in couples:
        ecart = (f"{c['ecart']:.2f} point" if c["unite"] == "points"
                 else f"{c['ecart']:.1%}")
        print(f"  {c['id']:26} {ecart:>12}  attendu {c['attendu']:14} "
              f"({c['robustesse']})", file=sys.stderr)


    print(file=sys.stderr)
    for unite in ("points", "relatif"):
        concernes = [c for c in couples if c["unite"] == unite]
        if not concernes:
            continue
        print(f"--- barres en {unite} : {len(concernes)} items ---", file=sys.stderr)
        for ligne in resultat["balayage"]:
            if ligne["unite"] != unite or not ligne["items"]:
                continue
            marque = " <-- publie" if (
                (unite == "points" and ligne["exact"] == 0.3
                 and ligne["approximatif"] == 1.0)
                or (unite == "relatif" and ligne["exact"] == 0.05
                    and ligne["approximatif"] == 0.25)) else ""
            print(f"  exact <= {ligne['exact']:<5} approx <= {ligne['approximatif']:<5} "
                  f"-> {ligne['accords']}/{ligne['items']} etiquettes reproduites"
                  f"{marque}", file=sys.stderr)

    sortie = Path("data/etalon_seuils.json")
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_text(json.dumps(resultat, ensure_ascii=False, indent=2),
                      encoding="utf-8")

    disponibles = max(len([c for c in couples if c["unite"] == u])
                      for u in ("points", "relatif"))
    print(f"\nAUCUNE VALEUR N'EST RETENUE. Il faudrait au moins "
          f"{MIN_ITEMS_PAR_CLASSE} couples par unite de comparaison pour "
          f"distinguer deux barres ; il y en a {disponibles} au mieux.\n"
          f"Ce tableau montre la forme de la mesure, pas son resultat.\n"
          f"Ce qui debloque : elargir le corpus, puis etiqueter un second debat.",
          file=sys.stderr)
    print(f"\n-> {sortie}", file=sys.stderr)


def mode_complet(items: list[dict], limite: int) -> None:
    backend = LocalBackend()
    ok, detail = backend.available()
    if not ok:
        sys.exit(f"backend indisponible : {detail}\n"
                 "Le mode complet exige llama-server. Le mode --seuils, non.")
    print(f"backend -- {detail}", file=sys.stderr)

    base = retrieval.load()
    resultats = []
    a_juger = [i for i in items if i.get("atteignable_aujourdhui") != "non"]
    connus_impossibles = len(items) - len(a_juger)
    if limite:
        a_juger = a_juger[:limite]

    for index, item in enumerate(a_juger, 1):
        statement = Statement(id=item["id"], speaker="inconnu",
                              text=item["enonce"], start=0, end=len(item["enonce"]))
        try:
            resultat = verify(backend, base, statement)
            rendu = resultat.verdict.value
        except BackendError as error:
            print(f"  [{index}] backend : {error}", file=sys.stderr)
            rendu = "erreur"
        attendu = str(item["verdict_attendu"])
        resultats.append({"id": item["id"], "attendu": attendu, "rendu": rendu,
                          "robustesse": item.get("robustesse", ""),
                          "origine": item.get("origine", "")})
        marque = "ok" if rendu == attendu else "≠"
        print(f"  [{index}/{len(a_juger)}] {marque:2} {item['id']:26} "
              f"attendu {attendu:20} rendu {rendu}", file=sys.stderr)

    # --- couverture d'abord (METHODE §5) ---------------------------------
    abstentions = sum(1 for r in resultats if r["rendu"] == Verdict.UNVERIFIED.value)
    attendues = sum(1 for r in resultats if r["attendu"] == Verdict.UNVERIFIED.value)
    mecaniques = [r for r in resultats if r["robustesse"] == "mecanique"]
    justes = sum(1 for r in mecaniques if r["rendu"] == r["attendu"])

    # Le seul taux qui ne se discute pas : un rouge sur un énoncé qui n'en
    # attendait pas est la faute que tout le projet existe pour éviter.
    faux_rouges = [r for r in resultats
                   if r["rendu"] == Verdict.FALSE.value
                   and r["attendu"] != Verdict.FALSE.value]

    print(f"\n--- couverture ---", file=sys.stderr)
    print(f"  items jugés            {len(resultats)}", file=sys.stderr)
    print(f"  items connus hors portée {connus_impossibles} (attribution absente)",
          file=sys.stderr)
    print(f"  abstentions rendues    {abstentions} — attendues {attendues}",
          file=sys.stderr)
    print(f"\n--- exactitude, sur les seuls items mécaniques ---", file=sys.stderr)
    print(f"  {justes}/{len(mecaniques)} étiquettes reproduites", file=sys.stderr)
    print(f"  faux rouges            {len(faux_rouges)} "
          f"{[r['id'] for r in faux_rouges]}", file=sys.stderr)

    sortie = Path("data/etalon_resultat.json")
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_text(json.dumps({"resultats": resultats}, ensure_ascii=False,
                                 indent=2), encoding="utf-8")
    print(f"\n→ {sortie}", file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("etalon", nargs="?", default="ETUDES/etalon/laref2026.yaml")
    ap.add_argument("--seuils", action="store_true",
                    help="balayage des barres sur les couples de valeurs, sans modèle")
    ap.add_argument("--limite", type=int, default=0)
    args = ap.parse_args()

    items = charger(Path(args.etalon))
    if args.seuils:
        mode_seuils(items)
    else:
        mode_complet(items, args.limite)


if __name__ == "__main__":
    main()
