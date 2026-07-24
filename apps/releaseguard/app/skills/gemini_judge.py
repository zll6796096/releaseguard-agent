import json

import structlog
from app.config import settings
from app.models import EvaluationRequest, EvidenceItem, GeminiJudgement
from google import genai
from google.genai import types

logger = structlog.get_logger()


class GeminiJudge:
    """Uses Gemini API to synthesize collected evidence and generate structured release judgements."""

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.GEMINI_MODEL

    def _get_fallback_judgement(self, reason: str) -> GeminiJudgement:
        """Helper to create a structured fallback judgement on failure or missing API keys.

        Args:
            reason (str): Reason for activating the fallback.

        Returns:
            GeminiJudgement: Structured fallback judgement.
        """
        return GeminiJudgement(
            decision="WARN",
            risk_score=50,
            confidence=0.5,
            affected_journey="unknown",
            why=f"Gemini API fallback activated: {reason}",
            evidence=["Gemini API was skipped or failed"],
            safe_next_action="Perform manual visual validation of checkout journey and code diff.",
            unsafe_actions=[
                "Relying on automatic AI validation without checking key configuration."
            ],
            human_approval_required=True,
            is_fallback=True,
        )

    async def judge(
        self,
        request: EvaluationRequest,
        evidence: list[EvidenceItem],
        preliminary_verdict: str,
    ) -> GeminiJudgement:
        """Sends collected evidence and request diff metadata to Gemini for structured release analysis.

        Args:
            request (EvaluationRequest): The incoming release request validation parameters.
            evidence (List[EvidenceItem]): The collected evidence list.
            preliminary_verdict (str): The preliminary safety verdict from local rules.

        Returns:
            GeminiJudgement: The final structured judgement object.
        """
        # If API key is not configured, return fallback immediately
        if not self.api_key:
            logger.info("gemini_api_key_missing_using_fallback")
            return self._get_fallback_judgement(
                "GEMINI_API_KEY environment variable is not configured."
            )

        # Format input evidence list
        evidence_summary = []
        for item in evidence:
            evidence_summary.append(
                {
                    "category": item.category,
                    "status": item.status,
                    "message": item.message,
                    "risk_score": item.risk_score,
                }
            )

        # Keep prompt clear, structured, and do not leak keys/secrets
        prompt = f"""
Please evaluate the following release request:

- Repo: {request.repo}
- PR Number: {request.pr_number}
- Commit SHA: {request.commit_sha}
- Changed Files: {json.dumps(request.changed_files)}
- Preliminary Policy Decision: {preliminary_verdict}

### Collected Evidence
{json.dumps(evidence_summary, indent=2)}

### Code Diff Snippet (summarized/sanitized)
{request.diff_text[:5000]}
"""

        system_instruction = """
You are ReleaseGuard, an evidence-based AI release gate for Cloud Run. Your job is to decide whether the collected evidence is strong enough to ship a PR.

Hard Safety Rules:
1. NEVER recommend auto-merge under any circumstance.
2. NEVER recommend production traffic shifts.
3. Any destructive database changes, security key leaks, or payment pathway changes require ESCALATE.
4. Insufficient evidence cannot lead to an APPROVE verdict.

An APPROVE result is only an evidence-sufficiency judgement. It does not authorize merge or production traffic.
Set human_approval_required to true only when unresolved risk or insufficient evidence requires additional human review.
Do not set it to true merely because merge and production traffic remain separate, guarded deployment actions.

Analyze the visual and API evidence, check if critical elements are hidden or broken (such as the checkout button), and verify there are no exposed credentials.
Return your decision matching the requested schema.
"""

        try:
            # Initialize the official Google GenAI Client
            client = genai.Client(api_key=self.api_key)

            # Request Gemini structured JSON mode using response_schema
            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=GeminiJudgement,
                    system_instruction=system_instruction,
                    temperature=0.1,
                ),
            )

            if not response.text:
                raise ValueError("Empty response received from Gemini API.")

            # Validate output matches the Pydantic schema
            judgement = GeminiJudgement.model_validate_json(response.text)
            return judgement

        except Exception as e:
            logger.exception("gemini_api_call_failed", error=str(e))
            return self._get_fallback_judgement(
                f"Gemini API call failed with exception: {e!s}"
            )
