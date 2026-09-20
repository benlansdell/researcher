# research-wiki

A small Python curator for an Obsidian-style Markdown vault.

You write notes normally. `research-wiki` scans changed source notes, asks an LLM what durable concepts they relate to, updates/creates topic pages under `Research/`, and—when it sees `#research`—can perform web research and create a cited research-run note.

The design is deliberately conservative:

- Your Markdown remains the source of truth.
- The program only replaces its own explicitly marked regions in source notes.
- Topic-page references and research links also live in marked regions.
- A content-hash state file prevents reprocessing loops caused by the program's own writes.
- `--dry-run` lets you see which files would change before writing anything.
- `#noresearchwiki` opts a source note out entirely.

## Requirements

- Python 3.11+
- An OpenAI API key in `OPENAI_API_KEY`
- An Obsidian vault, or simply any directory containing Markdown notes

The OpenAI integration uses the Responses API with Pydantic structured outputs. `#research` requests use the Responses API web-search tool.

## Install

From this repository:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
export OPENAI_API_KEY="..."
```

For development/tests:

```bash
pip install -e '.[dev]'
pytest
```

## Initialize a vault

```bash
research-wiki init ~/Documents/Obsidian/MyVault
```

This creates:

```text
.research-wiki.yaml
.research-wiki/
Research/
Research/Research Runs/
```

It does **not** alter your existing Obsidian settings.

The default config is roughly:

```yaml
model:
  provider: openai
  reason: gpt-5.6
  research: gpt-5.6
processing:
  source_dirs:
    - Daily
    - Notes
  research_dir: Research
  research_runs_dir: Research/Research Runs
  ignore_dirs:
    - .obsidian
    - .research-wiki
    - Templates
  research_tag: research
  opt_out_tag: noresearchwiki
  create_topics: true
  max_existing_candidates: 12
  automatic_research: true
editing:
  managed_sections_only: true
  include_source_excerpt: true
```

Edit `.research-wiki.yaml` to match your vault layout and preferred models.

## First run: dry-run

```bash
research-wiki process ~/Documents/Obsidian/MyVault --dry-run
```

Then actually apply:

```bash
research-wiki process ~/Documents/Obsidian/MyVault
```

To process one note:

```bash
research-wiki process ~/Documents/Obsidian/MyVault \
  --file Daily/2026-09-13.md
```

## Continuous mode

```bash
research-wiki watch ~/Documents/Obsidian/MyVault
```

The watcher is intentionally simple. It debounces filesystem changes, then invokes the same hash-based processor. For an always-on deployment, run it with launchd/systemd rather than adding more lifecycle machinery to the app.

## What happens to a source note?

Given:

```md
# 2026-09-13

I've been thinking that phototropism might count as a very weak
form of agency rather than merely looking like agency.

#research
How does Michael Levin's conception of agency differ from Friston's
active inference framework?
```

The program leaves your text untouched and appends a managed block such as:

```md
<!-- research-wiki:start -->
## Related research

- [[Research/Agency in biology]]
- [[Research/Phototropism]]

## Generated research

- [[Research/Research Runs/2026-09-13 - Levin and active inference]]
<!-- research-wiki:end -->
```

On later runs, that block is replaced rather than duplicated.

## Topic pages

Existing topic pages are preferred over creating near-duplicates. Candidate retrieval is currently lexical and deliberately simple; the LLM receives only the top candidate pages and decides which are genuinely related.

A generated topic starts as:

```md
---
type: topic
tags:
  - research/topic
---

# Phototropism

## Summary

## My observations

<!-- research-wiki:references:start -->
<!-- research-wiki:references:end -->

## Research

<!-- research-wiki:research:start -->
<!-- research-wiki:research:end -->

## Related
```

The agent owns only the marked reference/research regions. You can freely edit the rest.

## Research runs

A `#research` request creates a dated note under `Research/Research Runs/` with:

- the triggering source note
- the question
- a summary
- findings
- connections to existing topics
- open questions
- external sources/citations

The research call uses OpenAI's built-in web-search tool, so no separate search API is required.

## State and idempotence

`.research-wiki/state.json` stores SHA-256 hashes of processed files. After the program writes a file, it records the resulting hash. This is what prevents its own writes from repeatedly triggering processing.

Delete the relevant entry from the state file (or the state file itself) if you deliberately want to force reprocessing.

## Current intentionally-small scope

Version 0.1 does **not** yet include embeddings, PDF/paper ingestion, typed graph edges, topic-summary rewriting, Git integration, or a review/approval UI. Those are good second-stage features; the first goal is to learn whether the curation behavior is actually useful on a real vault.

## Safety / backup recommendation

Run with `--dry-run` first and keep your vault in Git or another backup system before using automatic writes. Although this app confines its own source-note edits to managed blocks, any software writing into a knowledge base should be treated as fallible.
