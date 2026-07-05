# ReleaseGuard Agent MVP — 3-Minute Demo Video Script

This script outlines the flow, screens, and narrative for a 2-3 minute demo video submission.

---

## 🕒 Video Outline & Timeline

| Time | Scene / Screen | Narration / Actions |
|---|---|---|
| **0:00 - 0:30** | **1. The Problem**<br>• Slide or Repository Home Page | "Hi everyone. Standard CI workflows do a great job checking if unit tests pass, but they don't check if the user journey is actually intact. For example, if a developer introduces a CSS change that sets opacity to zero on the checkout button, the element is still in the DOM. Unit tests pass, CI is green, but users cannot buy anything. Meet ReleaseGuard: an evidence-based AI release gate for Cloud Run." |
| **0:30 - 1:00** | **2. Healthy App Preview**<br>• Live Demo Store URL: `https://demo-store-788259830737.asia-northeast1.run.app` | "First, let's look at our healthy storefront deployed on Google Cloud Run. We can see the 'Pay $99.00' checkout button is visible, clickable, and our API `/healthz/` probe returns a clean status." |
| **1:00 - 1:30** | **3. The Buggy PR & Branch Preview**<br>• GitHub PR #2 Diff View<br>• Deployed Preview Service: `https://demo-store-pr-hidden-788259830737.asia-northeast1.run.app` | "Now, we have a developer submit a Pull Request that introduces a regression: the checkout button is hardcoded with a `hidden-button` class. When deployed to a dedicated Cloud Run PR preview branch, the page looks blank—the button is completely gone! Let's see how ReleaseGuard handles this." |
| **1:30 - 2:00** | **4. ReleaseGuard Probing & AI Synthesis**<br>• GitHub Actions Run Log View | "On the PR trigger, the ReleaseGuard workflow invokes our agent on Cloud Run. The agent boots up Playwright, visits the preview URL, checks DOM attributes, runs API probes, scans the diff text for leaked credentials, and synthesizes the findings using Gemini." |
| **2:00 - 2:40** | **5. The Verdict & The Block**<br>• PR #2 Comments View (BLOCK)<br>• GitHub Actions Failed Status Check | "Here is the result. ReleaseGuard comments directly on the PR with a detailed Markdown report: A bold BLOCK verdict, an overall risk score of 90/100, and clear evidence showing the Playwright probe detected `opacity: 0`. It also warns against auto-merging or shifting production traffic. Because the verdict is BLOCK, the GitHub Action workflow immediately fails, preventing any automated deployment scripts from shifting live traffic." |
| **2:40 - 3:00** | **6. Wrap Up**<br>• Summary slide / Key Documents | "By combining deterministic policy checks with LLM synthesis, ReleaseGuard delivers an intelligent, context-aware release gate layer that keeps broken code away from production. The project is open-source and ready to deploy. Thank you!" |
