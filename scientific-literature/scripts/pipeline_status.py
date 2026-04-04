from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from pipeline_state import PipelineState


def main() -> int:
    parser = argparse.ArgumentParser(description="Show pipeline step status.")
    parser.add_argument("--state-file", required=True)
    args = parser.parse_args()
    PipelineState(args.state_file).print_status()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
