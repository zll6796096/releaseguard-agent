import pytest
from app.models import EvidenceItem
from app.report import ReportGenerator

def test_report_generation():
    generator = ReportGenerator()
    evidence = [
        EvidenceItem(category="api_health", status="success", message="Health is good", risk_score=0),
        EvidenceItem(
            category="playwright_probe", 
            status="fail", 
            message="Checkout button is invisible", 
            risk_score=90, 
            details={"screenshot_path": "/tmp/releaseguard-artifacts/checkout.png"}
        )
    ]
    triggered_rules = ["Rule: Playwright journey check failed."]
    
    report = generator.generate(
        verdict="BLOCK",
        overall_risk=90,
        evidence=evidence,
        triggered_rules=triggered_rules
    )
    
    assert "🛡️ ReleaseGuard Verdict:" in report
    assert "BLOCK" in report
    assert "Overall Risk Score" in report
    assert "`90/100`" in report
    assert "Checkout button is invisible" in report
    assert "playwright_probe" in report
    assert "Affected Journeys" in report
    # Affected journey is checkout
    assert "checkout" in report
    # Contains screenshot path
    assert "/tmp/releaseguard-artifacts/checkout.png" in report
