"""Generate an original CC0 fixture without committing audio binaries."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.fixtures import make_demo  # noqa: E402

target = Path(sys.argv[1] if len(sys.argv) > 1 else "tmp/sunday-sketch.wav")
target.parent.mkdir(parents=True, exist_ok=True)
make_demo(target)
print(target.resolve())
