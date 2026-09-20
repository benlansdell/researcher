from __future__ import annotations

from pathlib import Path
from pydantic import BaseModel, Field
import yaml


DEFAULT_CONFIG_NAME = ".research-wiki.yaml"


class ModelConfig(BaseModel):
    provider: str = "openai"
    reason: str = "gpt-5.6"
    research: str = "gpt-5.6"


class ProcessingConfig(BaseModel):
    source_dirs: list[str] = Field(default_factory=lambda: ["Daily", "Notes"])
    research_dir: str = "Research"
    research_runs_dir: str = "Research/Research Runs"
    ignore_dirs: list[str] = Field(default_factory=lambda: [".obsidian", ".research-wiki", "Templates"])
    research_tag: str = "research"
    opt_out_tag: str = "noresearchwiki"
    create_topics: bool = True
    max_existing_candidates: int = 12
    automatic_research: bool = True


class EditingConfig(BaseModel):
    managed_sections_only: bool = True
    include_source_excerpt: bool = True


class AppConfig(BaseModel):
    model: ModelConfig = Field(default_factory=ModelConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    editing: EditingConfig = Field(default_factory=EditingConfig)

    @classmethod
    def load(cls, vault: Path) -> "AppConfig":
        path = vault / DEFAULT_CONFIG_NAME
        if not path.exists():
            return cls()
        return cls.model_validate(yaml.safe_load(path.read_text()) or {})

    def save(self, vault: Path) -> Path:
        path = vault / DEFAULT_CONFIG_NAME
        path.write_text(yaml.safe_dump(self.model_dump(), sort_keys=False))
        return path
