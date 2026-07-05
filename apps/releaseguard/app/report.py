from typing import List, Optional
from app.models import EvidenceItem, GeminiJudgement
import json

class ReportGenerator:
    """Generates user-friendly markdown reports summarizing release decisions."""

    def generate(
        self, 
        verdict: str, 
        overall_risk: int, 
        evidence: List[EvidenceItem], 
        triggered_rules: List[str],
        gemini_judgement: Optional[GeminiJudgement] = None
    ) -> str:
        """Constructs a Markdown report from evaluation results and Gemini analysis.

        Args:
            verdict (str): APPROVE or BLOCK decision.
            overall_risk (int): Overall risk score (0-100).
            evidence (List[EvidenceItem]): Gained evidence items.
            triggered_rules (List[str]): List of active risk policy rules triggered.
            gemini_judgement (Optional[GeminiJudgement]): Gemini AI judge's synthesis report.

        Returns:
            str: Markdown formatted string.
        """
        verdict_icon = "✅ APPROVE" if verdict == "APPROVE" else "🚫 BLOCK"
        
        lines = [
            f"## 🛡️ ReleaseGuard Verdict: {verdict_icon}",
            "",
            f"**Overall Risk Score**: `{overall_risk}/100`",
            ""
        ]

        if triggered_rules:
            lines.append("### ⚠️ Triggered Policy Rules")
            for rule in triggered_rules:
                lines.append(f"- {rule}")
            lines.append("")

        if gemini_judgement:
            lines.extend([
                "### 🧠 Gemini AI Judgement Synthesis",
                f"- **Verdict Recommendation**: `{gemini_judgement.decision}`",
                f"- **AI Risk Score**: `{gemini_judgement.risk_score}/100`",
                f"- **Confidence**: `{gemini_judgement.confidence * 100:.1f}%`",
                f"- **Analysis**: {gemini_judgement.why}",
                ""
            ])
            if gemini_judgement.safe_next_action:
                lines.append(f"- **Recommended Next Action**: {gemini_judgement.safe_next_action}")
            if gemini_judgement.unsafe_actions:
                lines.append("- **Unsafe Actions Detected**:")
                for action in gemini_judgement.unsafe_actions:
                    lines.append(f"  - ⚠️ {action}")
            lines.append("")

        lines.extend([
            "### 🛣️ Affected Journeys",
            f"- **Journey**: `{gemini_judgement.affected_journey if gemini_judgement else 'checkout'}`",
            "",
            "### 📊 Evidence Summary",
            "",
            "| Category | Status | Risk Score | Message |",
            "| --- | --- | --- | --- |"
        ])

        screenshot_path = None
        for item in evidence:
            status_icon = "🟢 Passed" if item.status in ("success", "pass") else "🔴 Failed" if item.status in ("failure", "fail") else "🟡 Warning"
            lines.append(f"| `{item.category}` | {status_icon} | `{item.risk_score}/100` | {item.message} |")
            
            # Check if screenshot is available in playwright probe details
            if item.details and "screenshot_path" in item.details:
                screenshot_path = item.details["screenshot_path"]

        if screenshot_path:
            lines.extend([
                "",
                "### 📸 Playwright Screenshot Artifact",
                f"**Path**: `{screenshot_path}`",
                f"![Checkout Page Screenshot](file://{screenshot_path})"
            ])

        lines.extend([
            "",
            "### 🔍 Detailed Findings"
        ])

        for item in evidence:
            if item.status not in ("success", "pass"):
                status_label = "🔴 Failed" if item.status in ("failure", "fail") else "🟡 Warning"
                lines.extend([
                    "",
                    f"#### {status_label} `{item.category}` (Risk: `{item.risk_score}/100`)",
                    f"**Details**: {item.message}",
                ])
                if item.details:
                    lines.append("```json")
                    lines.append(json.dumps(item.details, indent=2))
                    lines.append("```")

        lines.extend([
            "",
            "---",
            "*ReleaseGuard Agent v0.1.0 • Policy: Local Rule-Based + Playwright Probing + Gemini Synthesis*"
        ])

        return "\n".join(lines)
