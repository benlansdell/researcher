from __future__ import annotations

import json
from .config import AppConfig
from .models import NoteAnalysis, ResearchResult, TopicCandidate


class OpenAILLM:
    def __init__(self, config: AppConfig):
        self.config = config
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("The OpenAI SDK is required for live LLM calls. Install the package with `pip install -e .`.") from exc
        self.client = OpenAI()

    def analyze_note(self, source_path: str, text: str, candidates: list[TopicCandidate]) -> NoteAnalysis:
        prompt = f"""You are curating an Obsidian research wiki.

SOURCE NOTE: {source_path}

CONTENT:
{text}

EXISTING RESEARCH TOPICS (candidate matches):
{json.dumps([c.model_dump() for c in candidates], indent=2)}

Extract only substantive observations, claims, questions, people, papers, theories, or concepts that merit connection to a research wiki.
Use existing topics when genuinely relevant. Create new topics conservatively: only when the idea is durable and there is no suitable existing topic.
If the text contains the tag #{self.config.processing.research_tag}, convert the nearby substantive question(s) into research_requests. Do not treat the tag itself as content.
Return concise observations, not every sentence.
"""
        return self._parse(self.config.model.reason, prompt, NoteAnalysis)

    def research(self, question: str, vault_context: str) -> ResearchResult:
        prompt = f"""Research this question for a personal research wiki:

{question}

Relevant existing vault context:
{vault_context}

Prefer primary sources, original papers, books, official documentation, and original authors. Clearly distinguish evidence from interpretation. Produce a compact research note with useful citations. Put each source as a Markdown link or a citation containing a URL in the sources field.
"""
        response = self.client.responses.parse(
            model=self.config.model.research,
            tools=[{"type": "web_search"}],
            input=prompt,
            text_format=ResearchResult,
        )
        return _parsed_response(response, ResearchResult)

    def _parse(self, model: str, prompt: str, schema):
        response = self.client.responses.parse(model=model, input=prompt, text_format=schema)
        return _parsed_response(response, schema)


def _parsed_response(response, schema):
    # responses.parse stores parsed Pydantic data on output_text items.
    for output in response.output:
        if getattr(output, "type", None) != "message":
            continue
        for item in getattr(output, "content", []):
            parsed = getattr(item, "parsed", None)
            if parsed is not None:
                return parsed
    raise RuntimeError(f"Model returned no parsed {schema.__name__} result")
