#!/usr/bin/env python
"""Fabrique la page d'écoute de contrôle : une voix, trois extraits, un nom.

    python scripts/confirmation_page.py

Lit `data/empreintes/confirmation.yaml` (produit par `scripts/enrol.py`), coupe
les extraits, les encode DANS la page, et écrit un fichier HTML autonome.

Pourquoi tout embarquer plutôt que pointer vers des fichiers : la page est
destinée à être publiée et ouverte ailleurs que sur cette machine. Un lecteur
audio qui pointe vers `data/empreintes/...` ne jouerait rien.

Ce que la page rend en sortie est un YAML qui se recolle tel quel dans
`confirmation.yaml`, avec en plus les bornes éventuelles : quand une seule
partie de l'extrait est du locuteur nommé, le reste est retiré de l'empreinte.
"""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

SAMPLE_BITRATE = "32k"   # parole mono : intelligible, et la page reste légère
MAX_SECONDS = 18.0


def cut(wav: Path, start: float, seconds: float) -> bytes:
    """Un extrait mp3, en mémoire."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "clip.mp3"
        subprocess.run(
            ["ffmpeg", "-nostdin", "-loglevel", "error", "-y",
             "-ss", f"{start:.2f}", "-t", f"{seconds:.2f}", "-i", str(wav),
             "-ac", "1", "-b:a", SAMPLE_BITRATE, str(out)],
            check=True,
        )
        return out.read_bytes()


def spoken_text(blocks: list[dict], start: float, end: float) -> str:
    """Ce qui est dit pendant l'extrait, d'après la transcription de référence.

    Le texte aide autant que le son : on reconnaît souvent un intervenant à ce
    qu'il dit avant de le reconnaître à sa voix.
    """
    said = [b["texte"] for b in blocks if b["fin"] > start and b["debut"] < end]
    text = " ".join(said).strip()
    return text[:400] + ("…" if len(text) > 400 else "")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--confirmation", default="data/empreintes/confirmation.yaml")
    ap.add_argument("--wav", default="data/audio/laref2026.wav")
    ap.add_argument("--transcription", default="data/laref2026.whisper.json")
    ap.add_argument("--plateau", default="data/laref2026.plateau.yaml")
    ap.add_argument("--sortie", default="data/ecoute_de_controle.html")
    ap.add_argument("--gabarit", default="scripts/confirmation_page.html")
    args = ap.parse_args()

    confirmation = yaml.safe_load(Path(args.confirmation).read_text(encoding="utf-8"))
    panel = yaml.safe_load(Path(args.plateau).read_text(encoding="utf-8"))
    blocks = json.loads(Path(args.transcription).read_text(encoding="utf-8"))["blocs"]

    clusters = []
    for grappe in confirmation["grappes"]:
        extraits = []
        for clip in grappe["ecouter"]:
            # Le minutage est dans le nom de fichier produit par enrol.py ; on
            # repart de la seconde exacte portée par le lien video.
            start = float(clip["video"].rsplit("&t=", 1)[1].rstrip("s"))
            seconds = MAX_SECONDS
            audio = cut(Path(args.wav), start, seconds)
            extraits.append({
                "debut": start,
                "duree": seconds,
                "minutage": clip["minutage"],
                "video": clip["video"],
                "texte": spoken_text(blocks, start, start + seconds),
                "audio": "data:audio/mpeg;base64," + base64.b64encode(audio).decode(),
            })
            print(f"  grappe {grappe['grappe']:3} · {clip['minutage']:>7} · "
                  f"{len(audio) // 1024} Ko", file=sys.stderr)

        clusters.append({
            "grappe": grappe["grappe"],
            "nomSuggere": grappe["nom_suggere"],
            "idSuggere": grappe["id_suggere"],
            "part": grappe["part_des_mentions"],
            "mentions": grappe["mentions"],
            "minutes": round(grappe["secondes"] / 60),
            "segments": grappe["segments"],
            "extraits": extraits,
        })

    people = [{"id": p["id"], "nom": p["nom"], "role": p["role"],
               "analyse": bool(p.get("analyse"))}
              for p in panel["intervenants"]]

    payload = {
        "debat": panel.get("titre", ""),
        "video": panel.get("source", ""),
        "intervenants": people,
        "grappes": clusters,
    }

    template = Path(args.gabarit).read_text(encoding="utf-8")
    page = template.replace("/*__DONNEES__*/null",
                            json.dumps(payload, ensure_ascii=False))
    sortie = Path(args.sortie)
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_text(page, encoding="utf-8")
    print(f"\n{len(clusters)} grappes, "
          f"{sum(len(c['extraits']) for c in clusters)} extraits -> {sortie} "
          f"({sortie.stat().st_size // 1024} Ko)", file=sys.stderr)


if __name__ == "__main__":
    main()
