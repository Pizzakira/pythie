#!/usr/bin/env python
"""Le fine-tune français, converti en CTranslate2 : la boucle vient-elle des
poids ou de la pile ?

    python ETUDES/banc_francais_ct2.py data/banc_fr/extrait.wav

Protocole figé avant exécution : `ETUDES/preinscription-francais.md`.

Le 01/09, le modèle exécuté via `transformers` a produit une trentaine de
« c'est le 2ème » consécutifs sur 5 minutes. `transformers` découpe en blocs de
30 s et conditionne sur le texte précédent ; `faster-whisper` applique un VAD et
peut s'en passer. Si la boucle disparaît après conversion, elle venait de la
pile d'exécution et non du modèle.

À exécuter dans l'environnement qui porte le GPU :
    /c/ProgramData/anaconda3/envs/whisperx/python.exe
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

MODEL_ID = "bofenghuang/whisper-large-v3-french"

# Pré-inscrits. Ne pas modifier après avoir vu un résultat.
MAX_LOOP = 2            # répétitions consécutives tolérées
MIN_SPEED = 5.0         # multiples du direct
WITNESS_MIN_LOOP = 5    # ce que la métrique DOIT trouver dans le texte témoin

BIG_INTEGER = re.compile(r"\d{7,}")


def longest_repeat(text: str) -> tuple[int, str]:
    """La plus longue répétition consécutive d'un même groupe de mots.

    Sans découpage en segments, volontairement : la métrique du 01/09 comptait
    les segments consécutifs identiques et a rendu 0 sur une boucle manifeste,
    parce que la boucle vivait à l'intérieur d'un seul bloc de 30 s
    (METHODE.md §11). Une métrique doit chercher le phénomène là où il vit.
    """
    words = text.lower().split()
    best, phrase = 0, ""

    for size in range(1, 9):
        index = 0
        while index + size <= len(words):
            pattern = words[index:index + size]
            repeats = 1
            cursor = index + size
            while (cursor + size <= len(words)
                   and words[cursor:cursor + size] == pattern):
                repeats += 1
                cursor += size
            if repeats > best:
                best, phrase = repeats, " ".join(pattern)
            index = cursor if repeats > 1 else index + 1
    return best, phrase


def convert(destination: Path) -> Path:
    """Conversion CTranslate2, une fois. Le modèle est déjà dans le cache HF."""
    if (destination / "model.bin").exists():
        print(f"deja converti : {destination}", file=sys.stderr)
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    print(f"conversion CTranslate2 de {MODEL_ID} ...", file=sys.stderr)
    subprocess.run(
        [sys.executable, "-m", "ctranslate2.converters.transformers",
         "--model", MODEL_ID, "--output_dir", str(destination),
         "--copy_files", "tokenizer.json", "preprocessor_config.json",
         "--quantization", "float16"],
        check=True,
    )
    return destination


def transcribe(model_path: str, wav: Path) -> tuple[str, float, int]:
    from faster_whisper import WhisperModel

    model = WhisperModel(model_path, device="cuda", compute_type="float16")
    started = time.time()
    segments, info = model.transcribe(
        str(wav), language="fr", beam_size=5, vad_filter=True,
        condition_on_previous_text=False,
    )
    pieces = [s.text.strip() for s in segments]
    elapsed = time.time() - started
    return " ".join(pieces), info.duration / max(elapsed, 1e-6), len(pieces)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("wav", nargs="?", default="data/banc_fr/extrait.wav")
    ap.add_argument("--ancien", default="data/banc_fr/texte_francais.txt",
                    help="sortie transformers du 01/09 — le témoin de la métrique")
    ap.add_argument("--large-v3", default="data/banc_fr/texte_large-v3.txt")
    ap.add_argument("--modele-ct2", default="data/modeles/whisper-large-v3-french-ct2")
    ap.add_argument("--sortie", default="data/banc_fr/resultat_ct2.json")
    args = ap.parse_args()

    # --- 1. la métrique est validée sur un cas où elle DOIT se déclencher ---
    witness = Path(args.ancien).read_text(encoding="utf-8", errors="replace")
    witness_loop, witness_phrase = longest_repeat(witness)
    print(f"temoin de la metrique — plus longue repetition dans la sortie "
          f"transformers du 01/09 : {witness_loop}x « {witness_phrase} »",
          file=sys.stderr)
    if witness_loop < WITNESS_MIN_LOOP:
        sys.exit(f"La metrique ne retrouve pas la boucle connue "
                 f"({witness_loop} < {WITNESS_MIN_LOOP}). Banc interrompu : "
                 "sans temoin, un zero ne se lit pas.")

    reference = Path(args.large_v3).read_text(encoding="utf-8", errors="replace")
    reference_loop, reference_phrase = longest_repeat(reference)
    print(f"large-v3 sur le meme extrait : {reference_loop}x "
          f"« {reference_phrase} »", file=sys.stderr)

    # --- 2. conversion, puis mesure ---------------------------------------
    model_path = convert(Path(args.modele_ct2))
    text, speed, segments = transcribe(str(model_path), Path(args.wav))

    loop, phrase = longest_repeat(text)
    big = BIG_INTEGER.findall(text)

    passed = {
        "boucle": loop <= max(MAX_LOOP, reference_loop),
        "chiffres": not big,
        "vitesse": speed >= MIN_SPEED,
    }

    print(f"\n--- fine-tune francais, converti CTranslate2 ---", file=sys.stderr)
    print(f"  segments              {segments}", file=sys.stderr)
    print(f"  vitesse               {speed:.1f}x le direct  "
          f"[{'ok' if passed['vitesse'] else 'ECHEC'}]", file=sys.stderr)
    print(f"  plus longue boucle    {loop}x « {phrase} »  "
          f"[{'ok' if passed['boucle'] else 'ECHEC'}]", file=sys.stderr)
    print(f"  entiers aberrants     {big or 'aucun'}  "
          f"[{'ok' if passed['chiffres'] else 'ECHEC'}]", file=sys.stderr)

    verdict = (
        "utilisable — mais candidat seulement : sans verite de terrain, le "
        "titulaire reste titulaire a egalite (regle pre-inscrite)"
        if all(passed.values()) else
        "non retenu — D-046 confirme, et sa cause est desormais connue"
    )
    print(f"\n{verdict}", file=sys.stderr)

    out = Path(args.sortie)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "modele": MODEL_ID,
        "pile": "faster-whisper / CTranslate2 float16, VAD, sans conditionnement",
        "extrait": str(args.wav),
        "temoin_de_la_metrique": {"repetitions": witness_loop,
                                  "phrase": witness_phrase},
        "large_v3": {"repetitions": reference_loop, "phrase": reference_phrase},
        "mesure": {"segments": segments, "vitesse_directe": round(speed, 1),
                   "boucle": loop, "phrase_bouclee": phrase,
                   "entiers_aberrants": big},
        "criteres": passed,
        "verdict": verdict,
        "texte": text,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"→ {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
