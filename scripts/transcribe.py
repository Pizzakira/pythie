#!/usr/bin/env python
"""Transcrit un fichier audio et écrit une transcription au format du projet.

    python scripts/transcribe.py data/audio/laref2026.webm \\
        --modele large-v3 --sortie data/laref2026.whisper.json

Produit le même format que `fetch_transcript.py` — `{source, blocs:[...]}` —
avec en plus le bloc `transcription` qui déclare **le modèle et sa famille**.

Pourquoi la famille est écrite dans le fichier : l'accord entre deux ASR de la
même famille ne prouve rien (METHODE.md §9). Un fine-tune partage les modes de
défaillance de son modèle d'origine ; deux transcriptions qui se trompent
ensemble se corroborent. La couche d'accord (`pythie/media/transcripts.py`)
refuse donc de compter deux sources d'une même famille comme deux voix, et ce
refus n'est possible que si la famille est déclarée à la production.

Les segments ne sont PAS fusionnés par défaut : l'accord entre transcriptions
s'aligne sur le temps, et fusionner à 30 s détruit la précision qui le rend
possible — l'erreur d'alignement mesurée le 01/09 venait exactement de là
(METHODE.md §11, deuxième occurrence).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

# Which family a model belongs to. Declared here rather than guessed from the
# name: a fine-tune usually renames itself, and that rename is precisely what
# would make it look independent.
FAMILIES = {
    "tiny": "whisper", "base": "whisper", "small": "whisper",
    "medium": "whisper", "large-v2": "whisper", "large-v3": "whisper",
    "distil-large-v3": "whisper",
    "bofenghuang/whisper-large-v3-french": "whisper",   # fine-tune de large-v3
    "nyralabs/CrisperWhisper2.0_large": "crisper",
}


def family_of(model: str) -> str:
    if model in FAMILIES:
        return FAMILIES[model]
    print(
        f"famille inconnue pour « {model} » — declaree « {model} », "
        "donc comptee comme independante de tout le reste. "
        "A corriger dans FAMILIES si ce modele derive d'un autre.",
        file=sys.stderr,
    )
    return model


def to_wav(source: Path, target: Path) -> Path:
    """16 kHz mono PCM. Le décodeur interne varie d'une pile à l'autre ;
    ffmpeg une fois pour toutes évite d'en dépendre."""
    if target.exists():
        print(f"audio deja extrait : {target}", file=sys.stderr)
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", str(source),
         "-ac", "1", "-ar", "16000", "-vn", str(target)],
        check=True,
    )
    return target


def transcribe(wav: Path, model_name: str, language: str) -> list[dict]:
    from faster_whisper import WhisperModel

    model = WhisperModel(model_name, device="cuda", compute_type="float16")
    segments, info = model.transcribe(
        str(wav),
        language=language,
        beam_size=5,
        vad_filter=True,
        # Le conditionnement sur le texte précédent est ce qui entretient les
        # boucles d'hallucination observees le 01/09 sur le fine-tune francais.
        condition_on_previous_text=False,
    )
    print(f"duree detectee : {info.duration / 60:.1f} min", file=sys.stderr)

    blocs: list[dict] = []
    started = time.time()
    for segment in segments:  # generateur : la transcription se fait ici
        text = segment.text.strip()
        if not text:
            continue
        blocs.append({
            "debut": round(segment.start, 2),
            "fin": round(segment.end, 2),
            "texte": text,
            "locuteur": "inconnu",
        })
        if len(blocs) % 100 == 0:
            done = segment.end
            speed = done / max(time.time() - started, 1e-6)
            print(f"  {done / 60:6.1f} min transcrites — {speed:.1f}x le direct",
                  file=sys.stderr)
    return blocs


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("audio")
    ap.add_argument("--modele", default="large-v3")
    ap.add_argument("--langue", default="fr")
    ap.add_argument("--sortie", default="data/transcription.json")
    ap.add_argument("--source", default="", help="URL d'origine, pour la traçabilité")
    args = ap.parse_args()

    audio = Path(args.audio)
    wav = audio if audio.suffix == ".wav" else to_wav(audio, audio.with_suffix(".wav"))

    started = time.time()
    blocs = transcribe(wav, args.modele, args.langue)
    elapsed = time.time() - started

    sortie = Path(args.sortie)
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_text(
        json.dumps(
            {
                "source": args.source or str(audio),
                "transcription": {
                    "modele": args.modele,
                    "famille": family_of(args.modele),
                    "langue": args.langue,
                    "produite_le": time.strftime("%Y-%m-%d"),
                    "secondes_de_calcul": round(elapsed, 1),
                },
                "blocs": blocs,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    duree = blocs[-1]["fin"] / 60 if blocs else 0
    mots = sum(len(b["texte"].split()) for b in blocs)
    print(
        f"{len(blocs)} segments · {duree:.0f} min · {mots} mots · "
        f"{duree * 60 / max(elapsed, 1e-6):.1f}x le direct → {sortie}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
