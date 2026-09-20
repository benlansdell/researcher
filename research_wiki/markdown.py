from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

MANAGED_START = "<!-- research-wiki:start -->"
MANAGED_END = "<!-- research-wiki:end -->"
REFS_START = "<!-- research-wiki:references:start -->"
REFS_END = "<!-- research-wiki:references:end -->"
RESEARCH_START = "<!-- research-wiki:research:start -->"
RESEARCH_END = "<!-- research-wiki:research:end -->"

TAG_RE = re.compile(r"(?<![\w/])#([A-Za-z0-9_/-]+)")
WIKILINK_RE = re.compile(r"!?\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")


def note_title(path: Path, text: str) -> str:
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            header = text[4:end]
            for line in header.splitlines():
                if line.lower().startswith("title:"):
                    value = line.split(":", 1)[1].strip().strip('"\'')
                    if value:
                        return value
    m = re.search(r"^#\s+(.+?)\s*$", text, re.MULTILINE)
    return m.group(1).strip() if m else path.stem


def tags(text: str) -> set[str]:
    return {m.group(1).lower() for m in TAG_RE.finditer(text)}


def human_text(text: str) -> str:
    """Remove the agent-owned top-level block before analysis."""
    return replace_region(text, MANAGED_START, MANAGED_END, None)


def replace_region(text: str, start: str, end: str, body: str | None) -> str:
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    if body is None:
        return pattern.sub("", text).strip() + "\n"
    block = f"{start}\n{body.rstrip()}\n{end}"
    if pattern.search(text):
        return pattern.sub(block, text)
    return text.rstrip() + "\n\n" + block + "\n"


def upsert_named_region(text: str, heading: str, start: str, end: str, body: str) -> str:
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    block = f"{start}\n{body.rstrip()}\n{end}"
    if pattern.search(text):
        return pattern.sub(block, text)
    return text.rstrip() + f"\n\n{heading}\n\n{block}\n"


def slugify_block_id(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9-]+", "-", value.strip().lower()).strip("-")
    return value[:60] or "note"


def obsidian_link(relpath: str) -> str:
    p = relpath.replace("\\", "/")
    return f"[[{p[:-3] if p.lower().endswith('.md') else p}]]"


def existing_wikilinks(text: str) -> set[str]:
    return {m.group(1).strip() for m in WIKILINK_RE.finditer(text)}


def safe_filename(title: str) -> str:
    title = re.sub(r"[\\/:*?\"<>|]", "-", title).strip().strip(".")
    return title[:120] or "Untitled"


def topic_template(title: str) -> str:
    return f"""---
type: topic
tags:
  - research/topic
---

# {title}

## Summary

## My observations

{REFS_START}
{REFS_END}

## Research

{RESEARCH_START}
{RESEARCH_END}

## Related
"""


def add_reference(topic_text: str, source_relpath: str, excerpt: str) -> str:
    source = obsidian_link(source_relpath)
    entry = f"- {source}\n  > {excerpt.strip().replace(chr(10), ' ')}"
    existing = _region_body(topic_text, REFS_START, REFS_END)
    if source in existing and excerpt.strip() in existing:
        return topic_text
    body = (existing.rstrip() + "\n" + entry).strip()
    return upsert_named_region(topic_text, "## My observations", REFS_START, REFS_END, body)


def add_research_link(topic_text: str, research_relpath: str) -> str:
    link = f"- {obsidian_link(research_relpath)}"
    existing = _region_body(topic_text, RESEARCH_START, RESEARCH_END)
    if link in existing:
        return topic_text
    body = (existing.rstrip() + "\n" + link).strip()
    return upsert_named_region(topic_text, "## Research", RESEARCH_START, RESEARCH_END, body)


def _region_body(text: str, start: str, end: str) -> str:
    m = re.search(re.escape(start) + r"\n?(.*?)\n?" + re.escape(end), text, re.DOTALL)
    return m.group(1).strip() if m else ""
