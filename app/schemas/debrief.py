from typing import Any
from pydantic import BaseModel, Field


class DebriefRequest(BaseModel):
    ground_truth: str = Field("", description="Target ground truth answer facts or ideal rubric criteria", example="LSM tree buffer flushing uses sequential log writes to optimize throughput.")
    target_question: str = Field("", description="Main topic question asked during the defense session", example="How does LSM tree buffering minimize disk write amplification?")
    full_transcript: str = Field("", description="Complete transcript of candidate spoken responses throughout session", example="I implemented a log-structured merge tree with sequential append buffers...")
    history: list[dict[str, Any]] = Field(default_factory=list, description="List of real-time evaluation events captured during session")


class StarAnswerSchema(BaseModel):
    Situation: str = Field(..., description="Context framing of the candidate response")
    Task: str = Field(..., description="Core challenge or technical requirement")
    Action: str = Field(..., description="Actions and methodology articulated by candidate")
    Result: str = Field(..., description="Outcome and performance defense summary")


class CriticalShiftSchema(BaseModel):
    timestamp_sec: float = Field(..., description="Timestamp in seconds when key signal shift occurred")
    signal: str = Field(..., description="Signal level: GREEN, AMBER, or RED")
    spoken_phrase: str = Field(..., description="Spoken phrase or coaching nudge at signal shift")
    coaching_feedback: str = Field(..., description="Actionable coaching feedback provided to candidate")


class DebriefResponse(BaseModel):
    overall_score: int = Field(..., description="Overall defense score (0-100)", example=85)
    clarity_score: int = Field(..., description="Clarity and delivery sub-score (0-100)", example=88)
    confidence_score: int = Field(..., description="Poise and vocal confidence sub-score (0-100)", example=82)
    technical_depth_score: int = Field(..., description="Technical depth and accuracy sub-score (0-100)", example=86)
    green_percentage: int = Field(..., description="Percentage of GREEN signals recorded", example=75)
    amber_percentage: int = Field(..., description="Percentage of AMBER signals recorded", example=20)
    red_percentage: int = Field(..., description="Percentage of RED signals recorded", example=5)
    total_fillers: int = Field(..., description="Total count of filler words detected (e.g. um, uh, like)", example=2)
    total_technical_keywords: int = Field(..., description="Total count of domain technical keywords mentioned", example=6)
    dodged_questions_count: int = Field(..., description="Count of questions dodged or answered vaguely", example=0)
    total_duration_sec: float = Field(..., description="Total defense session duration in seconds", example=180.5)
    ideal_star_answer: StarAnswerSchema = Field(..., description="STAR framework breakdown of ideal answer structure")
    key_strengths: list[str] = Field(..., description="Highlighted technical strengths")
    key_weaknesses: list[str] = Field(..., description="Highlighted areas for improvement")
    suggested_followup_questions: list[str] = Field(..., description="Recommended follow-up questions for candidate practice")
    critical_shifts: list[CriticalShiftSchema] = Field(..., description="Recorded timeline shifts during interrogation")
    defense_verdict: str = Field(..., description="Final defense evaluation verdict", example="Strong Technical Defense")

