"""Pipeline progress tracking."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_STEPS = ["A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8"]
DEPENDENCIES = {
    "A2": ["A1"],
    "A3": ["A2"],
    "A4": ["A3"],
    "A5": ["A4"],
    "A6": ["A5"],
    "A7": ["A6"],
    "A8": ["A7"],
}


class PipelineState:
    def __init__(self, state_file: str):
        self.path = Path(state_file)
        self.data = self._load()

    def _load(self) -> dict[str, Any]:
        if self.path.exists():
            return json.loads(self.path.read_text(encoding="utf-8"))
        return {"steps": {step: {"status": "TODO"} for step in DEFAULT_STEPS}, "updated_at": None}

    def _save(self) -> None:
        self.data["updated_at"] = datetime.now(timezone.utc).date().isoformat()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def mark_step(self, step_name: str, status: str, notes: str | None = None, stats: dict[str, Any] | None = None) -> None:
        step = self.data.setdefault("steps", {}).setdefault(step_name, {})
        step["status"] = status
        if notes:
            step["notes"] = notes
        if stats:
            step["stats"] = stats
        self._save()

    def check_dependencies(self, step_name: str) -> tuple[bool, list[str]]:
        missing = []
        for dep in DEPENDENCIES.get(step_name, []):
            dep_status = self.data.get("steps", {}).get(dep, {}).get("status", "TODO")
            if dep_status not in {"DONE", "MERGED"}:
                missing.append(dep)
        return not missing, missing

    def get_next_steps(self) -> list[str]:
        ready = []
        for step, payload in self.data.get("steps", {}).items():
            if payload.get("status") in {"TODO", "IN_PROGRESS"}:
                ok, _ = self.check_dependencies(step)
                if ok:
                    ready.append(step)
        return sorted(ready)

    def print_status(self) -> None:
        for step in sorted(self.data.get("steps", {})):
            status = self.data["steps"][step].get("status", "TODO")
            print(f"{step}: {status}")
