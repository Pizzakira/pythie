#!/usr/bin/env python
"""Transcription agreement on FIGURES, over a whole debate.

QUESTION, pre-registered
------------------------
Over three hours of real broadcast, on how many figures do two independent
transcriptions agree -- and what does the disagreement cost us?

This is not a word error rate. Pythie only ever judges values, so the only
agreement that matters is on the figure and its unit. "Il y a" versus "on
compte" is irrelevant; "2,7" versus "27" decides whether a verdict is a fact
check or a fabricated quote.

WHY IT MATTERS HERE
-------------------
The first red this system ever produced was on "Je vous cite de au feu 600
millions de dettes françaises" -- ASR debris. The speaker said something else.
A second transcription would have disagreed on that figure, and the passage
would never have reached the verdict stage.

So the number this bench returns is the size of the guard we are missing.

SUCCESS CRITERION, fixed in advance
-----------------------------------
For each figure found in either transcription, aligned by timestamp:

  ACCORD      both sources carry the same figure -> judgeable
  DESACCORD   both carry a figure, and they differ -> MUST NOT be judged
  SEUL        only one source carries it -> not judgeable either

The rate that matters is DESACCORD + SEUL: it is the share of figures Pythie
would have to stay silent about, and therefore the honest cost of the guard.

WHAT THIS DOES NOT MEASURE
--------------------------
- Which source is right. Agreement is not truth: both can be wrong together.
- Prose quality, speakers, or timing precision beyond the alignment window.
- Anything about the verdict stage; this is upstream of it.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "banc_chiffres"
CONDA = Path.home() / ".conda" / "envs"

# Alignment tolerance. Captions lag speech, and the two sources segment
# differently; a figure spoken once can land a few seconds apart.
WINDOW = 6.0

NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
SCALE = re.compile(r"\b(milliards?|millions?|milliers?|%)\b", re.I)

TRANSCRIBE = r'''
import json, sys, warnings
warnings.filterwarnings("ignore")
from faster_whisper import WhisperModel
m = WhisperModel("large-v3", device="cuda", compute_type="float16")
segs, info = m.transcribe(sys.argv[1], language="fr", beam_size=5,
                          vad_filter=True, condition_on_previous_text=False,
                          word_timestamps=False)
out = [{"debut": s.start, "fin": s.end, "texte": s.text.strip()} for s in segs]
print(json.dumps({"segments": out}, ensure_ascii=False))
'''


def normalise_figure(text: str, position: int) -> str:
    """A figure plus the scale word that follows it.

    '3 000 milliards' and '3000 milliards' are the same claim; '600 millions'
    and '600 milliards' are not. Digit grouping is collapsed, the scale is kept.
    """
    cleaned = re.sub(r"(?<=\d)[\s  ](?=\d)", "", text)
    tail = cleaned[position:position + 40]
    scale = SCALE.search(tail)
    return (scale.group(0).lower() if scale else "")


def figures(segments: list[dict]) -> list[tuple[float, str, str]]:
    """(timestamp, figure, scale) for every number in a transcript."""
    found = []
    for seg in segments:
        text = re.sub(r"(?<=\d)[\s  ](?=\d)", "", seg["texte"])
        for m in NUMBER.finditer(text):
            tail = text[m.end():m.end() + 40]
            scale = SCALE.search(tail)
            found.append((seg["debut"], m.group(0).replace(",", "."),
                          scale.group(0).lower() if scale else ""))
    return found


def compare(a: list, b: list, window: float = WINDOW) -> dict:
    """Align two figure lists on the timeline and classify each."""
    used_b: set[int] = set()
    accord, desaccord, seul_a = [], [], []

    for t_a, fig_a, sc_a in a:
        best, best_dt = None, window + 1
        for j, (t_b, fig_b, sc_b) in enumerate(b):
            if j in used_b:
                continue
            dt = abs(t_b - t_a)
            if dt <= window and dt < best_dt:
                best, best_dt = j, dt
        if best is None:
            seul_a.append((t_a, fig_a, sc_a))
            continue
        used_b.add(best)
        t_b, fig_b, sc_b = b[best]
        same = fig_a == fig_b and (sc_a == sc_b or not sc_a or not sc_b)
        (accord if same else desaccord).append(
            (t_a, f"{fig_a} {sc_a}".strip(), f"{fig_b} {sc_b}".strip()))

    seul_b = [b[j] for j in range(len(b)) if j not in used_b]
    return {"accord": accord, "desaccord": desaccord,
            "seul_a": seul_a, "seul_b": seul_b}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--audio", default=None)
    ap.add_argument("--subs", default="data/laref2026.json")
    ap.add_argument("--reuse", action="store_true",
                    help="reuse a previous whisper pass if present")
    ap.add_argument("--depuis", type=float, default=0.0, help="start minute")
    ap.add_argument("--minutes", type=float, default=0.0,
                    help="slice length; 0 means the whole file")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    cache = OUT / "whisper_full.json"

    if args.reuse and cache.exists():
        whisper = json.loads(cache.read_text(encoding="utf-8"))["segments"]
        print(f"whisper : {len(whisper)} segments (cache)", file=sys.stderr)
    else:
        audio = Path(args.audio) if args.audio else next(
            iter((ROOT / "data" / "audio").glob("laref2026.*")), None)
        if audio is None:
            print("audio introuvable", file=sys.stderr)
            sys.exit(1)
        if args.minutes:
            # A slice, not three hours: the measurement is the same and the
            # wait is ninety seconds instead of twenty minutes.
            slice_wav = OUT / "slice.wav"
            subprocess.run(
                ["ffmpeg", "-nostdin", "-y", "-ss", str(args.depuis * 60),
                 "-t", str(args.minutes * 60), "-i", str(audio),
                 "-vn", "-ac", "1", "-ar", "16000", "-acodec", "pcm_s16le",
                 str(slice_wav)], check=True, capture_output=True)
            audio = slice_wav
        runner = OUT / "_transcribe.py"
        runner.write_text(TRANSCRIBE, encoding="utf-8")
        print(f"whisper : transcription de {audio.name} (comptez ~20 min)...",
              file=sys.stderr)
        r = subprocess.run(
            [str(CONDA / "karak" / "python.exe"), str(runner), str(audio)],
            capture_output=True, text=True,
            env={**os.environ, "PYTHONNOUSERSITE": "1"})
        line = next((l for l in reversed(r.stdout.splitlines())
                     if l.strip().startswith("{")), None)
        if line is None:
            print(f"echec:\n{r.stderr[-800:]}", file=sys.stderr)
            sys.exit(1)
        cache.write_text(line, encoding="utf-8")
        whisper = json.loads(line)["segments"]
        print(f"whisper : {len(whisper)} segments", file=sys.stderr)

    # Whisper timestamps restart at zero on a slice: shift them back onto the
    # debate timeline so both sources share one clock.
    if args.minutes:
        offset = args.depuis * 60
        for seg in whisper:
            seg["debut"] += offset
            seg["fin"] += offset

    subs = json.loads(Path(args.subs).read_text(encoding="utf-8"))["blocs"]
    if args.minutes:
        lo, hi = args.depuis * 60, (args.depuis + args.minutes) * 60
        subs = [b for b in subs if b["fin"] > lo and b["debut"] < hi]

    fig_w = figures(whisper)
    fig_s = figures(subs)
    res = compare(fig_w, fig_s)

    total = len(res["accord"]) + len(res["desaccord"]) + len(res["seul_a"]) + len(res["seul_b"])
    jugeable = len(res["accord"])

    print("\n=== ACCORD SUR LES CHIFFRES — debat entier ===\n")
    print(f"chiffres reperes   whisper {len(fig_w)}   sous-titres {len(fig_s)}")
    print(f"apparies (+/-{WINDOW:.0f}s)  {len(res['accord']) + len(res['desaccord'])}\n")
    print(f"  ACCORD      {len(res['accord']):5}   jugeable")
    print(f"  DESACCORD   {len(res['desaccord']):5}   ne doit PAS etre juge")
    print(f"  SEUL whisper{len(res['seul_a']):5}   non jugeable")
    print(f"  SEUL sous-t.{len(res['seul_b']):5}   non jugeable")
    print(f"\n  part jugeable : {100*jugeable/max(total,1):.0f} % des {total} chiffres")

    print("\n--- desaccords (ce que le garde-fou bloquerait) ---")
    for t, a, b in sorted(res["desaccord"])[:20]:
        print(f"  [{int(t)//60:3}:{int(t)%60:02d}]  whisper « {a:16} »   sous-titres « {b} »")

    (OUT / "resultat.json").write_text(json.dumps({
        "window_s": WINDOW,
        "counts": {k: len(v) for k, v in res.items()},
        "desaccords": [{"t": t, "whisper": a, "sous_titres": b}
                       for t, a, b in res["desaccord"]],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\ndetail: {OUT / 'resultat.json'}")


if __name__ == "__main__":
    main()
