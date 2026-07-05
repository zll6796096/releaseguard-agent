import re
from typing import List
from app.models import EvaluationRequest, EvidenceItem
from app.skills.base import BaseSkill

class SecretScan(BaseSkill):
    """Scans the PR diff text for leaked credentials and secrets."""

    def __init__(self):
        # Define regex patterns for typical secrets
        self.patterns = {
            "private_key": re.compile(r"-----BEGIN [A-Z\s]+ PRIVATE KEY-----"),
            "github_token": re.compile(r"(?:ghp_|github_pat_)[a-zA-Z0-9_]{36,82}"),
            "gcp_service_account": re.compile(r'"type":\s*"service_account"'),
            "generic_api_key": re.compile(r'(?:api[_-]key|secret|password|passwd|auth_token)\s*[:=]\s*["\'][a-zA-Z0-9_\-\.\~]{16,}["\']', re.IGNORECASE)
        }

    async def evaluate(self, request: EvaluationRequest) -> List[EvidenceItem]:
        """Scans the diff_text from the pull request for potential secrets.

        Args:
            request (EvaluationRequest): The incoming release request.

        Returns:
            List[EvidenceItem]: Secret scan evidence.
        """
        diff = request.diff_text
        if not diff:
            return [EvidenceItem(
                category="secret_scan",
                status="success",
                message="No diff text provided to scan.",
                risk_score=0,
                details={"secrets_found": []}
            )]

        found_secrets = []
        for name, pattern in self.patterns.items():
            matches = pattern.findall(diff)
            if matches:
                # Mask matches to prevent printing them directly in logs/reports
                masked_matches = [m[:10] + "..." + m[-4:] if len(m) > 14 else "..." for m in matches]
                found_secrets.append({
                    "type": name,
                    "count": len(matches),
                    "examples": masked_matches
                })

        if found_secrets:
            total_secrets = sum(item["count"] for item in found_secrets)
            return [EvidenceItem(
                category="secret_scan",
                status="failure",
                message=f"Detected {total_secrets} potential secret(s) in PR diff.",
                risk_score=95,
                details={"secrets_found": found_secrets}
            )]
        
        return [EvidenceItem(
            category="secret_scan",
            status="success",
            message="No credentials or secrets detected in PR diff.",
            risk_score=0,
            details={"secrets_found": []}
        )]
