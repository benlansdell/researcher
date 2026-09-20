from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


class TopicCandidate(BaseModel):
    name: str
    path: str
    summary: str = ""


class TopicLink(BaseModel):
    name: str
    relationship: str = "related-to"
    reason: str = ""


class Observation(BaseModel):
    text: str
    existing_topics: list[TopicLink] = Field(default_factory=list)
    new_topics: list[str] = Field(default_factory=list)


class ResearchRequest(BaseModel):
    question: str
    related_topics: list[str] = Field(default_factory=list)


class NoteAnalysis(BaseModel):
    observations: list[Observation] = Field(default_factory=list)
    research_requests: list[ResearchRequest] = Field(default_factory=list)


class ResearchResult(BaseModel):
    title: str
    summary: str
    findings: list[str] = Field(default_factory=list)
    connections: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)


class Change(BaseModel):
    path: str
    action: Literal["create", "update"]
    content: str
