"""Audio acquisition and normalisation.

Everything downstream -- VAD, speaker embeddings, ASR -- expects 16 kHz mono
PCM. Normalising once here means no other module has to care about the source
format, and it makes the pipeline reproducible: the same input always yields
the same samples.

We never download the video, only its audio, and we never republish a full
transcript. Reproducing a broadcast debate in extenso would be a reproduction
of a protected work; quoting the passages we analyse is not.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

SAMPLE_RATE = 16000


class MediaError(RuntimeError):
    pass


def _require(tool: str) -> str:
    path = shutil.which(tool)
    if not path:
        raise MediaError(f"{tool} not found on PATH")
    return path


@dataclass
class AudioTrack:
    samples: np.ndarray          # float32, mono, [-1, 1]
    sample_rate: int = SAMPLE_RATE
    source: str = ""
    title: str = ""

    @property
    def duration(self) -> float:
        return len(self.samples) / self.sample_rate

    def slice(self, start: float, end: float) -> np.ndarray:
        """Samples between two timestamps, in seconds."""
        a = max(0, int(start * self.sample_rate))
        b = min(len(self.samples), int(end * self.sample_rate))
        return self.samples[a:b] if b > a else np.zeros(0, dtype=np.float32)


def to_wav(source: Path | str, destination: Optional[Path] = None) -> Path:
    """Convert any local media file to 16 kHz mono WAV."""
    source = Path(source)
    destination = destination or source.with_suffix(".16k.wav")
    subprocess.run(
        [
            _require("ffmpeg"), "-nostdin", "-y", "-i", str(source),
            "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE),
            "-acodec", "pcm_s16le", str(destination),
        ],
        check=True, capture_output=True,
    )
    return destination


def read_wav(path: Path | str) -> AudioTrack:
    """Read a 16 kHz mono WAV into float32 samples."""
    import wave

    with wave.open(str(path), "rb") as handle:
        if handle.getframerate() != SAMPLE_RATE or handle.getnchannels() != 1:
            raise MediaError(
                f"{path}: expected {SAMPLE_RATE} Hz mono, got "
                f"{handle.getframerate()} Hz / {handle.getnchannels()} ch. "
                "Run to_wav() first."
            )
        raw = handle.readframes(handle.getnframes())

    pcm = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    return AudioTrack(samples=pcm, source=str(path))


def fetch_audio(url: str, out_dir: Path | str = "data") -> Tuple[Path, dict]:
    """Download the audio track only, plus its metadata.

    Returns (wav_path, metadata). Subtitles, when the platform has them, are
    fetched separately by scripts/fetch_transcript.py -- they give text and
    timing but no speaker, which is exactly what diarisation supplies.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    yt_dlp = _require("yt-dlp")

    with tempfile.TemporaryDirectory() as tmp:
        template = str(Path(tmp) / "audio.%(ext)s")
        subprocess.run(
            [yt_dlp, "-x", "--audio-format", "wav", "--audio-quality", "0",
             "--no-playlist", "-o", template, url],
            check=True, capture_output=True,
        )
        probe = subprocess.run(
            [yt_dlp, "--no-playlist", "--dump-json", "--skip-download", url],
            check=True, capture_output=True, text=True,
        )
        metadata = json.loads(probe.stdout.splitlines()[0])

        downloaded = next(Path(tmp).glob("audio.*"), None)
        if downloaded is None:
            raise MediaError(f"no audio track retrieved for {url}")

        target = out_dir / "audio.16k.wav"
        subprocess.run(
            [_require("ffmpeg"), "-nostdin", "-y", "-i", str(downloaded),
             "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE),
             "-acodec", "pcm_s16le", str(target)],
            check=True, capture_output=True,
        )

    return target, {
        "title": metadata.get("title", ""),
        "uploader": metadata.get("uploader", ""),
        "upload_date": metadata.get("upload_date", ""),
        "duration": metadata.get("duration", 0),
        "url": url,
    }


@dataclass
class Turn:
    """A stretch of speech attributed to one speaker."""

    start: float
    end: float
    speaker_id: str
    display_name: str
    role: str = ""
    similarity: float = 0.0
    accepted: bool = False
    reason: str = ""

    @property
    def duration(self) -> float:
        return self.end - self.start


def merge_adjacent(turns: List[Turn], max_gap: float = 0.6) -> List[Turn]:
    """Join consecutive turns from the same speaker.

    VAD cuts on silence, so one sentence often arrives as several fragments.
    Merging them before alignment keeps blocks readable rather than shredded.
    Unidentified stretches are merged too: several consecutive "unknown" spans
    are one unattributed passage, not several.
    """
    if not turns:
        return []

    merged = [turns[0]]
    for turn in turns[1:]:
        last = merged[-1]
        if turn.speaker_id == last.speaker_id and turn.start - last.end <= max_gap:
            last.end = turn.end
            last.similarity = max(last.similarity, turn.similarity)
        else:
            merged.append(turn)
    return merged
