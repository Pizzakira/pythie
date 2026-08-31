
import json, sys, warnings
warnings.filterwarnings("ignore")
from faster_whisper import WhisperModel
m = WhisperModel("large-v3", device="cuda", compute_type="float16")
segs, info = m.transcribe(sys.argv[1], language="fr", beam_size=5,
                          vad_filter=True, condition_on_previous_text=False,
                          word_timestamps=False)
out = [{"debut": s.start, "fin": s.end, "texte": s.text.strip()} for s in segs]
print(json.dumps({"segments": out}, ensure_ascii=False))
