"""Master API v1 Router consolidating all endpoint path registrations and mapping each route to its single-function handler with OpenAPI metadata."""

from fastapi import APIRouter

from app.api.v1.functions import (
    audio_websocket_endpoint,
    convert_elevenlabs_tts,
    convert_text_to_audio,
    copilot_websocket_endpoint,
    cumulative_test_report,
    debrief_endpoint,
    evaluate_test_audio,
    evaluate_test_question,
    generate_test_interview,
    health,
    llm_response_endpoint,
    route_event,
    speech_to_speech_endpoint,
    speech_to_text_endpoint,
    websocket_endpoint,
)
from app.schemas.broker import BrokerResponse
from app.schemas.debrief import DebriefResponse
from app.schemas.health import HealthResponse
from app.schemas.test_interview import QuestionEvaluateResponse, TestCumulativeReportResponse, TestGenerateResponse
from app.schemas.tts import TTSResponse

router = APIRouter()

# Health check
router.add_api_route(
    "/health",
    health,
    methods=["GET"],
    response_model=HealthResponse,
    tags=["Health Check"],
    summary="Service Health Check",
    description="Returns backend broker status and service readiness for health checks.",
)

# Broker routing
router.add_api_route(
    "/api/v1/route",
    route_event,
    methods=["POST"],
    response_model=BrokerResponse,
    tags=["Event Broker"],
    summary="Route Live Session Event",
    description="Routes a real-time event (audio, transcript, status, error) to active session WebSocket connections.",
)

# Debrief report
router.add_api_route(
    "/api/debrief",
    debrief_endpoint,
    methods=["POST"],
    response_model=DebriefResponse,
    tags=["Debrief & Evaluation"],
    summary="Generate Post-Defense Session Debrief Report",
    description="Analyzes full transcript and session history to produce a comprehensive STAR framework debrief report with sub-scores and verdict.",
)
router.add_api_route(
    "/api/v1/debrief",
    debrief_endpoint,
    methods=["POST"],
    response_model=DebriefResponse,
    tags=["Debrief & Evaluation"],
    summary="Generate Post-Defense Session Debrief Report (v1)",
    description="Alias route to generate a post-defense session debrief report containing STAR analysis, sub-scores, and final verdict.",
)

# ---------------------------------------------------------------------------
# 3-Endpoint Modular Pipeline (STT -> LLM Response -> ElevenLabs TTS)
# ---------------------------------------------------------------------------

# Endpoint 1: Speech-to-Text via AssemblyAI STT
router.add_api_route(
    "/api/v1/speech-to-text",
    speech_to_text_endpoint,
    methods=["POST"],
    response_model=None,
    tags=["Pipeline - Step 1: Speech-to-Text"],
    summary="Convert Spoken Audio to Text (AssemblyAI STT)",
    description="Endpoint 1: Accepts recorded audio binary upload and returns transcribed text via AssemblyAI Speech-to-Text.",
)
router.add_api_route(
    "/api/v1/stt",
    speech_to_text_endpoint,
    methods=["POST"],
    response_model=None,
    tags=["Pipeline - Step 1: Speech-to-Text"],
    summary="Convert Spoken Audio to Text (Alias)",
    description="Alias route to transcribe recorded audio via AssemblyAI Speech-to-Text.",
)

# Endpoint 2: LLM Response & Evaluation
router.add_api_route(
    "/api/v1/llm-response",
    llm_response_endpoint,
    methods=["POST"],
    response_model=QuestionEvaluateResponse,
    tags=["Pipeline - Step 2: LLM Response"],
    summary="Generate LLM Response & Evaluation",
    description="Endpoint 2: Evaluates prompt/transcript against criteria using Gemini LLM and generates structured response answer & feedback.",
)
router.add_api_route(
    "/api/v1/interview/grade",
    evaluate_test_question,
    methods=["POST"],
    response_model=QuestionEvaluateResponse,
    tags=["Technical Defense"],
    summary="Grade Candidate Response (Alias)",
    description="Alias route to grade candidate text answer, calculate next adaptive difficulty level, and broadcast grade_result via WebSocket if session_id is provided.",
)

# Endpoint 3: Text-to-Audio via ElevenLabs TTS
router.add_api_route(
    "/api/v1/elevenlabs/tts",
    convert_elevenlabs_tts,
    methods=["POST"],
    response_model=None,
    tags=["Pipeline - Step 3: Text-to-Audio"],
    summary="Convert Response Text to Spoken Audio (ElevenLabs TTS)",
    description="Endpoint 3: Converts response text into high-quality MP3 speech audio via ElevenLabs API. Supports binary audio stream or base64 JSON output.",
)
router.add_api_route(
    "/api/v1/text-to-audio",
    convert_elevenlabs_tts,
    methods=["POST"],
    response_model=None,
    tags=["Pipeline - Step 3: Text-to-Audio"],
    summary="Convert Response Text to Audio (Alias)",
    description="Alias endpoint for converting response text to ElevenLabs spoken audio.",
)
router.add_api_route(
    "/api/v1/tts",
    convert_text_to_audio,
    methods=["POST"],
    response_model=None,
    tags=["Pipeline - Step 3: Text-to-Audio"],
    summary="Convert Text to Audio (Compatibility Alias)",
    description="Compatibility alias for the VivaGuard text-to-audio endpoint.",
)

# Technical Defense - Question Generation
router.add_api_route(
    "/api/v1/test-interview/generate",
    generate_test_interview,
    methods=["POST"],
    response_model=TestGenerateResponse,
    tags=["Technical Defense"],
    summary="Generate Defense Questions",
    description="Generates AI-backed technical defense questions and evaluation criteria rubrics tailored to a domain and difficulty level.",
)
router.add_api_route(
    "/api/v1/interview/questions/generate",
    generate_test_interview,
    methods=["POST"],
    response_model=TestGenerateResponse,
    tags=["Technical Defense"],
    summary="Generate Defense Questions (Alias)",
    description="Alias endpoint for generating domain-specific technical defense questions and scoring criteria.",
)

# Technical Defense - Audio Evaluation
router.add_api_route(
    "/api/v1/test-interview/evaluate-audio",
    evaluate_test_audio,
    methods=["POST"],
    response_model=QuestionEvaluateResponse,
    tags=["Technical Defense"],
    summary="Transcribe and Evaluate Multipart Audio Answer",
    description="Transcribes an uploaded audio file using AssemblyAI Speech-to-Text and evaluates the resulting transcript against rubric criteria.",
)

# Technical Defense - Cumulative Report
router.add_api_route(
    "/api/v1/test-interview/cumulative-report",
    cumulative_test_report,
    methods=["POST"],
    response_model=TestCumulativeReportResponse,
    tags=["Technical Defense"],
    summary="Generate Cumulative Defense Readiness Report",
    description="Compiles overall session performance across all answered defense questions, calculating aggregate readiness percentage and action plan.",
)

# WebSockets
router.add_api_websocket_route("/ws", websocket_endpoint)
router.add_api_websocket_route("/ws/copilot", copilot_websocket_endpoint)
router.add_api_websocket_route("/ws/audio", audio_websocket_endpoint)
router.add_api_websocket_route("/ws/speech-to-speech", speech_to_speech_endpoint)



