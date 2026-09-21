# VivaGuard AI Backend Engine

This project provides the production backend broker, real-time AI copilot, speech evaluation engine, and adaptive viva defense system for VivaGuard.

## Technology Stack

- **Framework**: FastAPI (Async Python web server)
- **Real-Time Streaming**: Python WebSockets (16 kHz PCM audio streaming & live copilot broadcast)
- **Speech-to-Text & Voice Synthesis**: AssemblyAI Realtime STT & AssemblyAI Voice Agent (TTS)
- **AI Evaluation Engine**: Gemini AI / LLM Gateway for real-time rubric grading & adaptive defense
- **Data Validation**: Pydantic v2 schemas & OpenAPI 3.1.0 specifications

## Project Structure

- `app/main.py` - FastAPI application entry point, CORS configuration, and OpenAPI metadata
- `app/api/` - Versioned API routers, dependencies (`deps.py`), and endpoint handlers (`v1/functions/`)
- `app/schemas/` - Pydantic request and response validation models (`debrief.py`, `test_interview.py`, `broker.py`, `tts.py`, `health.py`)
- `app/services/` - Core domain services (`broker.py`, `evaluator.py`, `test_simulator.py`, `assemblyai_stt.py`, `assemblyai_tts.py`)
- `export_openapi.py` - Exporter script to generate static `swagger.json`, `openapi.json`, `swagger.yaml`, `openapi.yaml` specs

## Local Development & Setup

1. **Activate virtual environment**:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure environment variables** in `.env`:
   ```env
   ASSEMBLYAI_API_KEY=your_assemblyai_api_key
   GEMINI_API_KEY=your_gemini_api_key
   ```
4. **Start the API server**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

## Interactive Swagger UI & OpenAPI Specs

FastAPI automatically serves interactive Swagger UI and ReDoc documentation with full schema validation:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc UI**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI Schema (JSON)**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

### Static OpenAPI / Swagger Specifications

Exported specification files are located at:
- [`swagger.json`](file:///c:/Users/ADMIN/Desktop/Code/HACKATHONS/vivaguard/swagger.json) / [`openapi.json`](file:///c:/Users/ADMIN/Desktop/Code/HACKATHONS/vivaguard/openapi.json)
- [`swagger.yaml`](file:///c:/Users/ADMIN/Desktop/Code/HACKATHONS/vivaguard/swagger.yaml) / [`openapi.yaml`](file:///c:/Users/ADMIN/Desktop/Code/HACKATHONS/vivaguard/openapi.yaml)

To re-export or refresh static OpenAPI specs at any time:
```bash
python export_openapi.py
```

## API Endpoints

### Health & Routing
- `GET /health` - Service health status check
- `POST /api/v1/route` - Dispatch broker event to active WebSocket session subscribers
- `WS /ws` - Main session event stream
- `WS /ws/copilot` - Live AI copilot event channel
- `WS /ws/audio` - Binary 16 kHz PCM audio stream for AssemblyAI Speech-to-Text
- `WS /ws/speech-to-speech` - Bi-directional Speech-to-Speech AssemblyAI Voice Agent WebSocket stream

### Technical Defense & Grading
- `POST /api/v1/interview/questions/generate` - Generate domain-tailored defense questions & rubrics
- `POST /api/v1/interview/grade` - Grade candidate text response with Gemini & calculate adaptive difficulty
- `POST /api/v1/interview/evaluate-audio` - Upload binary audio for AssemblyAI STT transcription & response grading
- `POST /api/v1/test-interview/evaluate-audio-base64` - Grade base64 encoded audio response with AssemblyAI Voice Agent spoken feedback
- `POST /api/v1/test-interview/cumulative-report` - Compile cumulative readiness report across answered questions
- `POST /api/debrief` - Generate post-defense STAR framework debrief report with sub-scores and verdict

### Voice & Speech Synthesis (TTS)
- `POST /api/text-to-speech` - Synthesize text into WAV audio or JSON response via AssemblyAI Voice API
- `POST /api/v1/tts` - Convert text to WAV audio or JSON base64 payload via AssemblyAI Voice Agent


