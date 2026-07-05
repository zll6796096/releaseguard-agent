from typing import List, Tuple
from app.models import EvidenceItem

class RiskPolicy:
    """Applies deterministic rules to decide whether to APPROVE or BLOCK a release."""

    def decide(self, evidence: List[EvidenceItem]) -> Tuple[str, List[str], int]:
        """Applies release criteria rules over the gathered evidence items.

        Rules:
        - If checkout check fails (risk_score >= 8 or status == "failure"), BLOCK.
        - If secret scan check fails (risk_score >= 8 or status == "failure"), BLOCK.
        - If playwright probe fails (risk_score >= 80 or status == "fail"), BLOCK.
        - If Playwright cannot run (status == "warning"), WARN but do not BLOCK unless API checks also fail.
        - Otherwise APPROVE.

        Args:
            evidence (List[EvidenceItem]): The collected evidence list.

        Returns:
            Tuple[str, List[str], int]: (verdict, triggered_rules, overall_risk)
        """
        verdict = "APPROVE"
        triggered_rules = []
        overall_risk = 0

        # Calculate overall risk as the maximum risk score of all evidence items
        if evidence:
            overall_risk = max(item.risk_score for item in evidence)

        # Pre-assess if API probes failed
        api_failed = any(
            item.category in ("api_health", "api_checkout") and (item.status == "failure" or item.risk_score >= 8)
            for item in evidence
        )

        # Apply specific rules
        for item in evidence:
            if item.category == "api_checkout" and (item.status == "failure" or item.risk_score >= 8):
                verdict = "BLOCK"
                triggered_rules.append("Rule: Checkout page failed or checkout button was missing/invisible (API).")
            
            if item.category == "secret_scan" and (item.status == "failure" or item.risk_score >= 8):
                verdict = "BLOCK"
                triggered_rules.append("Rule: Secret scan detected exposed credentials or tokens in diff.")

            # General health check failure
            if item.category == "api_health" and (item.status == "failure" or item.risk_score >= 8):
                verdict = "BLOCK"
                triggered_rules.append("Rule: Preview environment health check failed.")

            # Playwright probe rules
            if item.category == "playwright_probe":
                if item.status == "fail" or item.risk_score >= 80:
                    verdict = "BLOCK"
                    triggered_rules.append("Rule: Playwright journey check failed (checkout button is not visible or usable).")
                elif item.status == "warning":
                    if api_failed:
                        verdict = "BLOCK"
                        triggered_rules.append("Rule: Playwright probe could not run and API probe failed.")
                    else:
                        # Playwright warning but API is healthy -> WARN but do not BLOCK
                        triggered_rules.append("Warning: Playwright probe could not run, but API checks passed (Proceed with caution).")

        return verdict, triggered_rules, overall_risk
