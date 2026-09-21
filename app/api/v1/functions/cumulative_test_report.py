from app.schemas.test_interview import TestCumulativeReportRequest, TestCumulativeReportResponse
from app.services.test_simulator import generate_cumulative_report


async def cumulative_test_report(req: TestCumulativeReportRequest) -> TestCumulativeReportResponse:
    """Generates a cumulative readiness report summarizing student performance across all completed test questions."""
    res = generate_cumulative_report(req.domain, req.format, req.evaluations)
    return TestCumulativeReportResponse(**res)

