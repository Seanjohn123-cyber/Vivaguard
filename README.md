# Vivaguard Backend Broker

This project provides the backend broker for the live voice/AI pipeline shown in the architecture diagram.

## Stack

- FastAPI
- Python WebSockets
- Pydantic models
- Async broker for session routing

## Project structure

- `app/main.py` - FastAPI application and WebSocket entry point
- `app/broker.py` - session and message broker logic
- `app/config.py` - environment settings
- `app/schemas.py` - request/response schemas

## Local development

1. Create and activate a virtual environment
2. Install dependencies:
   `pip install -r requirements.txt`
3. Create a `.env` file with your local secrets, for example:
   `ASSEMBLYAI_API_KEY=your_key_here`
   `GEMINI_API_KEY=your_key_here`
4. Start the API:
   `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`

## Endpoints

- `GET /health` - health check
- `WS /ws?session_id=<id>` - stream audio/transcription events
- `WS /ws/audio?session_id=<id>` - send 16 kHz PCM audio and receive transcript events
- `POST /api/v1/route` - enqueue a broker event
- `POST /api/v1/interview/questions/generate` - generate Gemini-backed questions and rubrics
- `POST /api/v1/interview/grade` - grade a transcript with Gemini and calculate next difficulty

### Grading request

Send the transcript captured by the frontend to `/api/v1/interview/grade`:

```json
{
  "session_id": "session-123",
  "question_id": 1,
  "question_text": "How would you prevent stale reads during a network partition?",
  "evaluation_criteria": [
    "Addresses quorum reads",
    "Explains consistency trade-offs"
  ],
  "transcript": "I would use quorum reads and reject writes without a majority.",
  "difficulty_level": "Senior",
  "adaptive_mode": true
}
```

The HTTP response contains `score` and `overall_score` (0-100), strengths, weaknesses,
actionable improvements, and `next_recommended_difficulty`. When `session_id` is provided,
the same response is broadcast to `/ws?session_id=session-123` as a `grade_result` event.

### Live audio protocol

Connect to `/ws/audio` with a unique session id. Send raw 16 kHz PCM audio as binary WebSocket messages. Transcript responses have this shape:

```json
{
  "type": "transcript",
  "final": true,
  "text": "hello",
  "confidence": 0.98,
  "words": []
}
```

Send `{"type":"stop"}` as a text message to terminate the AssemblyAI stream cleanly.
