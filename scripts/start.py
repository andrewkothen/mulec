#!/usr/bin/env python3
"""Start the built application, bound only to this computer."""

import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
python = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
if not python.exists():
    sys.exit("Run: uv sync --python 3.12, then npm ci --prefix frontend")
if not (ROOT / "frontend/out/index.html").exists() or "--build" in sys.argv:
    env = dict(os.environ, NEXT_TELEMETRY_DISABLED="1")
    subprocess.run(
        ["npm.cmd" if os.name == "nt" else "npm", "run", "build"], cwd=ROOT / "frontend", env=env, check=True
    )
print("\nMulec is ready at http://127.0.0.1:8765\nPress Ctrl+C to stop.\n", flush=True)
os.execv(
    str(python),
    [
        str(python),
        "-m",
        "uvicorn",
        "backend.api.app:create_app",
        "--factory",
        "--host",
        "127.0.0.1",
        "--port",
        "8765",
    ],
)
