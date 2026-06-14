from enum import StrEnum

from pydantic import BaseModel, Field


class AgentName(StrEnum):
    coordinator = "coordinator"
    product_recommendation = "product_recommendation"
    review_summarization = "review_summarization"
    price_comparison = "price_comparison"
    faq_policy = "faq_policy"


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    session_id: str | None = Field(default=None, max_length=128)
    customer_preferences: dict[str, str | int | float | bool] = Field(default_factory=dict)


class SourceRecord(BaseModel):
    table: str
    id: str
    label: str


class ChatResponse(BaseModel):
    session_id: str
    agent: AgentName
    answer: str
    sources: list[SourceRecord] = Field(default_factory=list)
    pii_redacted: bool = False


class AgentRoute(BaseModel):
    agent: AgentName
    rationale: str


class SpecialistAnswer(BaseModel):
    answer: str
    sources: list[SourceRecord] = Field(default_factory=list)


class TranscriptionResponse(BaseModel):
    text: str
    pii_redacted: bool
