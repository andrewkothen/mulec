#!/usr/bin/env python3
"""One-time local installation. Runtime does not require network access."""
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
if not npm:
    sys.exit("Install Node.js 22+ (including npm), then run this script again.")
uv = shutil.which("uv")
if not uv:
    target = ROOT / ".tools"
    local = target / ("Scripts/uv.exe" if os.name == "nt" else "bin/uv")
    if not local.exists():
        subprocess.run([sys.executable, "-m", "pip", "install", "--target", str(target), "uv"], check=True)
    uv = str(local)
env = dict(os.environ, UV_PYTHON_INSTALL_DIR=str(ROOT / ".tools/python"),
           UV_CACHE_DIR=str(ROOT / ".tools/cache"), NEXT_TELEMETRY_DISABLED="1")
subprocess.run([uv, "sync", "--locked", "--python", "3.12"], env=env, check=True)
subprocess.run([npm, "ci", "--no-fund"], cwd=ROOT / "frontend", env=env, check=True)
subprocess.run([npm, "run", "build"], cwd=ROOT / "frontend", env=env, check=True)
print("\nInstalled. Start Mulec with: python3 scripts/start.py")
