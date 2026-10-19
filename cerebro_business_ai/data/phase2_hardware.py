"""Capture a Phase 2 hardware snapshot through the shared ResourceGuard."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "ai-service"))
from app.resource_guard import ResourceGuard  # noqa: E402

if __name__ == "__main__":
    guard = ResourceGuard()
    output = ROOT / "data" / "phase2" / "resource_snapshot.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(guard.as_dict(), indent=2), encoding="utf-8")
    print(output.read_text(encoding="utf-8"))
