"""Run one pinned model in its own Python environment on a local WAV file."""

from contextlib import redirect_stdout
import json
from pathlib import Path
import sys


def predict_keys(path):
    import numpy as np
    import soundfile as sf
    import torch
    from skey.key_detection import DEFAULT_CHECKPOINT_PATH, key_map, load_model_components
    from torchaudio.functional import resample

    torch.set_num_threads(2)
    # The official checkpoint stores NumPy scalar settings alongside the tensors.
    with torch.serialization.safe_globals(
        [
            (np._core.multiarray.scalar, "numpy.core.multiarray.scalar"),
            np.dtype,
            np.dtypes.Float64DType,
            np.dtypes.Float32DType,
            np.dtypes.Int64DType,
        ]
    ):
        checkpoint = torch.load(DEFAULT_CHECKPOINT_PATH, weights_only=True, map_location="cpu")
    device = torch.device("cpu")
    vqt, network, crop = load_model_components(checkpoint, device)
    samples, rate = sf.read(path, dtype="float32")
    waveform = torch.from_numpy(samples[None, :])
    target_rate = checkpoint["audio"]["sr"]
    if rate != target_rate:
        waveform = resample(waveform, rate, target_rate)
    total = torch.zeros(len(key_map))
    weight = 0
    # Bounded windows keep the model's memory use independent of track length.
    with torch.inference_mode():
        for window in waveform.split(target_rate * 30, dim=-1):
            length = window.shape[-1]
            if length < target_rate * 2 or window.square().mean() < 1e-6:
                continue
            features = crop(vqt(window.unsqueeze(0)), torch.zeros(1))
            total += network(features).mean(dim=0) * length
            weight += length
    if not weight:
        return []
    result = []
    for index in total.argsort(descending=True).tolist():
        key, mode = key_map[index].split()
        result.append({"key": key, "mode": mode.lower(), "score": float(total[index] / weight)})
    return result


def predict_chords(path):
    import torch
    from lv_chordia.chord_recognition import chord_recognition

    torch.set_num_threads(2)
    return chord_recognition(str(path), device="cpu")


if __name__ == "__main__":
    model, filename = sys.argv[1:]
    path = Path(filename).resolve(strict=True)
    with redirect_stdout(sys.stderr):
        result = {"key": predict_keys, "chords": predict_chords}[model](path)
    print(json.dumps(result, allow_nan=False))
