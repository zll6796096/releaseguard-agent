from typing import Optional
from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.models import EvaluationRequest, ReleaseDecision
from app.orchestrator import EvaluationOrchestrator
from app.config import settings
import structlog

# Initialize structured logger
logger = structlog.get_logger()

app = FastAPI(title="ReleaseGuard Agent")
orchestrator = EvaluationOrchestrator()

security = HTTPBearer(auto_error=False)

async def verify_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """Verifies the bearer token if RELEASEGUARD_SHARED_TOKEN is configured."""
    if settings.RELEASEGUARD_SHARED_TOKEN:
        if not credentials or credentials.scheme != "Bearer" or credentials.credentials != settings.RELEASEGUARD_SHARED_TOKEN:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized: Invalid or missing token"
            )

@app.get("/healthz")
@app.get("/healthz/")
def healthz():
    """Health check endpoint."""
    return {"status": "ok"}

@app.post(
    "/evaluate",
    response_model=ReleaseDecision,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_token)]
)
async def evaluate(request: EvaluationRequest):
    """Evaluates a release preview environment and code changes for security and UX bugs.

    Args:
        request (EvaluationRequest): The metadata and location of changes.

    Returns:
        ReleaseDecision: Verdict, risk analysis, and markdown summary.
    """
    logger.info("evaluation_started", repo=request.repo, pr_number=request.pr_number, commit_sha=request.commit_sha)
    try:
        decision = await orchestrator.evaluate(request)
        logger.info(
            "evaluation_completed",
            repo=request.repo,
            pr_number=request.pr_number,
            verdict=decision.verdict,
            overall_risk=decision.overall_risk
        )
        return decision
    except Exception as e:
        logger.exception("evaluation_failed", repo=request.repo, pr_number=request.pr_number, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal evaluation error: {str(e)}"
        )
