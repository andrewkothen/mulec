"""Decode bounded local files; no URL fetching or external services."""
from dataclasses import dataclass
from pathlib import Path
import subprocess
import tempfile

import imageio_ffmpeg
import librosa
import numpy as np
import soundfile as sf

RATE = 22050
MAX_SECONDS = 15 * 60


@dataclass
class AudioData:
    samples: np.ndarray
    rate: int
    duration: float
    waveform: list[float]


def decode(path: Path, playback_path: Path) -> AudioData:
    # FFmpeg handles compressed formats; a time cap bounds decoded PCM memory.
    with tempfile.TemporaryDirectory() as temp:
        decoded = Path(temp) / "decoded.wav"
        try:
            process = subprocess.run(
                [imageio_ffmpeg.get_ffmpeg_exe(), "-nostdin", "-v", "error", "-y",
                 "-protocol_whitelist", "file,pipe", "-i", str(path), "-t", str(MAX_SECONDS + 1),
                 "-vn", "-ac", "1", "-ar", str(RATE), str(decoded)],
                capture_output=True, timeout=120, check=False,
            )
            if process.returncode:
                raise ValueError("This file could not be decoded. Try a WAV, FLAC, MP3 or M4A audio file.")
            y, sr = sf.read(decoded, dtype="float32")
        except subprocess.TimeoutExpired as exc:
            raise ValueError("Audio decoding exceeded two minutes. Try a shorter recording.") from exc
    duration = len(y) / sr
    if duration > MAX_SECONDS:
        raise ValueError("Recordings are limited to 15 minutes. Import a shorter excerpt.")
    if duration < 2:
        raise ValueError("Please import at least two seconds of audio.")
    if not np.isfinite(y).all():
        raise ValueError("Audio contains invalid sample values")
    peak = float(np.max(np.abs(y)))
    if peak < 1e-5:
        raise ValueError("This recording is silent; no musical content was found.")
    y = librosa.util.normalize(y)
    sf.write(playback_path, y, sr, subtype="PCM_16")
    waveform = [round(float(np.max(np.abs(c))), 4) for c in np.array_split(y, min(1000, len(y)))]
    return AudioData(y, sr, duration, waveform)
