from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

STATE_DIR = ".research-wiki"
STATE_FILE = "state.json"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class StateStore:
    def __init__(self, vault: Path):
        self.root = vault / STATE_DIR
        self.path = self.root / STATE_FILE
        self.root.mkdir(parents=True, exist_ok=True)
        self.data: dict[str, Any] = {"files": {}}
        if self.path.exists():
            try:
                self.data = json.loads(self.path.read_text())
            except json.JSONDecodeError:
                pass

    def hash_for(self, relpath: str) -> str | None:
        return self.data.get("files", {}).get(relpath, {}).get("hash")

    def is_changed(self, relpath: str, content: str) -> bool:
        return self.hash_for(relpath) != sha256_text(content)

    def mark(self, relpath: str, content: str) -> None:
        self.data.setdefault("files", {})[relpath] = {"hash": sha256_text(content)}

    def save(self) -> None:
        self.path.write_text(json.dumps(self.data, indent=2, sort_keys=True) + "\n")
