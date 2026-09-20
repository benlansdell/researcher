from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable

from .config import AppConfig
from .env import load_env
from .llm import OpenAILLM
from .markdown import (
    MANAGED_END,
    MANAGED_START,
    add_reference,
    add_research_link,
    human_text,
    obsidian_link,
    replace_region,
    safe_filename,
    tags,
    topic_template,
)
from .models import Change, NoteAnalysis, ResearchResult
from .retrieval import lexical_candidates
from .state import StateStore
from .vault import Vault, VaultNote


@dataclass
class ProcessResult:
    changes: list[Change]
    skipped: list[str]


class Processor:
    def __init__(self, vault_root: Path, config: AppConfig | None = None, llm=None):
        load_env(vault_root)
        self.config = config or AppConfig.load(vault_root)
        self.vault = Vault(vault_root, self.config)
        self.state = StateStore(vault_root)
        self.llm = llm or OpenAILLM(self.config)

    def process(self, *, dry_run: bool = False, only_file: str | None = None) -> ProcessResult:
        changes: list[Change] = []
        skipped: list[str] = []
        source_notes = self.vault.source_notes()
        if only_file:
            source_notes = [n for n in source_notes if n.relpath == only_file]
            if not source_notes:
                raise FileNotFoundError(f"Source note not found: {only_file}")

        for note in source_notes:
            if not self.state.is_changed(note.relpath, note.text):
                skipped.append(note.relpath)
                continue
            if self.config.processing.opt_out_tag.lower() in tags(note.text):
                self.state.mark(note.relpath, note.text)
                skipped.append(note.relpath)
                continue
            changes.extend(self._process_note(note, dry_run=dry_run))

        if not dry_run:
            self.state.save()
        return ProcessResult(changes=changes, skipped=skipped)

    def _process_note(self, note: VaultNote, *, dry_run: bool) -> list[Change]:
        research_notes = self.vault.research_notes()
        source = human_text(note.text)
        candidates = lexical_candidates(source, research_notes, self.config.processing.max_existing_candidates)
        analysis: NoteAnalysis = self.llm.analyze_note(note.relpath, source, candidates)

        changes: list[Change] = []
        topic_paths: dict[str, str] = {n.title.lower(): n.relpath for n in research_notes}
        related_links: list[str] = []

        for obs in analysis.observations:
            topic_names = [x.name for x in obs.existing_topics]
            if self.config.processing.create_topics:
                topic_names += obs.new_topics
            for topic_name in _uniq(topic_names):
                rel = topic_paths.get(topic_name.lower())
                if rel is None:
                    rel = f"{self.config.processing.research_dir}/{safe_filename(topic_name)}.md"
                    topic_paths[topic_name.lower()] = rel
                    current = topic_template(topic_name)
                    action = "create"
                else:
                    path = self.vault.root / rel
                    current = path.read_text(encoding="utf-8") if path.exists() else topic_template(topic_name)
                    action = "update" if path.exists() else "create"
                updated = add_reference(current, note.relpath, obs.text)
                if updated != current:
                    changes.append(Change(path=rel, action=action, content=updated))
                    if not dry_run:
                        self._write(rel, updated)
                related_links.append(obsidian_link(rel))

        research_links: list[str] = []
        if self.config.processing.automatic_research:
            for request in analysis.research_requests:
                result = self.llm.research(request.question, self._research_context(request.related_topics))
                rel, content = self._render_research_run(note, request.question, result)
                changes.append(Change(path=rel, action="create", content=content))
                if not dry_run:
                    self._write(rel, content)
                research_links.append(obsidian_link(rel))
                for topic_name in _uniq(request.related_topics + result.connections):
                    topic_rel = topic_paths.get(topic_name.lower())
                    if not topic_rel:
                        continue
                    path = self.vault.root / topic_rel
                    if not path.exists():
                        continue
                    current = path.read_text(encoding="utf-8")
                    updated = add_research_link(current, rel)
                    if updated != current:
                        changes.append(Change(path=topic_rel, action="update", content=updated))
                        if not dry_run:
                            self._write(topic_rel, updated)

        managed_lines = []
        if related_links:
            managed_lines += ["## Related research", "", *[f"- {x}" for x in _uniq(related_links)]]
        if research_links:
            if managed_lines:
                managed_lines.append("")
            managed_lines += ["## Generated research", "", *[f"- {x}" for x in _uniq(research_links)]]

        final_note = replace_region(note.text, MANAGED_START, MANAGED_END, "\n".join(managed_lines).strip())
        if final_note != note.text:
            changes.append(Change(path=note.relpath, action="update", content=final_note))
            if not dry_run:
                self._write(note.relpath, final_note)
                self.state.mark(note.relpath, final_note)
        else:
            self.state.mark(note.relpath, note.text)
        return changes

    def _research_context(self, related_topics: list[str]) -> str:
        notes = self.vault.research_notes()
        if related_topics:
            wanted = {x.lower() for x in related_topics}
            notes = [n for n in notes if n.title.lower() in wanted] or notes
        return "\n\n".join(f"# {n.title}\n{n.text[:2500]}" for n in notes[:8])

    def _render_research_run(self, source: VaultNote, question: str, result: ResearchResult) -> tuple[str, str]:
        day = date.today().isoformat()
        title = result.title.strip() or question[:80]
        rel = f"{self.config.processing.research_runs_dir}/{day} - {safe_filename(title)}.md"
        findings = "\n".join(f"- {x}" for x in result.findings) or "- None recorded."
        connections = "\n".join(f"- [[{x}]]" for x in result.connections) or "- None."
        opens = "\n".join(f"- {x}" for x in result.open_questions) or "- None."
        sources = "\n".join(f"{i}. {x}" for i, x in enumerate(result.sources, 1)) or "1. No external sources returned."
        content = f"""---
type: research-run
created: {day}
trigger: \"{obsidian_link(source.relpath)}\"
---

# {title}

## Question

{question}

## Summary

{result.summary}

## Findings

{findings}

## Connections

{connections}

## Open questions

{opens}

## Sources

{sources}
"""
        return rel, content

    def _write(self, relpath: str, content: str) -> None:
        path = self.vault.root / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        self.state.mark(relpath, content)


def _uniq(items: list[str]) -> list[str]:
    seen = set()
    out = []
    for item in items:
        key = item.strip().lower()
        if item.strip() and key not in seen:
            seen.add(key)
            out.append(item.strip())
    return out
