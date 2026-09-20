from __future__ import annotations

import re
from collections import Counter
from .models import TopicCandidate
from .vault import VaultNote

WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{2,}")
STOP = {"the", "and", "for", "that", "this", "with", "from", "into", "about", "what", "when", "where", "which", "have", "has", "are", "was", "were", "not", "but", "can", "could", "would", "should", "they", "their", "there", "then", "than", "also", "some", "more", "very"}


def tokens(text: str) -> Counter[str]:
    return Counter(w.lower() for w in WORD_RE.findall(text) if w.lower() not in STOP)


def lexical_candidates(source_text: str, research_notes: list[VaultNote], limit: int = 12) -> list[TopicCandidate]:
    src = tokens(source_text)
    scored: list[tuple[float, VaultNote]] = []
    for note in research_notes:
        dst = tokens(note.title + "\n" + note.text[:3000])
        overlap = sum(min(src[k], dst[k]) for k in src.keys() & dst.keys())
        title_bonus = sum(2 for t in tokens(note.title) if t in src)
        score = overlap + title_bonus
        if score > 0:
            scored.append((score, note))
    scored.sort(key=lambda x: (-x[0], x[1].title.lower()))
    return [TopicCandidate(name=n.title, path=n.relpath, summary=n.text[:700]) for _, n in scored[:limit]]
