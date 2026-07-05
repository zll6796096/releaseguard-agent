import pytest
from app.models import EvaluationRequest
from app.skills.secret_scan import SecretScan

@pytest.mark.asyncio
async def test_secret_scan_clean():
    scanner = SecretScan()
    req = EvaluationRequest(
        repo="owner/repo",
        pr_number=1,
        commit_sha="abc",
        preview_url="http://test",
        diff_text="""
        diff --git a/app/main.py b/app/main.py
        index 12345..67890 100644
        --- a/app/main.py
        +++ b/app/main.py
        @@ -1,3 +1,3 @@
        -print("hello")
        +print("world")
        """
    )
    evidence = await scanner.evaluate(req)
    assert len(evidence) == 1
    assert evidence[0].status == "success"
    assert evidence[0].risk_score == 0

@pytest.mark.asyncio
async def test_secret_scan_detects_github_token():
    scanner = SecretScan()
    req = EvaluationRequest(
        repo="owner/repo",
        pr_number=1,
        commit_sha="abc",
        preview_url="http://test",
        diff_text="""
        +++ b/config.py
        +GITHUB_TOKEN = "ghp_1234567890abcdefghijklmnopqrstuvwxyzAB"
        """
    )
    evidence = await scanner.evaluate(req)
    assert len(evidence) == 1
    assert evidence[0].status == "failure"
    assert evidence[0].risk_score == 95
    assert "Detected 1 potential secret" in evidence[0].message
    assert any(sec["type"] == "github_token" for sec in evidence[0].details["secrets_found"])

@pytest.mark.asyncio
async def test_secret_scan_detects_private_key():
    scanner = SecretScan()
    req = EvaluationRequest(
        repo="owner/repo",
        pr_number=1,
        commit_sha="abc",
        preview_url="http://test",
        diff_text="""
        +-----BEGIN RSA PRIVATE KEY-----
        +MIIEowIBAAKCAQEA0y8b...
        +-----END RSA PRIVATE KEY-----
        """
    )
    evidence = await scanner.evaluate(req)
    assert len(evidence) == 1
    assert evidence[0].status == "failure"
    assert evidence[0].risk_score == 95
    assert any(sec["type"] == "private_key" for sec in evidence[0].details["secrets_found"])
