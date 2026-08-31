#!/usr/bin/env python
"""Récupère une transcription horodatée depuis YouTube via yt-dlp.

On ne télécharge PAS la vidéo : uniquement la piste de sous-titres. Et on ne
republie pas la transcription intégrale — seuls les extraits effectivement
analysés sont affichés. Reproduire in extenso un débat diffusé serait une
reproduction d'une œuvre protégée.

    python scripts/fetch_transcript.py <url> --sortie data/laref2026.json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def recuperer_vtt(url: str, langue: str = "fr") -> str:
    """Télécharge les sous-titres (manuels si disponibles, sinon automatiques)."""
    with tempfile.TemporaryDirectory() as tmp:
        gabarit = str(Path(tmp) / "sub")
        commande = [
            "yt-dlp", "--skip-download",
            "--write-subs", "--write-auto-subs",
            "--sub-langs", f"{langue},{langue}-orig",
            "--sub-format", "vtt",
            "-o", gabarit, url,
        ]
        res = subprocess.run(commande, capture_output=True, text=True)
        fichiers = sorted(Path(tmp).glob("*.vtt"))
        if not fichiers:
            raise SystemExit(
                "Aucun sous-titre récupéré.\n"
                f"yt-dlp: {res.stderr.strip()[:600]}\n"
                "Si la vidéo n'a pas de piste, il faut passer par une "
                "transcription ASR — c'est ce que testera le POC 1."
            )
        return fichiers[0].read_text(encoding="utf-8", errors="replace")


HORODATAGE = re.compile(
    r"(\d{2}):(\d{2}):(\d{2})[.,](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[.,](\d{3})"
)
BALISE = re.compile(r"<[^>]+>")


def _secondes(h: str, m: str, s: str, ms: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def parser_vtt(vtt: str) -> list[dict]:
    """Extrait des segments horodatés, en supprimant les doublons de défilement
    propres aux sous-titres automatiques."""
    segments: list[dict] = []
    debut = fin = None
    lignes: list[str] = []

    def vider() -> None:
        if debut is None or not lignes:
            return
        texte = " ".join(lignes).strip()
        texte = BALISE.sub("", texte)
        texte = re.sub(r"\s+", " ", texte)
        if texte and (not segments or segments[-1]["texte"] != texte):
            segments.append({"debut": debut, "fin": fin, "texte": texte})

    for ligne in vtt.splitlines():
        m = HORODATAGE.search(ligne)
        if m:
            vider()
            lignes = []
            debut = _secondes(*m.groups()[:4])
            fin = _secondes(*m.groups()[4:])
        elif ligne.strip() and not ligne.startswith(("WEBVTT", "Kind:", "Language:", "NOTE")):
            lignes.append(ligne.strip())
    vider()
    return segments


def fusionner(segments: list[dict], secondes: float = 30.0) -> list[dict]:
    """Regroupe en blocs d'environ `secondes`.

    Les sous-titres automatiques n'identifient pas les locuteurs : le champ
    reste à renseigner à la main pour le POC. C'est justement la diarisation
    que le POC 1 devra tester.
    """
    blocs: list[dict] = []
    for seg in segments:
        if blocs and seg["fin"] - blocs[-1]["debut"] < secondes:
            blocs[-1]["texte"] += " " + seg["texte"]
            blocs[-1]["fin"] = seg["fin"]
        else:
            blocs.append({**seg, "locuteur": "inconnu"})
    return blocs


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("url")
    ap.add_argument("--sortie", default="data/transcript.json")
    ap.add_argument("--langue", default="fr")
    ap.add_argument("--bloc", type=float, default=30.0)
    args = ap.parse_args()

    print(f"Récupération des sous-titres : {args.url}", file=sys.stderr)
    blocs = fusionner(parser_vtt(recuperer_vtt(args.url, args.langue)), args.bloc)

    sortie = Path(args.sortie)
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_text(
        json.dumps({"source": args.url, "blocs": blocs}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    duree = blocs[-1]["fin"] / 60 if blocs else 0
    mots = sum(len(b["texte"].split()) for b in blocs)
    print(
        f"{len(blocs)} blocs · {duree:.0f} min · {mots} mots → {sortie}\n"
        "Locuteurs à renseigner à la main (les sous-titres auto ne les donnent pas).",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
