from app.schemas.debrief import DebriefRequest, DebriefResponse
from app.services.evaluator import generate_debrief


async def debrief_endpoint(req: DebriefRequest) -> DebriefResponse:
    """Generates a post-defense session debrief report containing STAR framework analysis, sub-scores, and final verdict."""
    res = generate_debrief(
        ground_truth=req.ground_truth,
        target_question=req.target_question,
        full_transcript=req.full_transcript,
        history=req.history,
    )
    return DebriefResponse(**res)

