import httpx
import re
from typing import List
from app.models import EvaluationRequest, EvidenceItem
from app.skills.base import BaseSkill

class ApiProbe(BaseSkill):
    """Probes the target preview application endpoints for health and usability."""

    async def evaluate(self, request: EvaluationRequest) -> List[EvidenceItem]:
        """Runs healthz and checkout page HTTP checks.

        Args:
            request (EvaluationRequest): The incoming release request.

        Returns:
            List[EvidenceItem]: API probe evidence.
        """
        evidence = []
        from urllib.parse import urlparse, urlunparse
        parsed = urlparse(request.preview_url)
        
        # 1. Probe /healthz (without original query params)
        healthz_url = urlunparse((parsed.scheme, parsed.netloc, "/healthz", "", "", ""))
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(healthz_url)
                if res.status_code == 200 and res.json().get("status") == "ok":
                    evidence.append(EvidenceItem(
                        category="api_health",
                        status="success",
                        message="Service health check passed successfully.",
                        risk_score=0,
                        details={"status_code": 200, "body": res.json()}
                    ))
                else:
                    evidence.append(EvidenceItem(
                        category="api_health",
                        status="failure",
                        message=f"Service health check failed with status code {res.status_code}.",
                        risk_score=10,
                        details={"status_code": res.status_code, "body": res.text[:200]}
                    ))
        except Exception as e:
            evidence.append(EvidenceItem(
                category="api_health",
                status="failure",
                message=f"Could not connect to health endpoint: {str(e)}",
                risk_score=10,
                details={"error": str(e)}
            ))

        # 2. Probe /checkout (preserving query params)
        checkout_url = urlunparse((parsed.scheme, parsed.netloc, "/checkout", "", parsed.query, parsed.fragment))
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(checkout_url)
                if res.status_code != 200:
                    evidence.append(EvidenceItem(
                        category="api_checkout",
                        status="failure",
                        message=f"Checkout page load failed with status code {res.status_code}.",
                        risk_score=10,
                        details={"status_code": res.status_code}
                    ))
                else:
                    html_content = res.text
                    
                    # Verify presence of the button with data-testid="checkout-button"
                    # Example button: <button type="submit" data-testid="checkout-button" class="btn-primary {% if hide_button %}hidden-button{% endif %}" id="checkout-btn">
                    has_testid = 'data-testid="checkout-button"' in html_content
                    has_hidden_class = "hidden-button" in html_content
                    
                    if not has_testid:
                        evidence.append(EvidenceItem(
                            category="api_checkout",
                            status="failure",
                            message="Checkout button with data-testid='checkout-button' was not found in the DOM.",
                            risk_score=10,
                            details={"button_found": False}
                        ))
                    elif has_hidden_class:
                        evidence.append(EvidenceItem(
                            category="api_checkout",
                            status="failure",
                            message="Checkout button is present in the DOM but has 'hidden-button' CSS class applied (invisible to users).",
                            risk_score=9,
                            details={"button_found": True, "invisible": True}
                        ))
                    else:
                        evidence.append(EvidenceItem(
                            category="api_checkout",
                            status="success",
                            message="Checkout button is present and visible to users.",
                            risk_score=0,
                            details={"button_found": True, "invisible": False}
                        ))
        except Exception as e:
            evidence.append(EvidenceItem(
                category="api_checkout",
                status="failure",
                message=f"Could not connect to checkout page: {str(e)}",
                risk_score=10,
                details={"error": str(e)}
            ))
            
        return evidence
