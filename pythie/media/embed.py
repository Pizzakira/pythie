"""Turning a stretch of audio into a vector that stands for a voice.

The registry in `voiceprint.py` compares vectors and knows nothing about audio;
this module is the only place where sound becomes a number, and it is kept
separate for that reason -- the identification rules must stay testable without
a GPU, a model download, or a three-hour wav.

ECAPA-TDNN (`speechbrain/spkrec-ecapa-voxceleb`), 192 dimensions, trained on
VoxCeleb. Chosen because it is ungated and runs locally: a speaker embedding
sent to a remote service would put a political debate's audio on someone else's
machine, which this project will not do.

TWO THINGS IT CANNOT DO, both declared rather than discovered later:

  - it does not detect overlapped speech. An embedding computed over two mixed
    voices resembles neither, so it lands somewhere between them and can score
    high against a third person entirely. Without an overlap detector, the rule
    stated in `consensus.py` -- overlap abstains outright -- cannot be applied,
    and everything built on top must say so.
  - it carries the channel with the voice. A print built from one recording
    matches that microphone as much as that person, which is why `Registry.enrol`
    refuses fewer than three samples.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import numpy as np

MODEL_ID = "speechbrain/spkrec-ecapa-voxceleb"
SAMPLE_RATE = 16_000

# Below this, an embedding is dominated by whatever phoneme happens to be in
# the window. Not swept -- declared, like every other value in this project
# that was posed rather than measured (METHODE.md §2).
MIN_SECONDS = 2.0


@dataclass
class Window:
    """A stretch of the audio, in seconds."""

    start: float
    end: float

    @property
    def duration(self) -> float:
        return self.end - self.start


class Embedder:
    """Loads the model once, embeds many windows.

    The model is loaded lazily so that importing this module -- which the
    pipeline does -- costs nothing when no audio is involved.
    """

    def __init__(self, device: str = "cuda", savedir: str = "data/modeles/ecapa"):
        self.device = device
        self.savedir = savedir
        self._model = None
        self._audio: Optional[Tuple[Path, np.ndarray]] = None

    # -- model ------------------------------------------------------------

    @property
    def model(self):
        if self._model is None:
            import warnings

            warnings.filterwarnings("ignore")
            from speechbrain.inference.speaker import EncoderClassifier
            from speechbrain.utils.fetching import LocalStrategy

            self._model = EncoderClassifier.from_hparams(
                source=MODEL_ID,
                savedir=self.savedir,
                # Copy rather than symlink: creating a symlink on Windows needs
                # a privilege a normal session does not have, and the failure
                # arrives as an opaque WinError 1314 halfway through a download.
                local_strategy=LocalStrategy.COPY,
                run_opts={"device": self.device},
            )
        return self._model

    # -- audio ------------------------------------------------------------

    def _samples(self, wav: Path) -> np.ndarray:
        """The whole file, in memory, once.

        Three hours of 16 kHz mono is about 350 MB as float32 -- large, but
        read once instead of seeking thousands of times, and it makes the
        window slicing exact rather than approximate.
        """
        wav = Path(wav)
        if self._audio and self._audio[0] == wav:
            return self._audio[1]

        import soundfile as sf

        data, rate = sf.read(str(wav), dtype="float32")
        if rate != SAMPLE_RATE:
            raise ValueError(
                f"{wav.name} echantillonne a {rate} Hz, {SAMPLE_RATE} attendu. "
                "Passer par scripts/transcribe.py, qui normalise via ffmpeg."
            )
        if data.ndim > 1:
            data = data.mean(axis=1)
        self._audio = (wav, data)
        return data

    # -- embedding --------------------------------------------------------

    def embed(
        self, wav: Path | str, windows: Sequence[Window], batch: int = 16
    ) -> Tuple[np.ndarray, List[int]]:
        """Embed each window. Returns the vectors and the indices kept.

        Windows shorter than `MIN_SECONDS` are dropped rather than padded:
        padding a short window with silence produces a vector that describes
        the silence as much as the voice, and it would enter a centroid as if
        it were evidence.
        """
        import torch

        samples = self._samples(Path(wav))
        kept: List[int] = []
        clips: List[np.ndarray] = []

        for index, window in enumerate(windows):
            if window.duration < MIN_SECONDS:
                continue
            start = int(window.start * SAMPLE_RATE)
            end = min(int(window.end * SAMPLE_RATE), len(samples))
            if end - start < MIN_SECONDS * SAMPLE_RATE:
                continue
            clips.append(samples[start:end])
            kept.append(index)

        if not clips:
            return np.zeros((0, 192), dtype=np.float32), []

        vectors: List[np.ndarray] = []
        for offset in range(0, len(clips), batch):
            group = clips[offset:offset + batch]
            longest = max(len(c) for c in group)
            # Padding inside a batch is unavoidable; `wav_lens` tells the model
            # what fraction of each row is real signal, so the padding is not
            # pooled into the embedding.
            padded = np.zeros((len(group), longest), dtype=np.float32)
            lengths = np.zeros(len(group), dtype=np.float32)
            for row, clip in enumerate(group):
                padded[row, :len(clip)] = clip
                lengths[row] = len(clip) / longest

            tensor = torch.from_numpy(padded).to(self.device)
            wav_lens = torch.from_numpy(lengths).to(self.device)
            with torch.no_grad():
                out = self.model.encode_batch(tensor, wav_lens=wav_lens)
            vectors.append(out.squeeze(1).cpu().numpy())

        return np.vstack(vectors).astype(np.float32), kept


def cosine(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Cosine similarity between two sets of vectors, rows against rows."""
    a = a / (np.linalg.norm(a, axis=-1, keepdims=True) + 1e-9)
    b = b / (np.linalg.norm(b, axis=-1, keepdims=True) + 1e-9)
    return a @ b.T
