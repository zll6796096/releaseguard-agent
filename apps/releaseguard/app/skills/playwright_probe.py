import os
import logging
from typing import List
from app.models import EvaluationRequest, EvidenceItem
from app.skills.base import BaseSkill

# Setup logging
logger = logging.getLogger("playwright_probe")

async def check_checkout_button(preview_url: str) -> EvidenceItem:
    """Probes the checkout page in a headless Chromium browser using Playwright.

    Verifies if the checkout button is present and visible to the user.
    Saves a screenshot to /tmp/releaseguard-artifacts/checkout.png.

    Args:
        preview_url (str): The base preview URL.

    Returns:
        EvidenceItem: Playwright check result evidence.
    """
    screenshot_dir = "/tmp/releaseguard-artifacts"
    screenshot_path = os.path.join(screenshot_dir, "checkout.png")
    
    # Ensure directory exists
    try:
        os.makedirs(screenshot_dir, exist_ok=True)
    except Exception as e:
        logger.warning(f"Could not create directory {screenshot_dir}: {str(e)}")

    # Import playwright dynamically to handle cases where it isn't fully installed
    try:
        from playwright.async_api import async_playwright
    except ImportError as e:
        return EvidenceItem(
            category="playwright_probe",
            status="warning",
            message=f"Playwright library not installed: {str(e)}",
            risk_score=50,
            details={"error": "playwright_not_installed"}
        )

    try:
        url = preview_url.rstrip("/")
        if not url.endswith("/checkout") and "/checkout" not in url:
            from urllib.parse import urlparse, urlunparse
            parsed = urlparse(preview_url)
            checkout_url = urlunparse((parsed.scheme, parsed.netloc, "/checkout", "", parsed.query, parsed.fragment))
        else:
            checkout_url = preview_url

        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                # Open page and wait
                await page.goto(checkout_url, timeout=5000)
                await page.wait_for_load_state("networkidle", timeout=3000)
            except Exception as e:
                # If page cannot load, this is a failure
                await browser.close()
                return EvidenceItem(
                    category="playwright_probe",
                    status="fail",
                    message=f"Failed to navigate to checkout page: {str(e)}",
                    risk_score=90,
                    details={"error": str(e)}
                )

            # Check if selector is visible
            selector = '[data-testid="checkout-button"]'
            btn_element = page.locator(selector)
            
            exists = await btn_element.count() > 0
            is_visible = False
            opacity = "1"
            
            if exists:
                is_visible = await btn_element.is_visible()
                try:
                    # Also retrieve computed opacity, since opacity: 0 still counts as visible in standard layout
                    opacity = await btn_element.evaluate("el => window.getComputedStyle(el).opacity")
                except Exception:
                    opacity = "1"

            # A button is truly visible if it exists, page says it is visible, and computed opacity is not "0"
            button_truly_visible = exists and is_visible and opacity != "0"

            # Save screenshot
            try:
                await page.screenshot(path=screenshot_path)
            except Exception as e:
                logger.warning(f"Could not save screenshot: {str(e)}")

            await browser.close()

            if button_truly_visible:
                return EvidenceItem(
                    category="playwright_probe",
                    status="pass",
                    message="Checkout button with data-testid='checkout-button' is present and visible.",
                    risk_score=0,
                    details={
                        "screenshot_path": screenshot_path,
                        "button_found": True,
                        "is_visible": True,
                        "opacity": opacity
                    }
                )
            else:
                reason = "not found in DOM" if not exists else "hidden by CSS display/visibility" if not is_visible else "invisible due to opacity: 0"
                return EvidenceItem(
                    category="playwright_probe",
                    status="fail",
                    message=f"Checkout button with data-testid='checkout-button' is not visible ({reason}).",
                    risk_score=90,
                    details={
                        "screenshot_path": screenshot_path,
                        "button_found": exists,
                        "is_visible": is_visible,
                        "opacity": opacity,
                        "reason": reason
                    }
                )

    except Exception as e:
        return EvidenceItem(
            category="playwright_probe",
            status="warning",
            message=f"Playwright execution failed: {str(e)}",
            risk_score=50,
            details={"error": str(e)}
        )

class PlaywrightProbe(BaseSkill):
    """Probes the checkout UI using headless Chromium via Playwright."""

    async def evaluate(self, request: EvaluationRequest) -> List[EvidenceItem]:
        """Runs the playwright journey checks and captures a screenshot.

        Args:
            request (EvaluationRequest): The incoming release request.

        Returns:
            List[EvidenceItem]: Playwright probe evidence.
        """
        item = await check_checkout_button(request.preview_url)
        return [item]
