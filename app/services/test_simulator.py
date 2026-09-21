import json
import re
import time
import urllib.request
import urllib.error
import uuid
from typing import Any

from fastapi import HTTPException

from app.core.config import settings

ASSEMBLYAI_LLM_GATEWAY_URL = "https://llm-gateway.assemblyai.com/v1/chat/completions"
DEFAULT_LLM_MODEL = "qwen3.5-4b-32k-fast"
GEMINI_JSON_MIME_TYPE = "application/json"


def call_gemini(prompt: str, retries: int = 2) -> str | None:
    """Call Gemini using a server-side API key and return the generated text."""
    if not settings.gemini_api_key:
        return None

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": GEMINI_JSON_MIME_TYPE},
    }
    endpoint = f"{settings.gemini_api_url.rstrip('/')}/{settings.gemini_model}:generateContent"
    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": settings.gemini_api_key,
    }

    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                candidates = data.get("candidates", [])
                parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
                text = "".join(str(part.get("text", "")) for part in parts)
                if text:
                    return text
        except urllib.error.HTTPError as http_err:
            if http_err.code == 429 and attempt < retries:
                time.sleep(2.0 * (attempt + 1))
                continue
            return None
        except (OSError, ValueError, KeyError, TypeError):
            if attempt < retries:
                time.sleep(1.0)
                continue
            return None

    return None


def call_assemblyai_llm_gateway(prompt: str, model: str = DEFAULT_LLM_MODEL, retries: int = 2) -> str | None:
    """Dispatches a prompt payload to the AssemblyAI LLM Gateway REST endpoint.

    Handles authorization, timeout, HTTP 429 rate limiting with backoff retries, and returns
    the generated text content or None if failed.
    """
    api_key = settings.assemblyai_api_key
    if not api_key:
        return None

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
    }
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json",
    }

    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(
                ASSEMBLYAI_LLM_GATEWAY_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                choices = data.get("choices", [])
                if choices and "message" in choices[0]:
                    return choices[0]["message"].get("content", "")
        except urllib.error.HTTPError as http_err:
            print(f"[AssemblyAI LLM Gateway HTTP {http_err.code}] {http_err} (Attempt {attempt+1}/{retries+1})")
            if http_err.code == 429 and attempt < retries:
                time.sleep(3.0 * (attempt + 1))
                continue
            return None
        except Exception as exc:
            print(f"[AssemblyAI LLM Gateway Error] {exc} (Attempt {attempt+1}/{retries+1})")
            if attempt < retries:
                time.sleep(2.0)
                continue
            return None

    return None


def call_llm(prompt: str) -> str | None:
    """Dispatches prompt to Gemini API first, falling back to AssemblyAI LLM Gateway if Gemini fails or is unconfigured."""
    text = call_gemini(prompt)
    if text:
        return text
    return call_assemblyai_llm_gateway(prompt)


def get_next_adaptive_difficulty(current_tier: str, score: int, adaptive_mode: bool = True) -> str:
    """Calculates the next difficulty tier (Junior, Mid-Level, Senior) based on response score.

    Prompts candidate up a tier if score >= 85, down if score < 50, or maintains current tier otherwise.
    Returns current tier unchanged if adaptive_mode is disabled.
    """
    tiers = ["Junior", "Mid-Level", "Senior"]
    normalized_tier = "Mid-Level"
    c_lower = current_tier.lower()
    if "junior" in c_lower or "entry" in c_lower or "easy" in c_lower:
        normalized_tier = "Junior"
    elif "senior" in c_lower or "lead" in c_lower or "expert" in c_lower or "hard" in c_lower:
        normalized_tier = "Senior"
    else:
        normalized_tier = "Mid-Level"

    if not adaptive_mode:
        return normalized_tier

    idx = tiers.index(normalized_tier)
    if score >= 85:
        next_idx = min(len(tiers) - 1, idx + 1)
    elif score < 50:
        next_idx = max(0, idx - 1)
    else:
        next_idx = idx

    return tiers[next_idx]


def parse_json_from_llm(raw_text: str) -> Any:
    """Robustly extracts and parses JSON payloads from LLM outputs."""
    if not raw_text or not raw_text.strip():
        raise ValueError("Empty response string")

    text = raw_text.strip()

    if "```" in text:
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text, flags=re.MULTILINE)
        text = re.sub(r"```$", "", text, flags=re.MULTILINE)
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    array_match = re.search(r"\[[\s\S]*\]", text)
    if array_match:
        cand = array_match.group(0)
        cand_clean = re.sub(r',\s*([\]}])', r'\1', cand)
        cand_clean = re.sub(r'"\s+or\s+"[^"]*"', '"', cand_clean)
        cand_clean = re.sub(r':\s*integer[^\n,}]*', ': 75', cand_clean, flags=re.IGNORECASE)
        try:
            return json.loads(cand_clean)
        except json.JSONDecodeError:
            pass

    obj_match = re.search(r"\{[\s\S]*\}", text)
    if obj_match:
        cand = obj_match.group(0)
        cand_clean = re.sub(r',\s*([\]}])', r'\1', cand)
        cand_clean = re.sub(r'"\s+or\s+"[^"]*"', '"', cand_clean)
        cand_clean = re.sub(r':\s*integer[^\n,}]*', ': 75', cand_clean, flags=re.IGNORECASE)
        try:
            return json.loads(cand_clean)
        except json.JSONDecodeError:
            pass

    cleaned = re.sub(r',\s*([\]}])', r'\1', text)
    cleaned = re.sub(r'"\s+or\s+"[^"]*"', '"', cleaned)
    cleaned = re.sub(r':\s*integer[^\n,}]*', ': 75', cleaned, flags=re.IGNORECASE)
    return json.loads(cleaned)


def generate_test_questions(
    domain: str,
    question_count: int = 2,
    difficulty_level: str = "Mid-Level",
    adaptive_mode: bool = True,
    format_name: str = "Technical Deep Dive"
) -> dict[str, Any]:
    """Generates structured technical interview or thesis defense questions using LLM Gateway.

    Prompts the LLM Gateway to produce domain-specific questions matching specified difficulty level and evaluation criteria.
    """
    session_id = f"test_{uuid.uuid4().hex[:8]}"

    prompt = (
        f"You are an expert technical interviewer and thesis defense examiner.\n"
        f"Generate exactly {min(question_count, 10)} high-quality technical interview or thesis defense questions for the domain: \"{domain}\".\n"
        f"Baseline difficulty tier: \"{difficulty_level}\" (Allowed values: Junior, Mid-Level, or Senior).\n"
        f"Adaptive progression enabled: {adaptive_mode}.\n"
        f"Tier Profile Guidelines:\n"
        f"  - Junior: Canonical definitions, foundational logic, basic syntax, guided scenarios.\n"
        f"  - Mid-Level: Real-world implementation mechanics, error handling, performance bottlenecks, production trade-offs.\n"
        f"  - Senior: Complex distributed edge cases, concurrency race states, CAP theorem, failovers, linearizability.\n\n"
        f"Respond ONLY with a valid JSON array of objects without markdown formatting or code blocks:\n"
        f"[\n"
        f"  {{\n"
        f"    \"question_text\": \"Short, precise interviewer prompt\",\n"
        f"    \"difficulty\": \"Junior\",\n"
        f"    \"criteria\": [\"Criterion 1\", \"Criterion 2\", \"Criterion 3\"],\n"
        f"    \"ideal_summary\": \"1 short model answer sentence under 20 words\"\n"
        f"  }}\n"
        f"]\n"
    )

    llm_output = call_llm(prompt)

    try:
        if not llm_output:
            raise ValueError("LLM returned empty output")
        parsed_questions = parse_json_from_llm(llm_output)
        if not isinstance(parsed_questions, list) or len(parsed_questions) == 0:
            raise ValueError("LLM returned non-list question payload.")
    except Exception:
        # Fallback question set if LLM output is empty or fails to parse
        parsed_questions = [
            {
                "question_text": f"Explain the core architectural principles and key implementation concepts of {domain}.",
                "difficulty": difficulty_level,
                "criteria": [f"Defines foundational concepts in {domain}", f"Explains primary implementation mechanics and trade-offs"]
            },
            {
                "question_text": f"How do you handle performance bottlenecks, state management, and error recovery in {domain}?",
                "difficulty": difficulty_level,
                "criteria": [f"Identifies performance bottlenecks in {domain}", f"Describes state management and error handling strategies"]
            }
        ]

    questions = []
    for i, q in enumerate(parsed_questions[:question_count]):
        q_diff = q.get("difficulty", difficulty_level)
        questions.append({
            "question_id": i + 1,
            "question_text": q.get('question_text', ''),
            "difficulty": q_diff,
            "difficulty_level": q_diff,
            "evaluation_criteria": q.get("criteria", [])
        })

    return {
        "session_id": session_id,
        "domain": domain,
        "format": format_name,
        "difficulty_level": difficulty_level,
        "adaptive_mode": adaptive_mode,
        "questions": questions
    }


def evaluate_question_response(
    question_id: int,
    question_text: str,
    criteria: list[str],
    transcript: str,
    difficulty_level: str = "Mid-Level",
    adaptive_mode: bool = True
) -> dict[str, Any]:
    """Grades a candidate's spoken response to a specific question using AssemblyAI LLM Gateway.

    Evaluates response against difficulty guidelines and target criteria, returning numerical scores, accuracy rating,
    bulleted strengths/weaknesses, actionable coaching tips, model answer summary, and next recommended difficulty.
    """
    text = transcript.strip()
    formatted_criteria = "\n".join([f"  {idx+1}. {c}" for idx, c in enumerate(criteria)]) if criteria else "  - Address core technical concepts and trade-offs."

    prompt = (
        f"You are a strict technical interviewer evaluating a candidate's spoken response under the \"{difficulty_level}\" tier.\n"
        f"Question: \"{question_text}\"\n"
        f"Evaluation Criteria Checkpoints:\n{formatted_criteria}\n"
        f"Candidate Spoken Response: \"{text or '(No response provided)'}\"\n\n"
        f"Grading Rigor Guidelines for \"{difficulty_level}\":\n"
        f"  - Junior: Focus on core conceptual accuracy. High tolerance for omitted edge cases.\n"
        f"  - Mid-Level: Enforce industry vocabulary. Penalize hand-waving or unquantified claims.\n"
        f"  - Senior: Zero tolerance for generalizations. Demand strict operational guarantees & quantitative proofs.\n\n"
        f"CRITICAL OUTPUT FORMAT RULES:\n"
        f"  1. Evaluate candidate response specifically against the Evaluation Criteria Checkpoints listed above.\n"
        f"  2. Keep all responses SHORT, PRECISE, DIRECT, AND CRISP.\n"
        f"  3. strengths: list of max 2 short bullet points (under 10 words per item).\n"
        f"  4. weaknesses: list of max 2 short bullet points (under 10 words per item).\n"
        f"  5. actionable_improvements: 1 concise coaching tip (under 15 words).\n"
        f"  6. ideal_response_summary: 1 concise model answer summary (under 18 words).\n\n"
        f"Respond ONLY with a valid JSON object without markdown formatting or code blocks with these exact fields:\n"
        f"{{\n"
        f"  \"overall_score\": 75,\n"
        f"  \"accuracy_rating\": \"Strong Answer\",\n"
        f"  \"strengths\": [\"Short strength 1\", \"Short strength 2\"],\n"
        f"  \"weaknesses\": [\"Short weakness 1\", \"Short weakness 2\"],\n"
        f"  \"actionable_improvements\": \"Short coaching tip.\",\n"
        f"  \"ideal_response_summary\": \"Short model answer summary.\"\n"
        f"}}\n"
    )

    llm_output = call_llm(prompt)

    try:
        if not llm_output:
            raise ValueError("LLM output is empty")
        eval_dict = parse_json_from_llm(llm_output)
        if not isinstance(eval_dict, dict) or "overall_score" not in eval_dict:
            raise ValueError("LLM returned incomplete grading schema.")
    except Exception:
        # Fallback dictionary if LLM output fails or is unconfigured/rate-limited
        eval_dict = {
            "overall_score": 75,
            "accuracy_rating": "Partially Correct",
            "strengths": ["Addressed core topic concepts"],
            "weaknesses": ["Could include specific technical mechanisms"],
            "actionable_improvements": "Incorporate specific technical mechanisms and quantitative figures.",
            "ideal_response_summary": "State core concepts, implementation mechanics, and quantitative trade-offs."
        }

    score = max(0, min(100, int(eval_dict.get("overall_score", 70))))
    next_diff = get_next_adaptive_difficulty(difficulty_level, score, adaptive_mode)

    return {
        "question_id": question_id,
        "transcript": transcript,
        "overall_score": score,
        "score": score,
        "accuracy_rating": str(eval_dict.get("accuracy_rating", "Partially Correct")),
        "strengths": [str(s)[:80] for s in eval_dict.get("strengths", ["Clear vocal articulation"])][:2],
        "weaknesses": [str(w)[:80] for w in eval_dict.get("weaknesses", ["Missed specific benchmark metrics"])][:2],
        "actionable_improvements": str(eval_dict.get("actionable_improvements", "Incorporate quantitative benchmark metrics."))[:120],
        "ideal_response_summary": str(eval_dict.get("ideal_response_summary", "State core methodology and architectural trade-offs."))[:120],
        "difficulty_evaluated": difficulty_level,
        "next_recommended_difficulty": next_diff
    }


def generate_cumulative_report(
    domain: str,
    format_name: str,
    evaluations: list[dict[str, Any]]
) -> dict[str, Any]:
    """Compiles a comprehensive interview readiness report across all completed question evaluations.

    Calculates aggregate overall score, readiness percentage, deduplicated cumulative strengths/weaknesses,
    and a targeted action plan.
    """
    if not evaluations:
        return {
            "domain": domain,
            "format": format_name,
            "overall_score": 75,
            "readiness_percentage": 75,
            "total_questions_answered": 0,
            "cumulative_strengths": ["Completed setup"],
            "persistent_weaknesses": ["No questions evaluated"],
            "action_plan": "Complete all practice questions for a full readiness report."
        }

    scores = [e.get("overall_score", 60) for e in evaluations]
    avg_score = int(sum(scores) / len(scores))
    readiness_pct = min(99, max(35, int(avg_score * 0.95 + 5)))

    all_strengths = []
    all_weaknesses = []
    for e in evaluations:
        all_strengths.extend(e.get("strengths", []))
        all_weaknesses.extend(e.get("weaknesses", []))

    # Deduplicate
    unique_strengths = list(dict.fromkeys(all_strengths))[:3]
    unique_weaknesses = list(dict.fromkeys(all_weaknesses))[:3]

    return {
        "domain": domain,
        "format": format_name,
        "overall_score": avg_score,
        "readiness_percentage": readiness_pct,
        "total_questions_answered": len(evaluations),
        "cumulative_strengths": unique_strengths or ["Clear articulation and steady delivery"],
        "persistent_weaknesses": unique_weaknesses or ["Lacked specific quantitative benchmark metrics"],
        "action_plan": "Practice stating concrete metrics within the first 15 seconds of your answer to maximize examiner confidence."
    }
