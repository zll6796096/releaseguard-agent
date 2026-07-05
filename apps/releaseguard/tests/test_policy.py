import pytest
from app.models import EvidenceItem
from app.skills.risk_policy import RiskPolicy

def test_policy_approve():
    policy = RiskPolicy()
    evidence = [
        EvidenceItem(category="api_health", status="success", message="OK", risk_score=0),
        EvidenceItem(category="api_checkout", status="success", message="OK", risk_score=0),
        EvidenceItem(category="secret_scan", status="success", message="OK", risk_score=0),
        EvidenceItem(category="playwright_probe", status="pass", message="OK", risk_score=0)
    ]
    verdict, triggered, risk = policy.decide(evidence)
    assert verdict == "APPROVE"
    assert len(triggered) == 0
    assert risk == 0

def test_policy_block_on_checkout_invisible():
    policy = RiskPolicy()
    evidence = [
        EvidenceItem(category="api_health", status="success", message="OK", risk_score=0),
        EvidenceItem(category="api_checkout", status="failure", message="Invisible button", risk_score=90),
        EvidenceItem(category="secret_scan", status="success", message="OK", risk_score=0)
    ]
    verdict, triggered, risk = policy.decide(evidence)
    assert verdict == "BLOCK"
    assert any("Checkout page failed or checkout button was missing/invisible" in rule for rule in triggered)
    assert risk == 90

def test_policy_block_on_secret_scan():
    policy = RiskPolicy()
    evidence = [
        EvidenceItem(category="api_health", status="success", message="OK", risk_score=0),
        EvidenceItem(category="api_checkout", status="success", message="OK", risk_score=0),
        EvidenceItem(category="secret_scan", status="failure", message="Secret leaked", risk_score=95)
    ]
    verdict, triggered, risk = policy.decide(evidence)
    assert verdict == "BLOCK"
    assert any("Secret scan detected exposed credentials" in rule for rule in triggered)
    assert risk == 95

def test_policy_block_on_playwright_fail():
    policy = RiskPolicy()
    evidence = [
        EvidenceItem(category="api_health", status="success", message="OK", risk_score=0),
        EvidenceItem(category="api_checkout", status="success", message="OK", risk_score=0),
        EvidenceItem(category="playwright_probe", status="fail", message="Button hidden", risk_score=90)
    ]
    verdict, triggered, risk = policy.decide(evidence)
    assert verdict == "BLOCK"
    assert any("Playwright journey check failed" in rule for rule in triggered)
    assert risk == 90

def test_policy_warn_on_playwright_warning_api_pass():
    policy = RiskPolicy()
    evidence = [
        EvidenceItem(category="api_health", status="success", message="OK", risk_score=0),
        EvidenceItem(category="api_checkout", status="success", message="OK", risk_score=0),
        EvidenceItem(category="playwright_probe", status="warning", message="No browser", risk_score=50)
    ]
    verdict, triggered, risk = policy.decide(evidence)
    # API checks passed, so Playwright warning alone should trigger a WARN verdict
    assert verdict == "WARN"
    assert any("Playwright probe could not run, but API checks passed" in rule for rule in triggered)
    assert risk == 50

def test_policy_block_on_playwright_warning_api_fail():
    policy = RiskPolicy()
    evidence = [
        EvidenceItem(category="api_health", status="failure", message="Down", risk_score=80),
        EvidenceItem(category="api_checkout", status="failure", message="Down", risk_score=85),
        EvidenceItem(category="playwright_probe", status="warning", message="No browser", risk_score=50)
    ]
    verdict, triggered, risk = policy.decide(evidence)
    assert verdict == "BLOCK"
    assert any("Playwright probe could not run and API probe failed" in rule for rule in triggered)
    assert risk == 85
