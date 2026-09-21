from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.deps import assemblyai, broker
from app.api.v1.api import api_router
from app.core.config import settings

tags_metadata = [
    {
        "name": "Health Check",
        "description": "System status, broker readiness checks, and health monitoring endpoints.",
    },
    {
        "name": "Event Broker",
        "description": "Real-time session event dispatching and broadcasting across WebSocket connections.",
    },
    {
        "name": "Technical Defense",
        "description": "AI-driven technical defense question generation, real-time response grading, audio answer evaluation, and cumulative progress reporting.",
    },
    {
        "name": "Debrief & Evaluation",
        "description": "Post-defense debrief reports with STAR framework analysis, sub-scores, and coaching verdict.",
    },
    {
        "name": "Voice & TTS",
        "description": "AssemblyAI Voice Agent integration, bi-directional Speech-to-Speech agent, and text-to-speech audio synthesis.",
    },
]

app_description = """
# VivaGuard AI Backend Broker & Evaluation Engine

VivaGuard provides a real-time AI copilot, speech evaluation engine, and adaptive technical interview defense system.

## Key Capabilities:
- **AssemblyAI Realtime Speech-to-Text**: Stream 16 kHz audio via WebSockets for real-time transcription.
- **AssemblyAI Voice Agent (TTS & Speech-to-Speech)**: Convert AI coaching feedback and text into audio responses and stream bi-directional voice agent conversations over WebSockets (`/ws/speech-to-speech`).
- **Gemini / LLM Evaluation Engine**: Analyze answers against technical rubrics, filler words, and domain depth.
- **Session Event Broker**: Low-latency WebSocket event distribution across client connections.
- **Adaptive Difficulty Engine**: Dynamically adjust question difficulty tier (Junior, Mid-Level, Senior) based on candidate performance.

## Interactive API Documentation
- **Swagger UI**: [/docs](http://localhost:8000/docs)
- **ReDoc**: [/redoc](http://localhost:8000/redoc)
- **OpenAPI Schema (JSON)**: [/openapi.json](http://localhost:8000/openapi.json)
"""

app = FastAPI(
    title=settings.app_name,
    description=app_description,
    version="1.0.0",
    openapi_tags=tags_metadata,
    contact={
        "name": "VivaGuard Engineering",
        "url": "https://vivaguard.ai",
    },
    license_info={
        "name": "MIT License",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/api/v1/openapi.json", include_in_schema=False)
async def get_openapi_spec():
    """Returns the generated OpenAPI JSON specification."""
    return JSONResponse(content=app.openapi())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)

