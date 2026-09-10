import json
import re
import time
import urllib.request
import urllib.error
import uuid
from typing import Any

from fastapi import HTTPException

from app.config import settings

ASSEMBLYAI_LLM_GATEWAY_URL = "https://llm-gateway.assemblyai.com/v1/chat/completions"
DEFAULT_LLM_MODEL = "qwen3.5-4b-32k-fast"


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


def generate_test_questions(
    domain: str,
    format_name: str,
    question_count: int,
    difficulty_level: str = "Mid-Level",
    adaptive_mode: bool = True
) -> dict[str, Any]:
    """Generates structured technical interview or thesis defense questions using LLM Gateway.

    Prompts the AssemblyAI LLM Gateway to produce domain-specific questions matching specified format,
    difficulty level, and evaluation criteria.
    """
    session_id = f"test_{uuid.uuid4().hex[:8]}"

    prompt = (
        f"You are an expert technical interviewer and thesis defense examiner.\n"
        f"Generate exactly {min(question_count, 10)} high-quality interview or thesis defense questions for the domain: \"{domain}\" in \"{format_name}\" format.\n"
        f"Baseline difficulty tier: \"{difficulty_level}\" (Junior, Mid-Level, or Senior).\n"
        f"Adaptive progression enabled: {adaptive_mode}.\n"
        f"Tier Profile Guidelines:\n"
        f"  - Junior: Canonical definitions, foundational logic, basic syntax, guided scenarios.\n"
        f"  - Mid-Level: Real-world implementation mechanics, error handling, performance bottlenecks, production trade-offs.\n"
        f"  - Senior: Complex distributed edge cases, concurrency race states, CAP theorem, failovers, linearizability.\n\n"
        f"Respond ONLY with a valid JSON array of objects without markdown formatting or code blocks:\n"
        f"[\n"
        f"  {{\n"
        f"    \"question_text\": \"Short, precise interviewer prompt\",\n"
        f"    \"difficulty\": \"Junior\" or \"Mid-Level\" or \"Senior\",\n"
        f"    \"criteria\": [\"Criterion 1\", \"Criterion 2\", \"Criterion 3\"],\n"
        f"    \"ideal_summary\": \"1 short model answer sentence under 20 words\"\n"
        f"  }}\n"
        f"]\n"
    )

    llm_output = call_assemblyai_llm_gateway(prompt)
    if not llm_output:
        raise HTTPException(
            status_code=502,
            detail="Failed to generate questions via AssemblyAI LLM Gateway API. Ensure AssemblyAI API key is configured and valid."
        )

    try:
        match = re.search(r"\[[\s\S]*\]", llm_output)
        json_str = match.group(0) if match else llm_output.strip()
        parsed_questions = json.loads(json_str)

        if not isinstance(parsed_questions, list) or len(parsed_questions) == 0:
            raise ValueError("LLM returned empty or non-list question payload.")

        questions = []
        for i, q in enumerate(parsed_questions[:question_count]):
            q_diff = q.get("difficulty", difficulty_level)
            questions.append({
                "question_id": i + 1,
                "question_text": f"[{format_name}] {q.get('question_text', '')}",
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
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to parse AI-generated questions from AssemblyAI LLM Gateway: {str(exc)}"
        ) from exc


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
        f"  \"overall_score\": integer between 0 and 100,\n"
        f"  \"accuracy_rating\": \"Strong Answer\" or \"Partially Correct\" or \"Deficient for {difficulty_level} Tier\",\n"
        f"  \"strengths\": [\"Short strength 1\", \"Short strength 2\"],\n"
        f"  \"weaknesses\": [\"Short weakness 1\", \"Short weakness 2\"],\n"
        f"  \"actionable_improvements\": \"Short coaching tip.\",\n"
        f"  \"ideal_response_summary\": \"Short model answer summary.\"\n"
        f"}}\n"
    )

    llm_output = call_assemblyai_llm_gateway(prompt)
    if not llm_output:
        raise HTTPException(
            status_code=502,
            detail="Failed to evaluate response via AssemblyAI LLM Gateway API. Ensure AssemblyAI API key is configured and valid."
        )

    try:
        match = re.search(r"\{[\s\S]*\}", llm_output)
        json_str = match.group(0) if match else llm_output.strip()
        eval_dict = json.loads(json_str)

        if not isinstance(eval_dict, dict) or "overall_score" not in eval_dict:
            raise ValueError("LLM returned incomplete grading schema.")

        score = int(eval_dict.get("overall_score", 70))
        next_diff = get_next_adaptive_difficulty(difficulty_level, score, adaptive_mode)

        return {
            "question_id": question_id,
            "transcript": transcript,
            "overall_score": score,
            "accuracy_rating": str(eval_dict.get("accuracy_rating", "Partially Correct")),
            "strengths": [str(s)[:80] for s in eval_dict.get("strengths", ["Clear vocal articulation"])][:2],
            "weaknesses": [str(w)[:80] for w in eval_dict.get("weaknesses", ["Missed specific benchmark metrics"])][:2],
            "actionable_improvements": str(eval_dict.get("actionable_improvements", "Incorporate quantitative benchmark metrics."))[:120],
            "ideal_response_summary": str(eval_dict.get("ideal_response_summary", "State core methodology and architectural trade-offs."))[:120],
            "difficulty_evaluated": difficulty_level,
            "next_recommended_difficulty": next_diff
        }
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to parse AI evaluation from AssemblyAI LLM Gateway: {str(exc)}"
        ) from exc


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
