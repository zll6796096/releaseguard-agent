import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.models import EvaluationRequest, EvidenceItem, GeminiJudgement, ReleaseDecision
from app.skills.gemini_judge import GeminiJudge
from app.orchestrator import EvaluationOrchestrator

@pytest.mark.asyncio
async def test_gemini_judge_missing_key():
    # If settings.GEMINI_API_KEY is empty, check that it returns fallback
    with patch("app.skills.gemini_judge.settings") as mock_settings:
        mock_settings.GEMINI_API_KEY = ""
        mock_settings.GEMINI_MODEL = "gemini-2.5-flash"
        
        judge = GeminiJudge()
        req = EvaluationRequest(
            repo="owner/repo", pr_number=1, commit_sha="abc", preview_url="http://test"
        )
        evidence = [EvidenceItem(category="api_health", status="success", message="OK", risk_score=0)]
        
        result = await judge.judge(req, evidence, "APPROVE")
        assert result.decision == "WARN"
        assert "Gemini API fallback activated" in result.why
        assert result.human_approval_required is True

@pytest.mark.asyncio
async def test_gemini_judge_api_failure():
    # If API call fails, check that it returns fallback
    with patch("app.skills.gemini_judge.settings") as mock_settings:
        mock_settings.GEMINI_API_KEY = "dummy-key"
        mock_settings.GEMINI_MODEL = "gemini-2.5-flash"
        
        with patch("app.skills.gemini_judge.genai.Client") as mock_client_cls:
            # Mock the client's generate_content call to raise Exception
            mock_client = MagicMock()
            mock_client.models.generate_content.side_effect = Exception("API Quota Exceeded")
            mock_client_cls.return_value = mock_client
            
            judge = GeminiJudge()
            req = EvaluationRequest(
                repo="owner/repo", pr_number=1, commit_sha="abc", preview_url="http://test"
            )
            evidence = [EvidenceItem(category="api_health", status="success", message="OK", risk_score=0)]
            
            result = await judge.judge(req, evidence, "APPROVE")
            assert result.decision == "WARN"
            assert "API Quota Exceeded" in result.why

@pytest.mark.asyncio
async def test_orchestrator_gemini_cannot_override_block():
    orchestrator = EvaluationOrchestrator()
    
    # Mock probes to return a failure (e.g. checkout button invisible -> BLOCK)
    mock_api_probe = AsyncMock()
    mock_api_probe.evaluate.return_value = [
        EvidenceItem(category="api_checkout", status="failure", message="Missing button", risk_score=90)
    ]
    mock_secret_scan = AsyncMock()
    mock_secret_scan.evaluate.return_value = []
    mock_playwright_probe = AsyncMock()
    mock_playwright_probe.evaluate.return_value = []
    
    orchestrator.probes = [mock_api_probe, mock_secret_scan, mock_playwright_probe]
    
    # Mock Gemini to return APPROVE
    mock_gemini = AsyncMock()
    mock_gemini.judge.return_value = GeminiJudgement(
        decision="APPROVE",
        risk_score=10,
        confidence=0.9,
        affected_journey="checkout",
        why="Gemini thinks everything is fine",
        evidence=["Tested OK"],
        safe_next_action="Deploy",
        unsafe_actions=[],
        human_approval_required=False
    )
    orchestrator.judge = mock_gemini
    
    req = EvaluationRequest(
        repo="owner/repo", pr_number=1, commit_sha="abc", preview_url="http://test"
    )
    
    decision = await orchestrator.evaluate(req)
    # The final decision must still be BLOCK because the deterministic policy blocked it!
    assert decision.verdict == "BLOCK"
    assert decision.overall_risk == 90 # Max of 90 (prelim) and 10 (Gemini)
    assert any("Checkout page failed or checkout button was missing/invisible" in rule for rule in decision.triggered_rules)

@pytest.mark.asyncio
async def test_orchestrator_gemini_blocks_when_preliminary_approves():
    orchestrator = EvaluationOrchestrator()
    
    # Mock probes to return success -> APPROVE
    mock_api_probe = AsyncMock()
    mock_api_probe.evaluate.return_value = [
        EvidenceItem(category="api_checkout", status="success", message="Visible", risk_score=0)
    ]
    mock_secret_scan = AsyncMock()
    mock_secret_scan.evaluate.return_value = []
    mock_playwright_probe = AsyncMock()
    mock_playwright_probe.evaluate.return_value = []
    
    orchestrator.probes = [mock_api_probe, mock_secret_scan, mock_playwright_probe]
    
    # Mock Gemini to return BLOCK
    mock_gemini = AsyncMock()
    mock_gemini.judge.return_value = GeminiJudgement(
        decision="BLOCK",
        risk_score=75,
        confidence=0.85,
        affected_journey="checkout",
        why="Gemini found UX layout regression not caught by API checks",
        evidence=["UX issue"],
        safe_next_action="Fix layout",
        unsafe_actions=["Shipping layout bug"],
        human_approval_required=True
    )
    orchestrator.judge = mock_gemini
    
    req = EvaluationRequest(
        repo="owner/repo", pr_number=1, commit_sha="abc", preview_url="http://test"
    )
    
    decision = await orchestrator.evaluate(req)
    # The final decision must be BLOCK because Gemini flagged BLOCK
    assert decision.verdict == "BLOCK"
    assert decision.overall_risk == 75 # Max of 0 (prelim) and 75 (Gemini)
    assert any("Gemini AI recommended BLOCK due to high risk." in rule for rule in decision.triggered_rules)
