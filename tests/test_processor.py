from pathlib import Path
from research_wiki.config import AppConfig
from research_wiki.models import NoteAnalysis, Observation, ResearchRequest, ResearchResult, TopicLink
from research_wiki.processor import Processor


class FakeLLM:
    def analyze_note(self, source_path, text, candidates):
        return NoteAnalysis(
            observations=[
                Observation(
                    text="Phototropism may be a minimal form of agency.",
                    existing_topics=[TopicLink(name="Agency in biology", relationship="example-of")],
                    new_topics=["Phototropism"],
                )
            ],
            research_requests=[ResearchRequest(question="How does Levin differ from active inference?", related_topics=["Agency in biology"])],
        )

    def research(self, question, vault_context):
        return ResearchResult(
            title="Levin and active inference",
            summary="A compact comparison.",
            findings=["They overlap but are not identical."],
            connections=["Agency in biology"],
            open_questions=["How should agency be operationalized?"],
            sources=["[Example](https://example.com)"],
        )


def setup_vault(tmp_path: Path):
    (tmp_path / "Daily").mkdir()
    (tmp_path / "Research").mkdir()
    (tmp_path / "Research" / "Research Runs").mkdir()
    (tmp_path / "Daily" / "2026-09-13.md").write_text("# 2026-09-13\n\nPhototropism seems agentic. #research\n")
    (tmp_path / "Research" / "Agency in biology.md").write_text("# Agency in biology\n")


def test_processor_writes_and_is_idempotent(tmp_path):
    setup_vault(tmp_path)
    p = Processor(tmp_path, AppConfig(), llm=FakeLLM())
    first = p.process()
    assert first.changes
    daily = (tmp_path / "Daily" / "2026-09-13.md").read_text()
    assert "<!-- research-wiki:start -->" in daily
    assert "[[Research/Agency in biology]]" in daily
    assert (tmp_path / "Research" / "Phototropism.md").exists()
    runs = list((tmp_path / "Research" / "Research Runs").glob("*.md"))
    assert len(runs) == 1

    second = Processor(tmp_path, AppConfig(), llm=FakeLLM()).process()
    assert second.changes == []
