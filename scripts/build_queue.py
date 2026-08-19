#!/usr/bin/env python3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from threads_automation.builder import write_content_queue  # noqa: E402


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(f"Usage: {Path(__file__).name} quiz|normal CONTENT_ID")
    print(write_content_queue(sys.argv[2], sys.argv[1]))
