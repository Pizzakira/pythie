#!/usr/bin/env python
"""Enrôle les voix du plateau sans que personne ait à écouter le débat.

    /c/ProgramData/anaconda3/envs/whisperx/python.exe scripts/enrol.py \\
        data/audio/laref2026.wav data/laref2026.whisper.json \\
        --plateau data/laref2026.plateau.yaml

Protocole figé avant exécution : `ETUDES/preinscription-empreintes.md`.

On ne reconnaît pas les voix, on les REGROUPE, et on laisse le débat les nommer :
un patronyme prononcé juste avant une prise de parole désigne presque toujours
celui qui va parler. C'est l'usage que D-041 autorise pour le signal des noms —
étiqueter des grappes, jamais réécrire du texte.

Ce que ce script produit est PROVISOIRE : chaque empreinte porte
`verifie_par_humain: false` et n'autorise aucun verdict tant que quelqu'un n'a
pas écouté un extrait par voix. Le script écrit ces extraits à confirmer.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pythie.media.embed import Embedder, Window, cosine  # noqa: E402
from pythie.media.voiceprint import Registry, Role  # noqa: E402

# Pré-inscrits. Ne pas modifier après avoir vu un résultat.
DISTANCES = [0.30, 0.40, 0.50, 0.60, 0.70]
MIN_NAME_SHARE = 0.60
MIN_MENTIONS = 3
MIN_COHESION = 0.60
MAX_CROSS = 0.50
MIN_CLUSTERS = 8
MIN_CANDIDATES = 4

# Une mention nomme ce qui SUIT, dans cette fenêtre. « Alors X, … » puis la
# question de l'animateur, puis la réponse : le nom précède la prise de parole
# de plusieurs secondes, et parfois de plusieurs dizaines.
LOOKAHEAD = (5.0, 90.0)


def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text.lower())
                   if unicodedata.category(c) != "Mn")


def surname_forms(nom: str) -> list[str]:
    """Le patronyme et ce que l'ASR en fait.

    On ne cherche que le nom de famille : les prénoms sont trop communs
    (« Marine » désigne deux personnes sur ce plateau) et les formes ASR
    déformées restent reconnaissables sur le patronyme.

    LE PATRONYME EST TOUT CE QUI SUIT LE PRÉNOM, pas le dernier mot. Prendre le
    dernier mot réduisait « Marine Le Pen » à « pen », trois lettres, écarté par
    le garde-fou de longueur : la candidate était **invisible** au mécanisme
    entier, et aucune de ses prises de parole ne pouvait être nommée. Le défaut
    ne se voyait pas dans un taux — il se voyait en lisant la liste des grappes
    et en n'y trouvant jamais son nom.
    """
    parts = strip_accents(nom).split()
    surname = " ".join(parts[1:]) if len(parts) > 1 else parts[0]
    return [surname, surname.replace("-", " ")]


def mentions(blocks: list[dict], panel: list[dict]) -> list[dict]:
    """Où chaque patronyme est prononcé, avec l'instant de la mention."""
    found = []
    for block in blocks:
        text = strip_accents(block["texte"])
        for person in panel:
            for form in surname_forms(person["nom"]):
                if len(form) >= 4 and form in text:
                    found.append({"id": person["id"], "nom": person["nom"],
                                  "role": person["role"], "t": block["debut"],
                                  "fin": block["fin"]})
                    break
    return found


def label_clusters(labels: np.ndarray, starts: np.ndarray, ends: np.ndarray,
                   durations: np.ndarray, cited: list[dict]) -> dict[int, dict]:
    """Quel nom les mentions désignent-elles, grappe par grappe.

    UNE MENTION = UNE VOIX, POUR UNE SEULE GRAPPE : la première voix qui prend
    la parole après le nom, ET QUI N'EST PAS CELLE QUI VIENT DE LE PRONONCER.

    Celui qui dit « Alors Jean-Luc Mélenchon, … » n'est jamais Mélenchon : il
    pose la question. Faire voter la grappe dominante des quatre-vingt-dix
    secondes suivantes revenait souvent à voter pour l'animateur, qui occupe
    la fenêtre avec sa question. Exclure la voix qui prononce le nom fait
    monter la concentration de chaque grappe — mesuré : Retailleau passe de
    57 % à 75 %, Glucksmann de 58 % à 88 %.

    La première version faisait voter chaque mention pour TOUTES les grappes
    présentes dans les quatre-vingt-dix secondes suivantes — soit une dizaine.
    Chaque nom se retrouvait dispersé sur dix grappes, et chaque grappe
    recevait une voix de dix noms différents : aucun patronyme ne pouvait
    atteindre 60 % des mentions, quel que soit le débat. Le critère était
    insatisfaisable par construction, et le banc aurait échoué même sur du
    matériel parfait. Défaut d'instrument, pas résultat.

    Un même patronyme prononcé deux fois au même endroit ne compte toujours
    qu'une fois : une question insistante n'est pas deux témoignages.
    """
    votes: dict[int, list[tuple[str, float]]] = {}
    for mention in cited:
        speaking = np.where((starts <= mention["t"]) & (ends >= mention["t"]))[0]
        asker = int(labels[speaking[0]]) if len(speaking) else None

        lo, hi = mention["fin"] + LOOKAHEAD[0], mention["fin"] + LOOKAHEAD[1]
        window = np.where((starts >= lo) & (starts <= hi))[0]
        if not len(window):
            continue

        occupancy: dict[int, float] = {}
        for position in window:
            cluster = int(labels[position])
            occupancy[cluster] = occupancy.get(cluster, 0.0) + float(durations[position])

        # Au moins dix secondes de parole : un « oui » jeté entre deux phrases
        # ne fait pas une prise de parole, et son empreinte serait du bruit.
        others = {c: seconds for c, seconds in occupancy.items()
                  if c != asker and seconds >= 10.0}
        if not others:
            continue
        votes.setdefault(max(others, key=others.get), []).append(
            (mention["id"], mention["t"]))

    result = {}
    for cluster, entries in votes.items():
        distinct: dict[str, set] = {}
        for speaker, when in entries:
            # Deux mentions à moins de 30 s l'une de l'autre sont la même
            # occasion, pas deux témoignages.
            bucket = distinct.setdefault(speaker, set())
            if not any(abs(when - other) < 30 for other in bucket):
                bucket.add(when)
        counts = Counter({k: len(v) for k, v in distinct.items()})
        total = sum(counts.values()) or 1
        winner, best = counts.most_common(1)[0]
        result[cluster] = {"id": winner, "mentions": best,
                           "share": best / total, "detail": dict(counts)}
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("wav")
    ap.add_argument("transcription")
    ap.add_argument("--plateau", default="data/laref2026.plateau.yaml")
    ap.add_argument("--min-segment", type=float, default=3.0)
    ap.add_argument("--sortie", default="data/empreintes/resultat.json")
    ap.add_argument("--extraits", default="data/empreintes/a_confirmer",
                    help="dossier ou ecrire un extrait par voix, pour ecoute humaine")
    ap.add_argument("--recalculer", action="store_true",
                    help="recalcule les empreintes au lieu de relire le cache")
    ap.add_argument("--confirmer", default="",
                    help="fichier de confirmation rempli a l'oreille : ecrit "
                         "alors des empreintes VERIFIEES")
    ap.add_argument("--ecrire-registre", action="store_true",
                    help="ecrit les empreintes sous corpus/voiceprints/")
    args = ap.parse_args()

    panel = yaml.safe_load(Path(args.plateau).read_text(encoding="utf-8"))
    people = {p["id"]: p for p in panel["intervenants"]}
    blocks = json.loads(Path(args.transcription).read_text(encoding="utf-8"))["blocs"]

    # --- 1. un vecteur par segment assez long ------------------------------
    windows = [Window(b["debut"], b["fin"]) for b in blocks]
    long_enough = [i for i, w in enumerate(windows)
                   if w.duration >= args.min_segment]
    print(f"{len(blocks)} segments, {len(long_enough)} d'au moins "
          f"{args.min_segment:.0f} s", file=sys.stderr)

    # Le calcul des empreintes coûte quelques minutes de GPU ; le regroupement
    # et l'étiquetage se rejouent en une seconde. On garde donc les vecteurs :
    # sans cela, chaque question posée aux données se paie en temps de calcul,
    # et on finit par ne plus poser de questions.
    cache = Path(args.sortie).parent / "vecteurs.npz"
    if cache.exists() and not args.recalculer:
        stored = np.load(cache)
        vectors, index = stored["v"], [int(i) for i in stored["i"]]
        print(f"vecteurs relus de {cache}", file=sys.stderr)
    else:
        embedder = Embedder()
        vectors, kept = embedder.embed(args.wav, [windows[i] for i in long_enough])
        index = [long_enough[k] for k in kept]
        cache.parent.mkdir(parents=True, exist_ok=True)
        np.savez(cache, v=vectors, i=np.array(index))
    starts = np.array([windows[i].start for i in index])
    ends = np.array([windows[i].end for i in index])
    durations = np.array([windows[i].duration for i in index])
    print(f"{len(vectors)} empreintes calculees", file=sys.stderr)

    cited = mentions(blocks, list(people.values()))
    print(f"{len(cited)} mentions de patronyme reperees", file=sys.stderr)

    # --- 2. balayage de la distance de regroupement ------------------------
    from sklearn.cluster import AgglomerativeClustering

    unit = vectors / (np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-9)
    balayage = []

    for distance in DISTANCES:
        model = AgglomerativeClustering(
            n_clusters=None, distance_threshold=distance,
            metric="cosine", linkage="average",
        )
        labels = model.fit_predict(unit)
        named = label_clusters(labels, starts, ends, durations, cited)

        retained = []
        centroids = {}
        for cluster, evidence in named.items():
            members = unit[labels == cluster]
            if len(members) < 3:
                continue
            centroid = members.mean(axis=0)
            centroid /= np.linalg.norm(centroid) + 1e-9
            cohesion = float(cosine(members, centroid[None, :]).mean())
            if (evidence["share"] >= MIN_NAME_SHARE
                    and evidence["mentions"] >= MIN_MENTIONS
                    and cohesion >= MIN_COHESION):
                retained.append({"cluster": cluster, "cohesion": cohesion,
                                 "segments": int((labels == cluster).sum()),
                                 **evidence})
                centroids[cluster] = centroid

        # séparation : deux voix retenues trop proches ne sont pas deux voix
        too_close = set()
        keys = list(centroids)
        for a in range(len(keys)):
            for b in range(a + 1, len(keys)):
                similarity = float(centroids[keys[a]] @ centroids[keys[b]])
                if similarity > MAX_CROSS:
                    too_close.add(keys[a])
                    too_close.add(keys[b])
        retained = [r for r in retained if r["cluster"] not in too_close]

        # un même nom sur deux grappes : la voix est coupée en deux, on ne
        # tranche pas laquelle est la bonne
        by_name = Counter(r["id"] for r in retained)
        retained = [r for r in retained if by_name[r["id"]] == 1]

        candidates = [r for r in retained
                      if people.get(r["id"], {}).get("role") == "candidate"]
        balayage.append({
            "distance": distance,
            "grappes": int(labels.max()) + 1,
            "retenues": len(retained),
            "candidats": len(candidates),
            "ecartees_trop_proches": len(too_close),
            "detail": retained,
            "labels": labels,
        })
        print(f"  distance {distance:.2f} -> {int(labels.max()) + 1:4} grappes, "
              f"{len(retained)} nommees, {len(candidates)} candidats",
              file=sys.stderr)

    # --- 3. décision, selon la règle pré-inscrite --------------------------
    lisibles = [b for b in balayage if b["grappes"] >= MIN_CLUSTERS]
    choix = max(lisibles, key=lambda b: (b["candidats"], -b["distance"])) if lisibles else None

    if choix is None:
        print(f"\nMOINS DE {MIN_CLUSTERS} GRAPPES A TOUTES LES DISTANCES : "
              "sous-regroupement, banc non concluant.", file=sys.stderr)
        return

    print(f"\nRETENU : distance {choix['distance']:.2f}, "
          f"{choix['candidats']} candidats sur 7", file=sys.stderr)
    for entry in sorted(choix["detail"], key=lambda r: -r["segments"]):
        person = people.get(entry["id"], {})
        print(f"  {person.get('nom', entry['id']):22} "
              f"{entry['segments']:4} segments, cohesion {entry['cohesion']:.2f}, "
              f"{entry['mentions']} mentions ({entry['share']:.0%})", file=sys.stderr)

    if choix["candidats"] < MIN_CANDIDATES:
        print(f"\nBOOTSTRAP EN ECHEC : {choix['candidats']} candidats enroles, "
              f"{MIN_CANDIDATES} exiges. Le marquage a la main redevient "
              "necessaire.", file=sys.stderr)

    # --- 4. ce qui reste à faire par une oreille --------------------------
    #
    # Le bootstrap propose des noms ; il ne les vérifie pas. On écrit donc, pour
    # CHAQUE grosse grappe — y compris celles qui n'atteignent pas la barre —
    # trois moments à écouter et le nom que les mentions suggèrent. Confirmer
    # coûte une minute par voix ; ne pas confirmer coûterait une citation
    # attribuée à la mauvaise personne, que rien en aval ne rattraperait.
    labels = choix["labels"]
    named = label_clusters(labels, starts, ends, durations, cited)
    source_url = panel.get("source", "")
    extraits = Path(args.extraits)
    extraits.mkdir(parents=True, exist_ok=True)

    propositions = []
    for cluster, evidence in sorted(named.items(),
                                    key=lambda kv: -int((labels == kv[0]).sum())):
        members = np.where(labels == cluster)[0]
        if len(members) < 10:
            continue
        person = people.get(evidence["id"], {})
        longest = sorted(members, key=lambda m: -windows[index[m]].duration)[:3]
        # Trois extraits découpés pour de bon : ouvrir un wav de 370 Mo et
        # chercher 140:44 est une corvée, et une corvée ne se fait pas. Le
        # lien vidéo est là pour ceux qui préfèrent le contexte à l'extrait.
        clips = []
        for rank, member in enumerate(longest, 1):
            window = windows[index[member]]
            clip = extraits / f"grappe{cluster:03}_{rank}.mp3"
            if not clip.exists():
                subprocess.run(
                    ["ffmpeg", "-nostdin", "-loglevel", "error", "-y",
                     "-ss", f"{window.start:.2f}", "-t",
                     f"{min(window.duration, 20.0):.2f}",
                     "-i", args.wav, "-ac", "1", "-b:a", "64k", str(clip)],
                    check=False,
                )
            clips.append({
                "extrait": str(clip),
                "minutage": f"{int(window.start) // 60}:{int(window.start) % 60:02d}",
                "video": (f"{source_url}&t={int(window.start)}s"
                          if source_url else ""),
            })

        propositions.append({
            "grappe": int(cluster),
            "nom_suggere": person.get("nom", evidence["id"]),
            "id_suggere": evidence["id"],
            "part_des_mentions": round(evidence["share"], 2),
            "mentions": evidence["mentions"],
            "segments": int(len(members)),
            "secondes": round(float(sum(windows[index[m]].duration for m in members)), 1),
            "ecouter": clips,
            "confirme": "",
        })

    confirmation = Path(args.sortie).parent / "confirmation.yaml"
    confirmation.write_text(
        "# Une minute d'ecoute par voix, et l'attribution devient utilisable.\n"
        "#\n"
        "# Pour chaque grappe : ecouter les trois moments indiques dans\n"
        f"# {args.wav}, puis remplir `confirme` avec le nom entendu, ou\n"
        "# `inconnu` si ce n'est aucun des intervenants, ou `plusieurs` si la\n"
        "# grappe melange visiblement deux personnes.\n"
        "#\n"
        "# `nom_suggere` vient des patronymes prononces juste avant la prise de\n"
        "# parole. Ils orientent, ils ne prouvent pas -- c'est exactement ce que\n"
        "# votre oreille tranche.\n"
        "#\n"
        "# Puis : scripts/enrol.py ... --confirmer data/empreintes/confirmation.yaml\n\n"
        + yaml.safe_dump({"grappes": propositions}, allow_unicode=True,
                         sort_keys=False),
        encoding="utf-8")

    # --- 5. l'oreille a parlé : on écrit des empreintes vérifiées ----------
    if args.confirmer:
        rempli = yaml.safe_load(Path(args.confirmer).read_text(encoding="utf-8"))
        registry = Registry()
        confirmees, refusees = 0, 0
        for grappe in rempli.get("grappes", []):
            reponse = str(grappe.get("confirme") or "").strip()
            if not reponse or reponse.lower() in ("inconnu", "plusieurs", "non"):
                refusees += 1
                continue
            # On accepte le nom tel qu'il a été écrit, en le rattachant au
            # plateau quand c'est possible : le rôle décide qui est analysé, et
            # il ne s'invente pas.
            person = next((p for p in people.values()
                           if strip_accents(p["nom"]) == strip_accents(reponse)
                           or p["id"].lower() == reponse.lower()), None)
            members = np.where(labels == grappe["grappe"])[0]
            if len(members) < 3:
                refusees += 1
                continue
            registry.enrol(
                display_name=person["nom"] if person else reponse,
                role=person["role"] if person else Role.OTHER,
                embeddings=[vectors[m] for m in members],
                seconds=float(sum(windows[index[m]].duration for m in members)),
                sources=[f"{args.transcription} (grappe {grappe['grappe']}, "
                         f"confirmee a l'oreille)"],
                enrolled_on="2026-09-01",
                human_verified=True,
            )
            confirmees += 1

        registry.save()
        print(f"\n{confirmees} empreintes VERIFIEES ecrites, {refusees} grappes "
              "laissees de cote", file=sys.stderr)
        print("Ces empreintes-la peuvent porter une attribution.", file=sys.stderr)
        return

    if args.ecrire_registre:
        registry = Registry()
        for entry in choix["detail"]:
            person = people.get(entry["id"], {})
            members = np.where(labels == entry["cluster"])[0]
            registry.enrol(
                display_name=person.get("nom", entry["id"]),
                role=person.get("role", Role.OTHER),
                embeddings=[vectors[m] for m in members],
                seconds=float(sum(windows[index[m]].duration for m in members)),
                sources=[f"{args.transcription} (grappe {entry['cluster']}, "
                         f"{entry['mentions']} mentions)"],
                enrolled_on="2026-09-01",
                human_verified=False,
            )
        registry.save()
        print(f"\n{len(registry.prints)} empreintes ecrites sous "
              "corpus/voiceprints/ — toutes NON VERIFIEES, donc sans autorite",
              file=sys.stderr)
    else:
        print("\n(registre non ecrit : --ecrire-registre pour le faire)",
              file=sys.stderr)

    sortie = Path(args.sortie)
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_text(json.dumps({
        "audio": args.wav,
        "transcription": args.transcription,
        "segments_embarques": len(vectors),
        "mentions": len(cited),
        "criteres": {"part_du_nom": MIN_NAME_SHARE, "mentions": MIN_MENTIONS,
                     "cohesion": MIN_COHESION, "separation": MAX_CROSS},
        "balayage": [{k: v for k, v in b.items() if k != "labels"}
                     for b in balayage],
        "retenu": {k: v for k, v in choix.items() if k != "labels"},
    }, ensure_ascii=False, indent=2, default=float), encoding="utf-8")
    print(f"-> {sortie}", file=sys.stderr)
    print(f"-> {len(propositions)} grappes a confirmer a l'oreille : "
          f"{confirmation}", file=sys.stderr)


if __name__ == "__main__":
    main()
