import asyncio
from typing import List
from app.models import EvaluationRequest, ReleaseDecision, EvidenceItem
from app.skills.api_probe import ApiProbe
from app.skills.secret_scan import SecretScan
from app.skills.playwright_probe import PlaywrightProbe
from app.skills.risk_policy import RiskPolicy
from app.skills.gemini_judge import GeminiJudge
from app.report import ReportGenerator

class EvaluationOrchestrator:
    """Orchestrates evidence collection skills, risk evaluation, and report generation."""

    def __init__(self):
        self.probes = [
            ApiProbe(),
            SecretScan(),
            PlaywrightProbe()
        ]
        self.policy = RiskPolicy()
        self.judge = GeminiJudge()
        self.reporter = ReportGenerator()

    async def evaluate(self, request: EvaluationRequest) -> ReleaseDecision:
        """Executes all configured probes, aggregates evidence, runs policy rules, and calls Gemini.

        Args:
            request (EvaluationRequest): The incoming code change metadata.

        Returns:
            ReleaseDecision: Verdict, overall risk, raw evidence, triggered rules, Gemini judgement, and report.
        """
        # Execute all probes in parallel
        tasks = [probe.evaluate(request) for probe in self.probes]
        results: List[List[EvidenceItem]] = await asyncio.gather(*tasks)
        
        # Flatten the list of evidence
        flat_evidence: List[EvidenceItem] = []
        for res_list in results:
            flat_evidence.extend(res_list)

        # Apply deterministic rules first
        prelim_verdict, triggered_rules, prelim_risk = self.policy.decide(flat_evidence)

        # Call Gemini Judge to synthesize evidence
        gemini_judgement = await self.judge.judge(request, flat_evidence, prelim_verdict)

        # Do not let Gemini override deterministic BLOCK
        # Final decision is BLOCK if either prelim or Gemini says BLOCK (or FIX_PR, ESCALATE)
        final_verdict = prelim_verdict
        if prelim_verdict != "BLOCK":
            if gemini_judgement.decision in ("BLOCK", "ESCALATE", "FIX_PR"):
                final_verdict = "BLOCK"
                triggered_rules.append(f"Rule: Gemini AI recommended {gemini_judgement.decision} due to high risk.")
            else:
                final_verdict = "APPROVE"

        # Final risk score = max of deterministic risk score and Gemini risk score
        final_risk = max(prelim_risk, gemini_judgement.risk_score)

        # Generate markdown report including Gemini explanation
        markdown_report = self.reporter.generate(
            verdict=final_verdict,
            overall_risk=final_risk,
            evidence=flat_evidence,
            triggered_rules=triggered_rules,
            gemini_judgement=gemini_judgement
        )

        return ReleaseDecision(
            verdict=final_verdict,
            overall_risk=final_risk,
            evidence=flat_evidence,
            triggered_rules=triggered_rules,
            markdown_report=markdown_report,
            gemini_judgement=gemini_judgement
        )
