
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
