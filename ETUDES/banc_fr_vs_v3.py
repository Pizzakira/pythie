#!/usr/bin/env python
"""whisper-large-v3-french against faster-whisper-large-v3, head to head.

QUESTION, pre-registered
------------------------
Over twenty minutes of real debate, does the French fine-tune do anything the
base model does not?

The proper-noun bench already answered "not on names": both scored 8/11 exact
on the same windows. But that bench was 8-second excerpts of clear speech. The
fine-tune's documented claim is different -- 2,500 hours of problematic data
filtered out, which reduces hallucination *in long form*. Twenty continuous
minutes is where that would show, and short windows cannot see it.

WHAT IS COMPARED
----------------
1. FIGURES. The only thing Pythie ever judges. Count, and agreement between
   the two transcripts once aligned on the timeline.
2. HALLUCINATION MARKERS. Long-form Whisper fails by repeating itself: the
   same segment emitted over and over on silence or music. Measured as the
   share of segments that duplicate their predecessor, and the longest run.
3. SPEED. Wall clock, because a model that is twice as good and ten times
   slower is a different trade.

WHAT THIS DOES NOT MEASURE
--------------------------
- Not word error rate: no reference transcript exists for this material.
- Not which one is right when they differ. Agreement is not truth; both share
  an architecture and can be wrong together, as they already were on
  "debut du cafe" where CrisperWhisper had "quinquennat".
- Not names. That bench exists separately and found them equal.

DEGREES OF FREEDOM, declared
----------------------------
- window: 20 minutes from --depuis, default minute 20
- alignment tolerance for figures: 6 seconds
- French forced on both, so we do not also compare language detectors
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "banc_fr"
CONDA = Path.home() / ".conda" / "envs"

WINDOW = 6.0
NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
SCALE = re.compile(r"\b(milliards?|millions?|milliers?|%)\b", re.I)

MODELS = {
    "faster-whisper-large-v3": CONDA / "karak" / "python.exe",
    # karak_crisper, not karak: the latter's torchcodec DLLs fail at import.
    "whisper-large-v3-french": CONDA / "karak_crisper" / "python.exe",
}

RUNNER = r'''
import json, sys, time, warnings
warnings.filterwarnings("ignore")
kind, wav = sys.argv[1], sys.argv[2]
t0 = time.time()

if kind == "faster-whisper-large-v3":
    from faster_whisper import WhisperModel
    m = WhisperModel("large-v3", device="cuda", compute_type="float16")
    segs, _ = m.transcribe(wav, language="fr", beam_size=5, vad_filter=True,
                           condition_on_previous_text=False)
    out = [{"debut": s.start, "fin": s.end, "texte": s.text.strip()} for s in segs]
else:
    import torch, soundfile as sf
    from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
    mid = "bofenghuang/whisper-large-v3-french"
    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        mid, torch_dtype=torch.float16, low_cpu_mem_usage=True).to("cuda")
    proc = AutoProcessor.from_pretrained(mid)
    pipe = pipeline("automatic-speech-recognition", model=model,
                    tokenizer=proc.tokenizer, feature_extractor=proc.feature_extractor,
                    torch_dtype=torch.float16, device="cuda",
                    chunk_length_s=30, stride_length_s=5,
                    return_timestamps=True)
    audio, sr = sf.read(wav, dtype="float32")
    res = pipe({"raw": audio, "sampling_rate": sr},
               generate_kwargs={"language": "fr", "task": "transcribe"})
    out = []
    for ch in res.get("chunks") or []:
        ts = ch.get("timestamp") or (None, None)
        out.append({"debut": ts[0] or 0.0, "fin": ts[1] or 0.0,
                    "texte": (ch.get("text") or "").strip()})
    if not out:
        out = [{"debut": 0.0, "fin": 0.0, "texte": (res.get("text") or "").strip()}]

print(json.dumps({"segments": out, "seconds": round(time.time()-t0, 1)},
                 ensure_ascii=False))
'''


def figures(segments: list[dict]) -> list[tuple[float, str, str]]:
    found = []
    for seg in segments:
        text = re.sub(r"(?<=\d)[\s  ](?=\d)", "", seg["texte"])
        for m in NUMBER.finditer(text):
            tail = text[m.end():m.end() + 40]
            scale = SCALE.search(tail)
            found.append((seg["debut"], m.group(0).replace(",", "."),
                          scale.group(0).lower() if scale else ""))
    return found


def repetition(segments: list[dict]) -> dict:
    """Long-form Whisper fails by repeating itself. This counts that."""
    dupes, run, longest = 0, 0, 0
    previous = None
    for seg in segments:
        text = seg["texte"].strip().lower()
        if text and text == previous:
            dupes += 1
            run += 1
            longest = max(longest, run)
        else:
            run = 0
        previous = text
    return {"segments": len(segments), "repetes": dupes,
            "part": round(dupes / max(len(segments), 1), 3),
            "plus_longue_serie": longest}


def align(a: list, b: list, window: float = WINDOW) -> dict:
    used: set[int] = set()
    accord, desaccord, seul_a = [], [], []
    for t_a, fig_a, sc_a in a:
        best, best_dt = None, window + 1
        for j, (t_b, _, _) in enumerate(b):
            if j in used:
                continue
            dt = abs(t_b - t_a)
            if dt <= window and dt < best_dt:
                best, best_dt = j, dt
        if best is None:
            seul_a.append((t_a, fig_a, sc_a))
            continue
        used.add(best)
        _, fig_b, sc_b = b[best]
        same = fig_a == fig_b and (sc_a == sc_b or not sc_a or not sc_b)
        (accord if same else desaccord).append(
            (t_a, f"{fig_a} {sc_a}".strip(), f"{fig_b} {sc_b}".strip()))
    return {"accord": accord, "desaccord": desaccord, "seul_a": seul_a,
            "seul_b": [b[j] for j in range(len(b)) if j not in used]}


def run(kind: str, wav: Path) -> dict:
    runner = OUT / "_runner.py"
    runner.write_text(RUNNER, encoding="utf-8")
    r = subprocess.run([str(MODELS[kind]), str(runner), kind, str(wav)],
                       capture_output=True, text=True,
                       env={**os.environ, "PYTHONNOUSERSITE": "1"})
    line = next((l for l in reversed(r.stdout.splitlines())
                 if l.strip().startswith("{")), None)
    if line is None:
        print(f"  {kind} : ECHEC\n{r.stderr[-500:]}", file=sys.stderr)
        return {"segments": [], "seconds": 0}
    return json.loads(line)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--depuis", type=float, default=20.0, help="start minute")
    ap.add_argument("--minutes", type=float, default=20.0)
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    audio = next(iter((ROOT / "data" / "audio").glob("laref2026.*")), None)
    if audio is None:
        print("audio introuvable dans data/audio/", file=sys.stderr)
        sys.exit(1)

    wav = OUT / "extrait.wav"
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-ss", str(args.depuis * 60),
                    "-t", str(args.minutes * 60), "-i", str(audio),
                    "-vn", "-ac", "1", "-ar", "16000", "-acodec", "pcm_s16le",
                    str(wav)], check=True, capture_output=True)
    print(f"extrait : {args.depuis:.0f}:00 -> {args.depuis + args.minutes:.0f}:00 "
          f"({args.minutes:.0f} min)\n", file=sys.stderr)

    results = {}
    for kind in MODELS:
        print(f"  {kind} ...", file=sys.stderr, flush=True)
        results[kind] = run(kind, wav)
        n = len(results[kind]["segments"])
        print(f"    {n} segments en {results[kind]['seconds']}s", file=sys.stderr)

    v3 = results["faster-whisper-large-v3"]
    fr = results["whisper-large-v3-french"]
    audio_s = args.minutes * 60

    print("\n=== FRANCAIS vs LARGE-V3 ===\n")
    print(f"{'':30}{'large-v3':>14}{'francais':>14}")
    print("-" * 58)
    print(f"{'segments':30}{len(v3['segments']):>14}{len(fr['segments']):>14}")
    print(f"{'duree (s)':30}{v3['seconds']:>14}{fr['seconds']:>14}")
    print(f"{'x temps reel':30}"
          f"{audio_s / max(v3['seconds'], .1):>13.1f}x"
          f"{audio_s / max(fr['seconds'], .1):>13.1f}x")

    rep_v3, rep_fr = repetition(v3["segments"]), repetition(fr["segments"])
    print(f"\n{'segments repetes':30}{rep_v3['repetes']:>14}{rep_fr['repetes']:>14}")
    print(f"{'  part':30}{rep_v3['part']:>14.1%}{rep_fr['part']:>14.1%}")
    print(f"{'  plus longue serie':30}"
          f"{rep_v3['plus_longue_serie']:>14}{rep_fr['plus_longue_serie']:>14}")

    fig_v3, fig_fr = figures(v3["segments"]), figures(fr["segments"])
    print(f"\n{'chiffres reperes':30}{len(fig_v3):>14}{len(fig_fr):>14}")

    al = align(fig_v3, fig_fr)
    apparies = len(al["accord"]) + len(al["desaccord"])
    print(f"\nappariement des chiffres (+/-{WINDOW:.0f}s) : {apparies}")
    print(f"  accord     {len(al['accord']):4}")
    print(f"  desaccord  {len(al['desaccord']):4}   <- ne doit pas etre juge")
    print(f"  seul v3    {len(al['seul_a']):4}")
    print(f"  seul fr    {len(al['seul_b']):4}")
    if apparies:
        print(f"  taux d'accord : {100*len(al['accord'])/apparies:.0f} %")

    if al["desaccord"]:
        print("\n--- desaccords sur un chiffre ---")
        for t, a, b in sorted(al["desaccord"])[:15]:
            print(f"  [{int(t)//60:3}:{int(t)%60:02d}]  v3 « {a:14} »   fr « {b} »")

    # Sauvegarder les DEUX textes : la comparaison des chiffres ne dit rien de
    # la qualite du texte, et c'est le texte qu'on lit.
    for nom, res in (("large-v3", v3), ("francais", fr)):
        lignes = [f"[{int(g['debut'])//60:>3}:{int(g['debut'])%60:02d}] {g['texte']}"
                  for g in res["segments"]]
        (OUT / f"texte_{nom}.txt").write_text("\n".join(lignes), encoding="utf-8")

    (OUT / "resultat.json").write_text(json.dumps({
        "extrait": {"depuis_min": args.depuis, "minutes": args.minutes},
        "large_v3": {"segments": len(v3["segments"]), "seconds": v3["seconds"],
                     "repetition": rep_v3, "chiffres": len(fig_v3)},
        "francais": {"segments": len(fr["segments"]), "seconds": fr["seconds"],
                     "repetition": rep_fr, "chiffres": len(fig_fr)},
        "accord": {k: len(v) for k, v in al.items()},
        "desaccords": [{"t": t, "v3": a, "fr": b} for t, a, b in al["desaccord"]],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\ndetail: {OUT / 'resultat.json'}")


if __name__ == "__main__":
    main()
