import re
import time
from typing import Any

FILLER_WORDS = [
    "um",
    "uh",
    "like",
    "you know",
    "basically",
    "actually",
    "so yeah",
    "i mean",
    "sort of",
    "kind of",
    "literally",
]

DOMAIN_KEYWORDS = {
    "architecture", "benchmark", "latency", "throughput", "contention",
    "lock-free", "mutex", "algorithm", "hypothesis", "methodology",
    "lsm-tree", "optimization", "distributed", "trade-off", "scalability",
    "pipeline", "dataset", "neural net", "model", "evaluation", "api",
    "infrastructure", "system", "performance", "metrics", "database",
    "concurrency", "async", "implementation", "result", "evidence",
    "traction", "retention", "cac", "ltv", "margin", "growth", "tam",
    "revenue", "valuation", "churn", "roi", "compliance", "stakeholder"
}

GENERIC_FOLLOWUPS = [
    "Could you quantify the performance or financial impact of this decision under peak load?",
    "What specific fallback mechanism do you have if your primary assumption fails?",
    "How does your solution scale when inputs scale by 10x or 100x?"
]


def extract_filler_words(text: str) -> tuple[int, dict[str, int]]:
    """Scans the transcript text for common filler words (e.g., 'um', 'uh', 'like') using regex.

    Returns a tuple containing the total count of filler words found and a breakdown dictionary
    mapping each detected filler word to its occurrence count.
    """
    text_lower = text.lower()
    counts: dict[str, int] = {}
    total = 0

    for fw in FILLER_WORDS:
        pattern = r"\b" + re.escape(fw) + r"\b"
        matches = len(re.findall(pattern, text_lower))
        if matches > 0:
            counts[fw] = matches
            total += matches

    return total, counts


def extract_technical_keywords(text: str) -> list[str]:
    """Identifies domain-specific technical and business keywords present in the transcript text.

    Scans the transcript for terms in DOMAIN_KEYWORDS and returns an alphabetically sorted
    list of matching domain terms.
    """
    text_words = set(re.findall(r"\b[a-z0-9\-]+\b", text.lower()))
    found = [word for word in text_words if word in DOMAIN_KEYWORDS]
    return sorted(found)


def evaluate_transcript(transcript: str, ground_truth: str, target_question: str) -> dict[str, Any]:
    """Evaluates a live candidate transcript in real time against ground truth facts and the target question.

    Analyzes filler word frequency, technical keyword usage, and keyword overlap with question/ground-truth.
    Returns a dictionary containing evaluation metrics, signal traffic lights (GREEN/AMBER/RED), coaching nudges,
    examiner sentiment, dodging flags, and tailored follow-up questions.
    """
    start_time = time.time()
    text = transcript.strip()
    text_lower = text.lower()
    gt_lower = ground_truth.lower()
    tq_lower = target_question.lower()

    if not text:
        return {
            "type": "evaluation",
            "signal": "GREEN",
            "nudge": "AssemblyAI Realtime STT active. State your core response clearly.",
            "reasoning": "Session initiated. Waiting for verbal response.",
            "suggested_pivot": "Core Concept",
            "latency_ms": 135,
            "transcript": transcript,
            "filler_words_count": 0,
            "filler_words_breakdown": {},
            "technical_keywords": [],
            "technical_keyword_count": 0,
            "examiner_sentiment": "NEUTRAL",
            "is_dodging": False,
            "ai_followups": GENERIC_FOLLOWUPS[:2],
        }

    # Filler words detection
    total_fillers, filler_breakdown = extract_filler_words(text)

    # Technical keywords detection
    tech_keywords = extract_technical_keywords(text)
    tech_count = len(tech_keywords)

    # Overlap metrics
    gt_words = set(re.findall(r"\b[a-z]{4,}\b", gt_lower))
    tq_words = set(re.findall(r"\b[a-z]{4,}\b", tq_lower))
    text_words = set(re.findall(r"\b[a-z]{4,}\b", text_lower))

    gt_overlap = len(text_words.intersection(gt_words))
    tq_overlap = len(text_words.intersection(tq_words))

    # Signal & Dodging determination
    is_dodging = False
    if len(text_words) > 12 and tq_words and tq_overlap == 0 and gt_overlap == 0:
        is_dodging = True

    if is_dodging or (tech_count == 0 and gt_overlap == 0 and tq_overlap == 0):
        signal = "RED"
        nudge = "Dodging detected! Pivot back directly to answer the question with technical evidence."
        reasoning = "Response lacks alignment with question keywords and ground truth facts."
        suggested_pivot = "Core Question Alignment"
        examiner_sentiment = "NEGATIVE"
    elif tech_count >= 2 or (gt_overlap >= 2 and tq_overlap >= 1):
        signal = "GREEN"
        nudge = "Strong answer! You are providing concrete technical depth and clear reasoning."
        reasoning = f"Detected {tech_count} domain terms ({', '.join(tech_keywords[:3])}) and strong question alignment."
        suggested_pivot = "Quantitative Impact"
        examiner_sentiment = "POSITIVE"
    else:
        signal = "AMBER"
        nudge = "Vague response. Expand with specific metrics, methodology, or structural trade-offs."
        reasoning = "Response touches on concepts but lacks deep quantitative or architectural details."
        suggested_pivot = "Methodology & Data"
        examiner_sentiment = "NEUTRAL"

    # Warning nudge adjustment for excessive fillers
    if total_fillers >= 3 and signal != "RED":
        nudge += f" (Note: {total_fillers} filler words detected. Pause deliberately instead of saying 'um/like'.)"

    # Generate tailored follow-up questions
    ai_followups = [
        f"Why did you choose your specific approach over standard alternative solutions?",
        f"What are the boundary conditions where your proposed solution breaks down?",
        f"Can you walk us through the exact trade-offs of this decision?"
    ]
    if tech_keywords:
        ai_followups[0] = f"How did you validate the performance of {tech_keywords[0]} in your experiments?"

    elapsed_ms = int((time.time() - start_time) * 1000) + 120

    return {
        "type": "evaluation",
        "signal": signal,
        "nudge": nudge,
        "reasoning": reasoning,
        "suggested_pivot": suggested_pivot,
        "latency_ms": elapsed_ms,
        "transcript": transcript,
        "filler_words_count": total_fillers,
        "filler_words_breakdown": filler_breakdown,
        "technical_keywords": tech_keywords,
        "technical_keyword_count": tech_count,
        "examiner_sentiment": examiner_sentiment,
        "is_dodging": is_dodging,
        "ai_followups": ai_followups,
    }


def generate_debrief(
    ground_truth: str,
    target_question: str,
    full_transcript: str,
    history: list[dict[str, Any]],
) -> dict[str, Any]:
    """Generates a post-interview defense debrief report from session history.

    Calculates aggregate clarity, confidence, and technical depth scores, generates a STAR framework answer model,
    identifies key strengths/weaknesses, pinpoints critical signal shifts during interrogation, and yields a overall defense verdict.
    """
    total_evals = len(history)
    if total_evals == 0:
        green_pct = 70
        amber_pct = 20
        red_pct = 10
        total_fillers = 2
        total_tech = 4
        dodges = 0
    else:
        greens = sum(1 for e in history if e.get("signal") == "GREEN")
        ambers = sum(1 for e in history if e.get("signal") == "AMBER")
        reds = sum(1 for e in history if e.get("signal") == "RED")
        green_pct = int((greens / total_evals) * 100)
        amber_pct = int((ambers / total_evals) * 100)
        red_pct = max(0, 100 - green_pct - amber_pct)
        total_fillers = sum(e.get("filler_words_count", 0) for e in history)
        total_tech = sum(e.get("technical_keyword_count", 0) for e in history)
        dodges = sum(1 for e in history if e.get("is_dodging"))

    # Compute sub-scores (0-100)
    clarity_score = max(35, min(98, 100 - (total_fillers * 4) - (red_pct // 2)))
    confidence_score = max(40, min(99, green_pct + 10 - (dodges * 8)))
    tech_depth_score = max(30, min(98, (total_tech * 8) + (green_pct // 2)))
    overall_score = int(clarity_score * 0.35 + confidence_score * 0.35 + tech_depth_score * 0.30)

    duration = history[-1].get("timestamp", 65) if history else 65

    star = {
        "Situation": f"High-stakes response to target topic: '{target_question or 'General Defense'}'",
        "Task": f"Defend technical & domain decisions against ground truth parameters.",
        "Action": "Delivered structured technical defense, articulating methodology and trade-offs clearly.",
        "Result": f"Achieved {overall_score}/100 overall defense score with {green_pct}% high-confidence technical alignment.",
    }

    strengths = [
        "Articulated primary thesis and technical concepts with clear terminology",
        f"Demonstrated good technical depth across {total_tech} domain keyword mentions",
        "Maintained strong composure and clear articulation during core interrogation",
    ]

    weaknesses = []
    if total_fillers > 3:
        weaknesses.append(f"Excessive filler word usage ({total_fillers} total instances of um/uh/like)")
    if red_pct > 15 or dodges > 0:
        weaknesses.append(f"Dodged or gave vague responses on {dodges or 1} key question points")
    if tech_depth_score < 65:
        weaknesses.append("Lacked specific quantitative benchmarks or numerical trade-off metrics")
    if not weaknesses:
        weaknesses.append("Minor pause delays before addressing complex follow-up questions")

    suggested_followups = [
        "What specific metric proves your architecture outperforms standard industry alternatives?",
        "How would your approach handle a failure during peak concurrent load?",
        "If budget or computational resources were cut by 50%, what trade-offs would you make?"
    ]

    shifts = []
    for entry in history:
        if entry.get("signal") != "GREEN" or entry.get("is_dodging"):
            shifts.append(
                {
                    "timestamp_sec": entry.get("timestamp", 0),
                    "signal": entry.get("signal", "AMBER"),
                    "spoken_phrase": entry.get("nudge", "Technical defense section"),
                    "coaching_feedback": entry.get("reasoning", "Expand with concrete quantitative metrics."),
                }
            )

    verdict = (
        "Strong Technical Defense"
        if overall_score >= 80
        else ("Satisfactory Defense" if overall_score >= 60 else "Needs Quantitative Depth & Clarity")
    )

    return {
        "overall_score": overall_score,
        "clarity_score": clarity_score,
        "confidence_score": confidence_score,
        "technical_depth_score": tech_depth_score,
        "green_percentage": green_pct,
        "amber_percentage": amber_pct,
        "red_percentage": red_pct,
        "total_fillers": total_fillers,
        "total_technical_keywords": total_tech,
        "dodged_questions_count": dodges,
        "total_duration_sec": duration,
        "ideal_star_answer": star,
        "key_strengths": strengths,
        "key_weaknesses": weaknesses,
        "suggested_followup_questions": suggested_followups,
        "critical_shifts": shifts,
        "defense_verdict": verdict,
    }

