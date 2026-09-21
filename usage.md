# Vivaguard Backend Architectural Overview & API Usage Guide

This document provides a detailed breakdown of each file in the backend codebase, along with a complete API endpoint reference with sample request and response payloads.

---

## Directory Structure

```
backend/
├── app/                      # Main application package
│   ├── api/                  # API Layer (endpoints & versioning)
│   │   ├── v1/
│   │   │   ├── endpoints/    # Feature-specific API route handlers
│   │   │   │   ├── broker.py
│   │   │   │   ├── debrief.py
│   │   │   │   ├── health.py
│   │   │   │   ├── test_interview.py
│   │   │   │   └── websockets.py
│   │   │   └── api.py        # Aggregates v1 endpoints into APIRouter
│   │   └── deps.py           # Shared dependency singletons (broker, assemblyai)
│   │
│   ├── core/                 # Application configuration & settings
│   │   ├── __init__.py
│   │   └── config.py         # Pydantic BaseSettings environment parsing
│   │
│   ├── schemas/              # Pydantic data models & request/response validation
│   │   ├── __init__.py
│   │   ├── broker.py
│   │   ├── debrief.py
│   │   ├── health.py
│   │   └── test_interview.py
│   │
│   ├── services/             # Core business logic & external API clients
│   │   ├── __init__.py
│   │   ├── assemblyai_client.py
│   │   ├── assemblyai_stt.py
│   │   ├── broker.py
│   │   ├── evaluator.py
│   │   ├── rate_limiter.py
│   │   ├── session_manager.py
│   │   └── test_simulator.py
│   │
│   └── main.py               # FastAPI application entry point
│
├── tests/                    # Unit test suite
│   ├── test_gemini_grading.py
│   ├── test_rate_limiter.py
│   └── test_session_manager.py
│
├── .env                      # Local environment variables
└── usage.md                  # Comprehensive documentation (this file)
```

---

## Detailed File Breakdown

### 1. Application Entry Point & Core Configuration

#### [`app/main.py`](file:///c:/Users/ADMIN/Desktop/Code/HACKATHONS/vivaguard/backend/app/main.py)
* **Purpose**: Serves as the primary entry point for the FastAPI web server.
* **Responsibilities**:
  * Initializes the `FastAPI` app instance with title and metadata.
  * Configures `CORSMiddleware` to allow cross-origin requests from frontend clients.
  * Mounts the aggregated API router (`api_router` from `app.api.v1.api`).
  * Runs the server via `uvicorn.run()` when executed directly.

#### [`app/core/config.py`](file:///c:/Users/ADMIN/Desktop/Code/HACKATHONS/vivaguard/backend/app/core/config.py)
* **Purpose**: Manages application-wide settings and environment variable parsing.
* **Responsibilities**:
  * Uses Pydantic's `BaseSettings` to parse configuration from `.env` files and environment variables.
  * Configures server settings (`host`, `port`), rate limiting thresholds (`max_requests_per_minute`, `token_bucket_capacity`), and external service credentials (`assemblyai_api_key`, `gemini_api_key`, `gemini_api_url`).
  * Exposes global `settings` singleton instance.

#### [`app/api/deps.py`](file:///c:/Users/ADMIN/Desktop/Code/HACKATHONS/vivaguard/backend/app/api/deps.py)
* **Purpose**: Centralizes shared application dependencies and state singletons.
* **Responsibilities**:
  * Instantiates the global `broker` (`SessionBroker` initialized with configured `RateLimiter`).
  * Instantiates the global `assemblyai` (`AssemblyAIClient`).
  * Provides dependency injection access for route handlers in `app/api/v1/endpoints/`.

---

### 2. API Layer & Endpoint Handlers (`app/api/v1/`)

#### [`app/api/v1/api.py`](file:///c:/Users/ADMIN/Desktop/Code/HACKATHONS/vivaguard/backend/app/api/v1/api.py)
* **Purpose**: Aggregates all feature-specific routers into a single master `api_router`.
* **Responsibilities**: Includes `health_router`, `broker_router`, `debrief_router`, `test_interview_router`, and `websockets_router`.

#### [`app/api/v1/endpoints/health.py`](file:///c:/Users/ADMIN/Desktop/Code/HACKATHONS/vivaguard/backend/app/api/v1/endpoints/health.py)
* **Endpoint**: `GET /health`
* **Purpose**: Health check endpoint.
* **Responsibilities**: Returns `HealthResponse` confirming service status (`status: ok`) and availability of the broker service.

#### [`app/api/v1/endpoints/broker.py`](file:///c:/Users/ADMIN/Desktop/Code/HACKATHONS/vivaguard/backend/app/api/v1/endpoints/broker.py)
* **Endpoint**: `POST /api/v1/route`
* **Purpose**: HTTP route handler for event dispatching.
* **Responsibilities**: Receives a `BrokerEvent` payload, checks rate limits, and routes the event to all active WebSocket clients connected to the target `session_id`.

#### [`app/api/v1/endpoints/debrief.py`](file:///c:/Users/ADMIN/Desktop/Code/HACKATHONS/vivaguard/backend/app/api/v1/endpoints/debrief.py)
* **Endpoints**: `POST /api/v1/debrief`, `POST /api/debrief`
* **Purpose**: Post-session debrief generator.
* **Responsibilities**: Receives full session transcript and interaction history in a `DebriefRequest`, invokes `generate_debrief()`, and returns a detailed report featuring STAR framework analysis, confidence sub-scores, and key strengths/weaknesses.

#### [`app/api/v1/endpoints/test_interview.py`](file:///c:/Users/ADMIN/Desktop/Code/HACKATHONS/vivaguard/backend/app/api/v1/endpoints/test_interview.py)
* **Endpoints**:
  * `POST /api/v1/test-interview/generate` & `/api/v1/interview/questions/generate`
  * `POST /api/v1/test-interview/evaluate-question` & `/api/v1/interview/grade`
  * `POST /api/v1/test-interview/evaluate-audio` & `/api/v1/interview/evaluate-audio`
  * `POST /api/v1/test-interview/evaluate-audio-base64`
  * `POST /api/v1/test-interview/cumulative-report`
* **Purpose**: Interview simulator endpoints (Mode A).
* **Responsibilities**:
  * `generate_test_interview`: Generates structured practice questions tailored to a specific domain, format, and baseline difficulty.
  * `evaluate_test_question`: Grades text transcript against criteria, returning scores, strengths/weaknesses, and next recommended difficulty tier (Junior, Mid-Level, Senior).
  * `evaluate_test_audio`: Accepts multipart audio file upload (webm/mp3/wav/m4a), transcribes audio via AssemblyAI STT, and grades the candidate response.
  * `evaluate_test_audio_base64`: Accepts base64 encoded audio in JSON payload, transcribes via AssemblyAI STT, and grades the candidate response.
  * `cumulative_test_report`: Compiles an overall readiness score and cumulative action plan across all answered questions.

#### [`app/api/v1/endpoints/websockets.py`](file:///c:/Users/ADMIN/Desktop/Code/HACKATHONS/vivaguard/backend/app/api/v1/endpoints/websockets.py)
* **Endpoints**:
  * `WebSocket /ws`: Generic session-based messaging and broadcasting.
  * `WebSocket /ws/copilot`: Full-duplex live copilot session accepting audio streams/JSON frames, piping audio to AssemblyAI, evaluating transcript real-time, and returning signal feedback (GREEN/AMBER/RED).
  * `WebSocket /ws/audio`: Direct raw PCM audio streaming to AssemblyAI real-time Speech-to-Text engine.

---

### 3. Data Schemas & Validation (`app/schemas/`)

#### [`app/schemas/health.py`](file:///c:/Users/ADMIN/Desktop/Code/HACKATHONS/vivaguard/backend/app/schemas/health.py)
* **Model**: `HealthResponse`
* **Fields**: `status`, `service`.

#### [`app/schemas/broker.py`](file:///c:/Users/ADMIN/Desktop/Code/HACKATHONS/vivaguard/backend/app/schemas/broker.py)
* **Models**:
  * `BrokerEvent`: `event_id`, `session_id`, `type` (audio, transcript, tool_call, status, error), `payload`.
  * `BrokerResponse`: `ok`, `message`, `event_id`.

#### [`app/schemas/debrief.py`](file:///c:/Users/ADMIN/Desktop/Code/HACKATHONS/vivaguard/backend/app/schemas/debrief.py)
* **Model**: `DebriefRequest`
* **Fields**: `ground_truth`, `target_question`, `full_transcript`, `history`.

#### [`app/schemas/test_interview.py`](file:///c:/Users/ADMIN/Desktop/Code/HACKATHONS/vivaguard/backend/app/schemas/test_interview.py)
* **Models**:
  * `TestGenerateRequest`: Domain, interview format, question count, baseline difficulty, adaptive mode.
  * `GeneratedQuestionSchema`: Question ID, question text, difficulty tier, criteria list.
  * `TestGenerateResponse`: Session ID, domain, format, questions list.
  * `QuestionEvaluateRequest`: Session ID, question text, evaluation criteria, transcript, difficulty level, adaptive mode.
  * `AudioEvaluateRequest`: Session ID, question text, evaluation criteria, base64 audio payload, difficulty level, adaptive mode.
  * `QuestionEvaluateResponse`: Score, accuracy rating, strengths, weaknesses, actionable improvements, ideal response summary, next recommended difficulty.
  * `TestCumulativeReportRequest`: Domain, format, evaluations list.

---

### 4. Business Services Layer (`app/services/`)

#### [`app/services/assemblyai_client.py`](file:///c:/Users/ADMIN/Desktop/Code/HACKATHONS/vivaguard/backend/app/services/assemblyai_client.py)
* **Class**: `AssemblyAIClient`
* **Responsibilities**:
  * Manages asynchronous WebSocket connection to AssemblyAI's real-time STT engine (`wss://streaming.assemblyai.com/v3/ws`).
  * Normalizes raw STT transcript frames into standardized transcript payloads.
  * Handles bidirectional streaming sessions (`stream_session`) by concurrently sending audio chunks from a queue and receiving transcript callbacks.

#### [`app/services/assemblyai_stt.py`](file:///c:/Users/ADMIN/Desktop/Code/HACKATHONS/vivaguard/backend/app/services/assemblyai_stt.py)
* **Key Functions & Classes**:
  * `transcribe_audio_file()`: Uploads recorded audio bytes (webm, mp3, wav, m4a) to AssemblyAI Speech-to-Text API and returns transcript text.
  * `LiveTranscriptionSession`: Wraps AssemblyAI's v3 streaming client (`StreamingClient`) for real-time PCM16 audio transcription over WebSockets.

#### [`app/services/broker.py`](file:///c:/Users/ADMIN/Desktop/Code/HACKATHONS/vivaguard/backend/app/services/broker.py)
* **Class**: `SessionBroker`
* **Responsibilities**:
  * Thread-safe registry mapping `session_id` keys to sets of active WebSocket client connections.
  * Registers and unregisters client connections upon connect/disconnect.
  * Broadcasts text or JSON payloads to all connected peers in a session.
  * Enforces rate limiting per session via `route_event()`.

#### [`app/services/evaluator.py`](file:///c:/Users/ADMIN/Desktop/Code/HACKATHONS/vivaguard/backend/app/services/evaluator.py)
* **Key Functions**:
  * `extract_filler_words()`: Regex scanner counting filler words (`um`, `uh`, `like`, `basically`).
  * `extract_technical_keywords()`: Matches transcript against domain terms (`architecture`, `latency`, `concurrency`, `trade-off`).
  * `evaluate_transcript()`: Analyzes live transcript in real time, calculating traffic light signal (GREEN/AMBER/RED), dodging detection, coaching nudges, and examiner sentiment.
  * `generate_debrief()`: Processes complete session history to calculate overall defense score, STAR framework answer breakdown, strengths/weaknesses, and final defense verdict.

#### [`app/services/rate_limiter.py`](file:///c:/Users/ADMIN/Desktop/Code/HACKATHONS/vivaguard/backend/app/services/rate_limiter.py)
* **Classes**: `TokenBucket`, `RateLimiter`
* **Responsibilities**:
  * `TokenBucket`: Refills tokens over time and consumes tokens per request.
  * `RateLimiter`: Dual-layer rate limiter enforcing sliding window request limits per minute and token bucket burst capacity per `session_id`.

#### [`app/services/session_manager.py`](file:///c:/Users/ADMIN/Desktop/Code/HACKATHONS/vivaguard/backend/app/services/session_manager.py)
* **Classes**: `SessionRecord`, `SessionManager`
* **Responsibilities**:
  * Tracks operational state (`active`, `completed`), metadata, and cumulative token usage counters (`total_input_tokens`, `total_output_tokens`).

#### [`app/services/test_simulator.py`](file:///c:/Users/ADMIN/Desktop/Code/HACKATHONS/vivaguard/backend/app/services/test_simulator.py)
* **Key Functions**:
  * `call_gemini()`: Dispatches prompt payloads to Google Gemini API using configured server API key.
  * `call_assemblyai_llm_gateway()`: Fallback REST client for LLM Gateway completions.
  * `get_next_adaptive_difficulty()`: Calculates adaptive progression between Junior, Mid-Level, and Senior difficulty tiers.
  * `generate_test_questions()`: Prompts Gemini to generate domain-specific interview questions with criteria.
  * `evaluate_question_response()`: Evaluates candidate spoken answers against criteria and returns numerical scores and feedback.
  * `generate_cumulative_report()`: Compiles aggregate scores and cumulative action plans across answered questions.

---

## API Reference & Usage Examples

### 1. Health Check (`GET /health`)

Check service availability and status.

* **Request**:
  ```http
  GET /health HTTP/1.1
  Host: localhost:8000
  ```
* **Response (200 OK)**:
  ```json
  {
    "status": "ok",
    "service": "vivaguard-broker"
  }
  ```

---

### 2. Route Session Event (`POST /api/v1/route`)

Routes an incoming event payload to all active WebSocket clients registered under a `session_id`.

* **Request**:
  ```http
  POST /api/v1/route HTTP/1.1
  Host: localhost:8000
  Content-Type: application/json

  {
    "event_id": "evt_987654",
    "session_id": "session_abc123",
    "type": "transcript",
    "payload": {
      "text": "Candidate stated: 'We used std::atomic for reference counting.'",
      "final": true
    }
  }
  ```
* **Response (200 OK)**:
  ```json
  {
    "ok": true,
    "message": "Event routed",
    "event_id": "evt_987654"
  }
  ```
* **Response (429 Rate Limit Exceeded)**:
  ```json
  {
    "detail": "Rate limit exceeded for session session_abc123"
  }
  ```

---

### 3. Generate Session Debrief (`POST /api/v1/debrief`)

Generates a post-interview defense report featuring STAR framework analysis, sub-scores, strengths, weaknesses, and a final verdict.

* **Request**:
  ```http
  POST /api/v1/debrief HTTP/1.1
  Host: localhost:8000
  Content-Type: application/json

  {
    "ground_truth": "Our shared cache uses std::atomic variables for reference counting and bucket locks to prevent race conditions under high concurrency.",
    "target_question": "How did you handle race conditions in your shared cache implementation?",
    "full_transcript": "To handle race conditions, we used std::atomic variables for reference counting and fine-grained mutex locks on hash buckets to cut contention by 80%.",
    "history": [
      {
        "timestamp": 20,
        "signal": "GREEN",
        "filler_words_count": 0,
        "technical_keyword_count": 3,
        "is_dodging": false,
        "nudge": "Strong answer!",
        "reasoning": "Detected 3 domain terms."
      }
    ]
  }
  ```
* **Response (200 OK)**:
  ```json
  {
    "overall_score": 88,
    "clarity_score": 95,
    "confidence_score": 90,
    "technical_depth_score": 82,
    "green_percentage": 100,
    "amber_percentage": 0,
    "red_percentage": 0,
    "total_fillers": 0,
    "total_technical_keywords": 3,
    "dodged_questions_count": 0,
    "total_duration_sec": 20,
    "ideal_star_answer": {
      "Situation": "High-stakes response to target topic: 'How did you handle race conditions in your shared cache implementation?'",
      "Task": "Defend technical & domain decisions against ground truth parameters.",
      "Action": "Delivered structured technical defense, articulating methodology and trade-offs clearly.",
      "Result": "Achieved 88/100 overall defense score with 100% high-confidence technical alignment."
    },
    "key_strengths": [
      "Articulated primary thesis and technical concepts with clear terminology",
      "Demonstrated good technical depth across 3 domain keyword mentions",
      "Maintained strong composure and clear articulation during core interrogation"
    ],
    "key_weaknesses": [
      "Minor pause delays before addressing complex follow-up questions"
    ],
    "suggested_followup_questions": [
      "What specific metric proves your architecture outperforms standard industry alternatives?",
      "How would your approach handle a failure during peak concurrent load?",
      "If budget or computational resources were cut by 50%, what trade-offs would you make?"
    ],
    "critical_shifts": [],
    "defense_verdict": "Strong Technical Defense"
  }
  ```

---

### 4. Generate Interview Questions (`POST /api/v1/test-interview/generate`)

Generates structured technical interview or thesis defense questions tailored to domain, format, and baseline difficulty.

* **Request**:
  ```http
  POST /api/v1/test-interview/generate HTTP/1.1
  Host: localhost:8000
  Content-Type: application/json

  {
    "domain": "Html",
    "question_count": 2,
    "difficulty_level": "junior"
  }
  ```
* **Response (200 OK)**:
  ```json
  {
    "session_id": "test_f6701d30",
    "domain": "Html",
    "format": "Technical Deep Dive",
    "difficulty_level": "junior",
    "adaptive_mode": true,
    "questions": [
      {
        "question_id": 1,
        "question_text": "What is the role of the Document Object Model (DOM), and how does the difference between `forEach` and `length` affect decision making?",
        "difficulty": "Junior",
        "difficulty_level": "Junior",
        "evaluation_criteria": [
          "Define DOM as an object representation of HTML.",
          "Explain `length` returns an integer while `forEach` iterates.",
          "Identify `forEach` for callbacks and `length` for index access."
        ]
      },
      {
        "question_id": 2,
        "question_text": "In a real-world form, why do you prevent default submission on the submit event if validation fails?",
        "difficulty": "Junior",
        "difficulty_level": "Junior",
        "evaluation_criteria": [
          "Describes preventing browser native submit behavior",
          "Explains custom validation logic before submission"
        ]
      }
    ]
  }
  ```

---

### 5. Grade Spoken Response (`POST /api/v1/test-interview/evaluate-question`)

Grades a candidate's spoken answer against criteria checkpoints under the target difficulty tier.

* **Request**:
  ```http
  POST /api/v1/test-interview/evaluate-question HTTP/1.1
  Host: localhost:8000
  Content-Type: application/json

  {
    "session_id": "test_e5a2b1f8",
    "question_id": 1,
    "question_text": "How did you handle race conditions in your shared cache implementation?",
    "evaluation_criteria": [
      "Mentions atomic variables or bucket-level locks",
      "Explains deadlock prevention strategy",
      "Provides a concrete trade-off example"
    ],
    "transcript": "To handle race conditions in our shared memory cache, we used std::atomic variables for reference counting and fine-grained mutex locks on individual hash buckets. To prevent deadlocks, we established a strict lock acquisition hierarchy.",
    "difficulty_level": "Senior",
    "adaptive_mode": true
  }
  ```
* **Response (200 OK)**:
  ```json
  {
    "question_id": 1,
    "transcript": "To handle race conditions in our shared memory cache, we used std::atomic variables for reference counting and fine-grained mutex locks on individual hash buckets. To prevent deadlocks, we established a strict lock acquisition hierarchy.",
    "overall_score": 92,
    "score": 92,
    "accuracy_rating": "Strong Answer",
    "strengths": [
      "Explains atomic reference counting",
      "Outlines strict locking hierarchy"
    ],
    "weaknesses": [
      "Omitted explicit latency metrics"
    ],
    "actionable_improvements": "State specific latency figures and contention drop percentage under peak load.",
    "ideal_response_summary": "Use std::atomic variables for reference counting and fine-grained mutexes per bucket with a lock hierarchy.",
    "difficulty_evaluated": "Senior",
    "next_recommended_difficulty": "Senior"
  }
  ```

---

### 5B. Grade Spoken Audio Answer via AssemblyAI (`POST /api/v1/test-interview/evaluate-audio`)

Transcribes a candidate's spoken audio recording via AssemblyAI Speech-to-Text API (`universal-3-5-pro`) and grades the transcript against criteria checkpoints.

* **Request**:
  ```http
  POST /api/v1/test-interview/evaluate-audio HTTP/1.1
  Host: localhost:8000
  Content-Type: multipart/form-data; boundary=----WebKitFormBoundary7MA4YWxkTrZu0gW

  ------WebKitFormBoundary7MA4YWxkTrZu0gW
  Content-Disposition: form-data; name="audio_file"; filename="answer.webm"
  Content-Type: audio/webm

  <binary audio content>
  ------WebKitFormBoundary7MA4YWxkTrZu0gW
  Content-Disposition: form-data; name="question_id"

  1
  ------WebKitFormBoundary7MA4YWxkTrZu0gW
  Content-Disposition: form-data; name="question_text"

  What is the role of the Document Object Model (DOM), and how does the difference between forEach and length affect decision making?
  ------WebKitFormBoundary7MA4YWxkTrZu0gW
  Content-Disposition: form-data; name="evaluation_criteria"

  ["Define DOM as an object representation of HTML.", "Explain length returns an integer while forEach iterates.", "Identify forEach for callbacks and length for index access."]
  ------WebKitFormBoundary7MA4YWxkTrZu0gW
  Content-Disposition: form-data; name="difficulty_level"

  junior
  ------WebKitFormBoundary7MA4YWxkTrZu0gW
  Content-Disposition: form-data; name="adaptive_mode"

  true
  ------WebKitFormBoundary7MA4YWxkTrZu0gW--
  ```

* **Response (200 OK)**:
  ```json
  {
    "question_id": 1,
    "transcript": "The DOM is an object representation of the HTML document structure. Length gives element count as an integer while forEach iterates through callbacks.",
    "overall_score": 88,
    "score": 88,
    "accuracy_rating": "Strong Answer",
    "strengths": [
      "Defined DOM as object representation of HTML",
      "Clearly contrasted length integer vs forEach callback iteration"
    ],
    "weaknesses": [
      "Could specify performance implications of index access"
    ],
    "actionable_improvements": "Mention index access vs callback iteration performance in high-frequency loops.",
    "ideal_response_summary": "The DOM represents HTML elements as tree objects; length enables index access while forEach executes callbacks per node.",
    "difficulty_evaluated": "Junior",
    "next_recommended_difficulty": "Mid-Level"
  }
  ```

---

### 5C. Grade Base64 Encoded Audio Answer (`POST /api/v1/test-interview/evaluate-audio-base64`)

* **Request**:
  ```http
  POST /api/v1/test-interview/evaluate-audio-base64 HTTP/1.1
  Host: localhost:8000
  Content-Type: application/json

  {
    "question_id": 1,
    "question_text": "What is the role of the Document Object Model (DOM)...",
    "evaluation_criteria": [
      "Define DOM as an object representation of HTML."
    ],
    "audio_base64": "GkXfo59ChoEBQveBAULygQRC84EIQoKEd2VibUKG...",
    "difficulty_level": "junior",
    "adaptive_mode": true
  }
  ```

---

### 6. Cumulative Readiness Report (`POST /api/v1/test-interview/cumulative-report`)

Compiles an overall readiness score and cumulative action plan across all answered practice questions.

* **Request**:
  ```http
  POST /api/v1/test-interview/cumulative-report HTTP/1.1
  Host: localhost:8000
  Content-Type: application/json

  {
    "domain": "Distributed Systems & Shared Caches",
    "format": "Technical Deep Dive",
    "evaluations": [
      {
        "question_id": 1,
        "overall_score": 92,
        "strengths": ["Explains atomic reference counting"],
        "weaknesses": ["Omitted explicit latency metrics"]
      }
    ]
  }
  ```
* **Response (200 OK)**:
  ```json
  {
    "domain": "Distributed Systems & Shared Caches",
    "format": "Technical Deep Dive",
    "overall_score": 92,
    "readiness_percentage": 92,
    "total_questions_answered": 1,
    "cumulative_strengths": [
      "Explains atomic reference counting"
    ],
    "persistent_weaknesses": [
      "Omitted explicit latency metrics"
    ],
    "action_plan": "Practice stating concrete metrics within the first 15 seconds of your answer to maximize examiner confidence."
  }
  ```

---

### 7. Real-Time WebSockets Interface

#### Generic Session Broadcast (`ws://localhost:8000/ws?session_id=session_abc123`)
* Accepts JSON frames from client and broadcasts payload to all connected session peers.
* Enforces rate limiting per `session_id`.

#### Live Copilot Evaluator (`ws://localhost:8000/ws/copilot?session_id=session_abc123`)
1. **Client Setup Frame**:
   ```json
   {
     "type": "setup",
     "ground_truth": "Our cache uses std::atomic variables and bucket mutex locks.",
     "target_question": "How did you handle race conditions in your shared cache?"
   }
   ```
2. **Server Ack**:
   ```json
   {
     "type": "setup_ack",
     "stt_engine": "AssemblyAI Realtime STT"
   }
   ```
3. **Client Audio Stream / Transcript Frame**:
   Send binary PCM audio chunks or text frame:
   ```json
   {
     "type": "transcript",
     "text": "We used atomic variables and fine-grained mutexes."
   }
   ```
4. **Server Live Evaluation Frame**:
   ```json
   {
     "type": "evaluation",
     "signal": "GREEN",
     "nudge": "Strong answer! You are providing concrete technical depth and clear reasoning.",
     "reasoning": "Detected 2 domain terms (mutex, atomic) and strong question alignment.",
     "suggested_pivot": "Quantitative Impact",
     "latency_ms": 135,
     "filler_words_count": 0,
     "technical_keyword_count": 2,
     "is_dodging": false
   }
   ```

#### Raw Audio Stream (`ws://localhost:8000/ws/audio?session_id=session_abc123`)
* Streams binary PCM audio chunks directly to AssemblyAI real-time Speech-to-Text engine.
* Returns normalized STT JSON transcript frames.
