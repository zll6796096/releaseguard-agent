import asyncio

from app.models import EvaluationRequest, EvidenceItem, ReleaseDecision
from app.report import ReportGenerator
from app.skills.api_probe import ApiProbe
from app.skills.gemini_judge import GeminiJudge
from app.skills.playwright_probe import PlaywrightProbe
from app.skills.risk_policy import RiskPolicy
from app.skills.secret_scan import SecretScan


class EvaluationOrchestrator:
    """Orchestrates evidence collection skills, risk evaluation, and report generation."""

    def __init__(self):
        self.probes = [ApiProbe(), SecretScan(), PlaywrightProbe()]
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
        results: list[list[EvidenceItem]] = await asyncio.gather(*tasks)

        # Flatten the list of evidence
        flat_evidence: list[EvidenceItem] = []
        for res_list in results:
            flat_evidence.extend(res_list)

        # Apply deterministic rules first
        prelim_verdict, triggered_rules, prelim_risk = self.policy.decide(
            flat_evidence
        )

        # Call Gemini Judge to synthesize evidence
        gemini_judgement = await self.judge.judge(
            request, flat_evidence, prelim_verdict
        )

        # Fail closed unless both independent gates explicitly approve. A WARN,
        # human-review requirement, or fallback judgement is not release authority.
        gate_failures = []
        if prelim_verdict != "APPROVE":
            gate_failures.append(
                f"Rule: Deterministic policy did not explicitly APPROVE ({prelim_verdict})."
            )
        if gemini_judgement.decision != "APPROVE":
            gate_failures.append(
                f"Rule: Gemini AI recommended {gemini_judgement.decision} due to high risk."
            )
        if gemini_judgement.human_approval_required:
            gate_failures.append("Rule: Gemini judgement requires human approval.")
        if gemini_judgement.is_fallback:
            gate_failures.append("Rule: Gemini fallback judgement cannot authorize release.")

        triggered_rules.extend(gate_failures)
        final_verdict = "BLOCK" if gate_failures else "APPROVE"

        # Final risk score = max of deterministic risk score and Gemini risk score
        final_risk = max(prelim_risk, gemini_judgement.risk_score)

        # Generate markdown report including Gemini explanation
        markdown_report = self.reporter.generate(
            verdict=final_verdict,
            overall_risk=final_risk,
            evidence=flat_evidence,
            triggered_rules=triggered_rules,
            gemini_judgement=gemini_judgement,
        )

        return ReleaseDecision(
            verdict=final_verdict,
            overall_risk=final_risk,
            evidence=flat_evidence,
            triggered_rules=triggered_rules,
            markdown_report=markdown_report,
            gemini_judgement=gemini_judgement,
        )
