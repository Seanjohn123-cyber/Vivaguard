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
4. Start the API:
   `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`

## Endpoints

- `GET /health` - health check
- `WS /ws?session_id=<id>` - stream audio/transcription events
- `WS /ws/audio?session_id=<id>` - send 16 kHz PCM audio and receive transcript events
- `POST /api/v1/route` - enqueue a broker event

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
