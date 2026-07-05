import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from app.main import app
from app.config import settings
from app.models import EvidenceItem, GeminiJudgement

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_token():
    # Save original token
    orig_token = settings.RELEASEGUARD_SHARED_TOKEN
    yield
    # Restore original token
    settings.RELEASEGUARD_SHARED_TOKEN = orig_token

def test_unauthorized_evaluate():
    settings.RELEASEGUARD_SHARED_TOKEN = "secret-token"
    # Call evaluate without authorization
    response = client.post("/evaluate", json={
        "repo": "owner/repo",
        "pr_number": 1,
        "commit_sha": "abc",
        "preview_url": "http://test"
    })
    assert response.status_code == 401
    assert "Unauthorized" in response.json()["detail"]

    # Call with wrong authorization
    response = client.post("/evaluate", json={
        "repo": "owner/repo",
        "pr_number": 1,
        "commit_sha": "abc",
        "preview_url": "http://test"
    }, headers={"Authorization": "Bearer wrong-token"})
    assert response.status_code == 401

    # Call with correct token (and mock the orchestrator to prevent real calls)
    from app.models import ReleaseDecision
    dummy_decision = ReleaseDecision(
        verdict="APPROVE",
        overall_risk=0,
        evidence=[],
        triggered_rules=[],
        markdown_report="OK"
    )
    with patch("app.main.orchestrator.evaluate", new_callable=AsyncMock) as mock_eval:
        mock_eval.return_value = dummy_decision
        response = client.post("/evaluate", json={
            "repo": "owner/repo",
            "pr_number": 1,
            "commit_sha": "abc",
            "preview_url": "http://test"
        }, headers={"Authorization": "Bearer secret-token"})
        assert response.status_code == 200

def test_healthz_always_public():
    settings.RELEASEGUARD_SHARED_TOKEN = "secret-token"
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
@patch("app.skills.api_probe.ApiProbe.evaluate", new_callable=AsyncMock)
@patch("app.skills.secret_scan.SecretScan.evaluate", new_callable=AsyncMock)
@patch("app.skills.playwright_probe.PlaywrightProbe.evaluate", new_callable=AsyncMock)
@patch("app.skills.gemini_judge.GeminiJudge.judge", new_callable=AsyncMock)
async def test_api_scenarios_clean(mock_judge, mock_playwright, mock_secret, mock_api):
    settings.RELEASEGUARD_SHARED_TOKEN = ""
    
    # 1. Clean Scenario
    mock_api.return_value = [
        EvidenceItem(category="api_health", status="success", message="OK", risk_score=0),
        EvidenceItem(category="api_checkout", status="success", message="OK", risk_score=0)
    ]
    mock_secret.return_value = [
        EvidenceItem(category="secret_scan", status="success", message="OK", risk_score=0)
    ]
    mock_playwright.return_value = [
        EvidenceItem(category="playwright_probe", status="pass", message="OK", risk_score=0)
    ]
    mock_judge.return_value = GeminiJudgement(
        decision="APPROVE",
        risk_score=0,
        confidence=1.0,
        affected_journey="checkout",
        why="Clean",
        evidence=[],
        safe_next_action="",
        unsafe_actions=[],
        human_approval_required=False
    )

    response = client.post("/evaluate", json={
        "repo": "owner/repo",
        "pr_number": 1,
        "commit_sha": "abc",
        "preview_url": "http://test"
    })
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["verdict"] == "APPROVE"
    assert res_json["overall_risk"] < 50
    assert "file://" not in res_json["markdown_report"]

@pytest.mark.asyncio
@patch("app.skills.api_probe.ApiProbe.evaluate", new_callable=AsyncMock)
@patch("app.skills.secret_scan.SecretScan.evaluate", new_callable=AsyncMock)
@patch("app.skills.playwright_probe.PlaywrightProbe.evaluate", new_callable=AsyncMock)
@patch("app.skills.gemini_judge.GeminiJudge.judge", new_callable=AsyncMock)
async def test_api_scenarios_hidden_checkout(mock_judge, mock_playwright, mock_secret, mock_api):
    settings.RELEASEGUARD_SHARED_TOKEN = ""

    # 2. Hidden Checkout Scenario (Playwright fail: 90)
    mock_api.return_value = [
        EvidenceItem(category="api_health", status="success", message="OK", risk_score=0),
        EvidenceItem(category="api_checkout", status="success", message="OK", risk_score=0)
    ]
    mock_secret.return_value = []
    mock_playwright.return_value = [
        EvidenceItem(category="playwright_probe", status="fail", message="Invisible", risk_score=90, details={"screenshot_path": "/tmp/releaseguard-artifacts/checkout.png"})
    ]
    mock_judge.return_value = GeminiJudgement(
        decision="BLOCK",
        risk_score=90,
        confidence=0.9,
        affected_journey="checkout",
        why="Invisible button",
        evidence=[],
        safe_next_action="",
        unsafe_actions=[],
        human_approval_required=True
    )

    response = client.post("/evaluate", json={
        "repo": "owner/repo",
        "pr_number": 1,
        "commit_sha": "abc",
        "preview_url": "http://test"
    })
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["verdict"] == "BLOCK"
    assert res_json["overall_risk"] >= 90
    
    # Check that report contains decision, risk, evidence, and NO file:// link but contains TODO
    report = res_json["markdown_report"]
    assert "BLOCK" in report
    assert "Overall Risk Score" in report
    assert "playwright_probe" in report
    assert "file://" not in report
    assert "TODO" in report

@pytest.mark.asyncio
@patch("app.skills.api_probe.ApiProbe.evaluate", new_callable=AsyncMock)
@patch("app.skills.secret_scan.SecretScan.evaluate", new_callable=AsyncMock)
@patch("app.skills.playwright_probe.PlaywrightProbe.evaluate", new_callable=AsyncMock)
@patch("app.skills.gemini_judge.GeminiJudge.judge", new_callable=AsyncMock)
async def test_api_scenarios_secret_leak(mock_judge, mock_playwright, mock_secret, mock_api):
    settings.RELEASEGUARD_SHARED_TOKEN = ""

    # 3. Secret Leak Scenario (Secret scan: 95)
    mock_api.return_value = []
    mock_secret.return_value = [
        EvidenceItem(category="secret_scan", status="failure", message="Secret leaked", risk_score=95)
    ]
    mock_playwright.return_value = []
    mock_judge.return_value = GeminiJudgement(
        decision="BLOCK",
        risk_score=95,
        confidence=0.95,
        affected_journey="unknown",
        why="Secret leak",
        evidence=[],
        safe_next_action="",
        unsafe_actions=[],
        human_approval_required=True
    )

    response = client.post("/evaluate", json={
        "repo": "owner/repo",
        "pr_number": 1,
        "commit_sha": "abc",
        "preview_url": "http://test"
    })
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["verdict"] == "BLOCK"
    assert res_json["overall_risk"] >= 95
