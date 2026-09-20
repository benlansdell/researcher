from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from .config import AppConfig
from .markdown import note_title


@dataclass
class VaultNote:
    path: Path
    relpath: str
    text: str
    title: str


class Vault:
    def __init__(self, root: Path, config: AppConfig):
        self.root = root.resolve()
        self.config = config

    def read_note(self, path: Path) -> VaultNote:
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(self.root).as_posix()
        return VaultNote(path, rel, text, note_title(path, text))

    def source_notes(self) -> list[VaultNote]:
        notes: list[VaultNote] = []
        for dirname in self.config.processing.source_dirs:
            base = self.root / dirname
            if not base.exists():
                continue
            for path in base.rglob("*.md"):
                if self._ignored(path):
                    continue
                notes.append(self.read_note(path))
        return sorted(notes, key=lambda n: n.relpath)

    def research_notes(self) -> list[VaultNote]:
        base = self.root / self.config.processing.research_dir
        runs = (self.root / self.config.processing.research_runs_dir).resolve()
        if not base.exists():
            return []
        out = []
        for path in base.rglob("*.md"):
            try:
                path.resolve().relative_to(runs)
                continue
            except ValueError:
                pass
            out.append(self.read_note(path))
        return out

    def _ignored(self, path: Path) -> bool:
        rel_parts = path.relative_to(self.root).parts
        return any(part in self.config.processing.ignore_dirs for part in rel_parts)
