#!/usr/bin/env python3
"""Install the optional CPU harmony models once for offline use."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / ".tools"
PYTHON = Path("Scripts/python.exe" if os.name == "nt" else "bin/python")
MODELS = {
    "key": (
        "skey @ git+https://github.com/deezer/skey.git@80d9590e150b836a341dfc6dbf05aa20bc81d10b",
        "torch==2.7.1",
        "torchaudio==2.7.1",
    ),
    "chords": (
        "lv-chordia @ git+https://github.com/openmirlab/lv-chordia.git@d8ab9ac99bce081bb79065d717f96e2c3b2099c8",
        "torch==2.15.0",
    ),
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Install optional local harmony models.")
    parser.add_argument(
        "--research-key-model",
        action="store_true",
        help="Also install S-KEY weights, restricted to noncommercial research.",
    )
    args = parser.parse_args()
    uv = shutil.which("uv") or str(TOOLS / ("Scripts/uv.exe" if os.name == "nt" else "bin/uv"))
    python = ROOT / ".venv" / PYTHON
    if not Path(uv).is_file() or not python.exists():
        sys.exit("Run python3 scripts/setup.py first.")
    env = dict(os.environ, UV_CACHE_DIR=str(TOOLS / "cache"))
    for model, packages in MODELS.items():
        if model == "key" and not args.research_key_model:
            continue
        directory = TOOLS / "harmony" / model
        if not (directory / PYTHON).exists():
            subprocess.run([uv, "venv", "--python", str(python), str(directory)], env=env, check=True)
        subprocess.run(
            [uv, "pip", "install", "--python", str(directory / PYTHON), *packages], env=env, check=True
        )
    print("Chord model installed. New transcriptions will use it locally.")
    if args.research_key_model:
        print(
            "S-KEY weights are restricted to noncommercial research. Enable inference with MULEC_ENABLE_RESEARCH_KEY_MODEL=1."
        )
