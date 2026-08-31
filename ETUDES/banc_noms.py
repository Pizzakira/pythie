#!/usr/bin/env python
"""ASR bench on PROPER NOUNS.

QUESTION, pre-registered before running anything
------------------------------------------------
Which transcription source recovers candidate surnames on real broadcast audio?

Not word error rate. Pythie needs two things from a transcript: the figures,
and who said them. Proper nouns carry the second, and the YouTube captions
destroy them -- observed on LaREF 2026: "Bruno Rota" for Retailleau, "Guxman"
for Glucksmann, "Talenaissance" for Attal, "Bronillot" for Retailleau again.

SUCCESS CRITERION, fixed in advance
-----------------------------------
Per source, the share of the 8 reference windows where the surname is written
in a form a reader would recognise. Scored on three levels, decided before
seeing any output:

  EXACT      the surname, correctly spelled
  RECOVERABLE a variant close enough that a fuzzy match to the roster would
              resolve it (edit ratio >= 0.72 against the true surname)
  LOST       neither

WHAT THIS BENCH DOES NOT MEASURE
--------------------------------
- Not overall WER. A source may be excellent on prose and poor on names.
- Not figures. That is a separate bench, on separate windows.
- Not real-time behaviour. These are offline passes on short excerpts.
- Not diarisation. Knowing a name was pronounced is not knowing who is speaking.

A source winning here does not become the transcription source; it becomes the
one whose introductions we trust to LABEL diarisation clusters.

DEGREES OF FREEDOM, declared
----------------------------
- window: 8 seconds centred on the mention (a name needs its introduction)
- fuzzy threshold for RECOVERABLE: 0.72
- no language detection: French forced, so we do not also compare detectors
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUDIO = ROOT / "data" / "audio"
OUT = ROOT / "data" / "banc_noms"

CONDA = Path.home() / ".conda" / "envs"
ENVS = {
    "faster-whisper-large-v3": CONDA / "karak" / "python.exe",
    "crisperwhisper": CONDA / "karak_crisper" / "python.exe",
}

WINDOW = 8.0
FUZZY = 0.72

# Reference windows: timestamp, who is actually named, and what the YouTube
# captions wrote there. Established by reading the caption file.
CASES = [
    (4,      ["Retailleau", "Glucksmann"], "Bruno Rota Raphaël Guxman"),
    (16,     ["Tondelier", "Attal"],       "Marine Tondelier et Gabriel Atal"),
    (376,    ["Retailleau"],               "Alors voilà Bronillot, vous avez la parole"),
    (857,    ["Attal"],                    "Talenaissance"),
    (1093,   ["Attal"],                    "Gabriel Atal"),
    (3525,   ["Retailleau"],               "Bruno Rota"),
    (9018,   ["Glucksmann"],               "Raphael Guxman"),
    (1164,   ["Mélenchon"],                "monsieur Mélenchon"),
]


def flat(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).lower()


def score(transcript: str, surname: str) -> str:
    """EXACT / RECOVERABLE / LOST for one surname in one transcript."""
    hay = flat(transcript)
    needle = flat(surname)
    if re.search(rf"\b{re.escape(needle)}\b", hay):
        return "EXACT"
    words = re.findall(r"[a-z][a-z'-]{2,}", hay)
    # Also try adjacent pairs: "Bruno Rota" may split a surname in two.
    grams = words + [f"{a}{b}" for a, b in zip(words, words[1:])]
    if difflib.get_close_matches(needle, grams, n=1, cutoff=FUZZY):
        return "RECOVERABLE"
    return "LOST"


def cut(source: Path, start: float, seconds: float, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-nostdin", "-y", "-ss", str(max(0.0, start - seconds / 2)),
         "-t", str(seconds), "-i", str(source),
         "-vn", "-ac", "1", "-ar", "16000", "-acodec", "pcm_s16le", str(dest)],
        check=True, capture_output=True,
    )
    return dest


RUNNER = r'''
import json, sys, warnings
warnings.filterwarnings("ignore")
kind, wav = sys.argv[1], sys.argv[2]
if kind == "faster-whisper-large-v3":
    from faster_whisper import WhisperModel
    m = WhisperModel("large-v3", device="cuda", compute_type="float16")
    segs, _ = m.transcribe(wav, language="fr", beam_size=5,
                           vad_filter=True, condition_on_previous_text=False)
    print(json.dumps({"text": " ".join(s.text for s in segs).strip()}))
else:
    import torch
    from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
    mid = "nyralabs/CrisperWhisper2.0_large"
    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        mid, torch_dtype=torch.float16, low_cpu_mem_usage=True).to("cuda")
    proc = AutoProcessor.from_pretrained(mid)
    pipe = pipeline("automatic-speech-recognition", model=model,
                    tokenizer=proc.tokenizer, feature_extractor=proc.feature_extractor,
                    torch_dtype=torch.float16, device="cuda")
    out = pipe(wav, generate_kwargs={"language": "fr"})
    print(json.dumps({"text": (out.get("text") or "").strip()}))
'''


def transcribe(kind: str, wav: Path) -> str:
    python = ENVS[kind]
    if not python.exists():
        return f"[env absent: {python}]"
    runner = OUT / "_runner.py"
    runner.parent.mkdir(parents=True, exist_ok=True)
    runner.write_text(RUNNER, encoding="utf-8")
    result = subprocess.run(
        [str(python), str(runner), kind, str(wav)],
        capture_output=True, text=True,
        env={**__import__("os").environ, "PYTHONNOUSERSITE": "1"},
    )
    for line in reversed(result.stdout.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line).get("text", "")
            except json.JSONDecodeError:
                continue
    return f"[echec] {result.stderr.strip()[-200:]}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio", default=None)
    parser.add_argument("--only", nargs="*", choices=list(ENVS), default=list(ENVS))
    args = parser.parse_args()

    source = Path(args.audio) if args.audio else next(iter(AUDIO.glob("laref2026.*")), None)
    if source is None or not source.exists():
        print("audio introuvable dans data/audio/", file=sys.stderr)
        sys.exit(1)

    OUT.mkdir(parents=True, exist_ok=True)
    rows = []

    for timestamp, surnames, caption in CASES:
        wav = cut(source, timestamp, WINDOW, OUT / f"w{timestamp}.wav")
        entry = {
            "t": timestamp, "surnames": surnames,
            "sources": {"sous-titres YouTube": caption},
        }
        for kind in args.only:
            entry["sources"][kind] = transcribe(kind, wav)
        rows.append(entry)
        print(f"[{timestamp//60}:{timestamp%60:02d}] {', '.join(surnames)}", file=sys.stderr)
        for name, text in entry["sources"].items():
            print(f"   {name:26} {text[:96]}", file=sys.stderr)

    tally: dict[str, dict[str, int]] = {}
    for entry in rows:
        for name, text in entry["sources"].items():
            bucket = tally.setdefault(name, {"EXACT": 0, "RECOVERABLE": 0, "LOST": 0})
            for surname in entry["surnames"]:
                bucket[score(text, surname)] += 1

    print("\n=== NOMS PROPRES — resultat ===")
    total = sum(len(e["surnames"]) for e in rows)
    print(f"{total} patronymes sur {len(rows)} fenetres de {WINDOW:.0f}s\n")
    print(f"{'source':28} {'EXACT':>6} {'RECUP':>6} {'PERDU':>6}   utilisable")
    print("-" * 62)
    for name, bucket in sorted(tally.items(), key=lambda kv: -kv[1]["EXACT"]):
        usable = 100 * (bucket["EXACT"] + bucket["RECOVERABLE"]) / total
        print(f"{name:28} {bucket['EXACT']:6} {bucket['RECOVERABLE']:6} "
              f"{bucket['LOST']:6}   {usable:5.0f}%")

    (OUT / "resultat.json").write_text(
        json.dumps({"window_s": WINDOW, "fuzzy": FUZZY, "cases": rows, "tally": tally},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\ndetail: {OUT / 'resultat.json'}")


if __name__ == "__main__":
    main()
