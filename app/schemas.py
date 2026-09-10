from typing import Any, Literal
from pydantic import AliasChoices, BaseModel, Field


class BrokerEvent(BaseModel):
    event_id: str = Field(..., description="Unique event id")
    session_id: str = Field(..., description="Target session")
    type: Literal["audio", "transcript", "tool_call", "status", "error"]
    payload: dict[str, Any] = Field(default_factory=dict)


class BrokerResponse(BaseModel):
    ok: bool = True
    message: str = "Event routed"
    event_id: str | None = None


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "vivaguard-broker"


class DebriefRequest(BaseModel):
    ground_truth: str = ""
    target_question: str = ""
    full_transcript: str = ""
    history: list[dict[str, Any]] = Field(default_factory=list)


# Test Interview Simulator (Mode A) Schemas
class TestGenerateRequest(BaseModel):
    domain: str = Field(..., description="Interview domain or defense topic")
    format: str = Field("Technical Deep Dive", description="Technical Deep Dive, STAR Behavioral, or Panel Cross-Examination")
    question_count: int = Field(3, description="Number of questions (3, 5, or 10)")
    difficulty_level: str = Field("Mid-Level", description="Baseline difficulty tier: Junior, Mid-Level, or Senior")
    adaptive_mode: bool = Field(True, description="Enable adaptive difficulty progression")


class GeneratedQuestionSchema(BaseModel):
    question_id: int
    question_text: str
    difficulty: str = Field("Mid-Level", description="Question difficulty: Junior, Mid-Level, or Senior")
    difficulty_level: str = Field("Mid-Level", description="Alias for question difficulty level")
    evaluation_criteria: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("evaluation_criteria", "criteria")
    )


class TestGenerateResponse(BaseModel):
    session_id: str
    domain: str
    format: str
    difficulty_level: str = "Mid-Level"
    adaptive_mode: bool = True
    questions: list[GeneratedQuestionSchema]


class QuestionEvaluateRequest(BaseModel):
    question_id: int
    question_text: str
    evaluation_criteria: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("evaluation_criteria", "criteria"),
        description="Evaluation criteria or key checkpoint requirements for grading"
    )
    transcript: str = ""
    difficulty_level: str = Field("Mid-Level", description="Difficulty tier under which response is evaluated")
    adaptive_mode: bool = Field(True, description="Whether adaptive progression is active")


class QuestionEvaluateResponse(BaseModel):
    question_id: int
    transcript: str
    overall_score: int
    accuracy_rating: str
    strengths: list[str]
    weaknesses: list[str]
    actionable_improvements: str
    ideal_response_summary: str
    difficulty_evaluated: str = "Mid-Level"
    next_recommended_difficulty: str = "Mid-Level"


class TestCumulativeReportRequest(BaseModel):
    domain: str = ""
    format: str = ""
    evaluations: list[dict[str, Any]] = Field(default_factory=list)
