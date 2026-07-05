#!/usr/bin/env python3
import os
import sys
import json
import subprocess
import urllib.request
import urllib.error

def run_git_command(args: list) -> str:
    """Executes a git command and returns its output. Returns empty string on failure."""
    try:
        res = subprocess.run(args, capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except Exception as e:
        print(f"Git command {' '.join(args)} failed: {str(e)}", file=sys.stderr)
        return ""

def main():
    print("ReleaseGuard Agent Caller Script Starting...")

    # Load configuration
    repo = os.environ.get("GITHUB_REPOSITORY", "owner/repo")
    pr_number_str = os.environ.get("PR_NUMBER")
    commit_sha = os.environ.get("COMMIT_SHA")
    preview_url = os.environ.get("RELEASEGUARD_PREVIEW_URL")
    agent_url = os.environ.get("RELEASEGUARD_AGENT_URL")
    shared_token = os.environ.get("RELEASEGUARD_SHARED_TOKEN", "")

    # Validation
    if not agent_url:
        print("Error: RELEASEGUARD_AGENT_URL environment variable is not configured.", file=sys.stderr)
        sys.exit(1)

    if not preview_url:
        print("Error: RELEASEGUARD_PREVIEW_URL environment variable is not configured.", file=sys.stderr)
        sys.exit(1)

    try:
        pr_number = int(pr_number_str) if pr_number_str else 0
    except ValueError:
        print(f"Warning: Invalid PR_NUMBER value: {pr_number_str}. Defaulting to 0.", file=sys.stderr)
        pr_number = 0

    if not commit_sha:
        # Fallback to local git commit SHA if GITHUB env var is missing
        commit_sha = run_git_command(["git", "rev-parse", "HEAD"]) or "unknown-sha"

    # Gather changed files and diff
    # Attempt to diff against base commit, otherwise diff against HEAD~1, or fallback to current uncommitted diff
    changed_files_raw = run_git_command(["git", "diff", "--name-only", "HEAD~1"])
    if not changed_files_raw:
        changed_files_raw = run_git_command(["git", "diff", "--name-only"])
    
    changed_files = [line.strip() for line in changed_files_raw.split("\n") if line.strip()]

    diff_text = run_git_command(["git", "diff", "HEAD~1"])
    if not diff_text:
        diff_text = run_git_command(["git", "diff"])

    # Cap diff text at 50KB to protect payload limits
    max_size = 50 * 1024
    if len(diff_text) > max_size:
        diff_text = diff_text[:max_size] + "\n\n[Diff truncated to 50KB limit]"

    # Prepare payload
    payload = {
        "repo": repo,
        "pr_number": pr_number,
        "commit_sha": commit_sha,
        "preview_url": preview_url,
        "changed_files": changed_files,
        "diff_text": diff_text
    }

    # Construct request
    endpoint = f"{agent_url.rstrip('/')}/evaluate"
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    if shared_token:
        # Add Authorization header without logging the token
        req.add_header("Authorization", f"Bearer {shared_token}")

    print(f"Sending evaluation request to ReleaseGuard Agent at {endpoint}...")
    print(f"Target Preview URL: {preview_url}")
    print(f"PR Number: {pr_number}, Commit SHA: {commit_sha}")
    print(f"Changed files count: {len(changed_files)}")

    try:
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode("utf-8")
            res_json = json.loads(res_body)
            
            # Print decision to logs
            verdict = res_json.get("verdict", "UNKNOWN")
            overall_risk = res_json.get("overall_risk", 0)
            print(f"\nReleaseGuard verdict received: {verdict} (Risk: {overall_risk}/100)")
            
            # Write response to file
            result_file = "releaseguard-result.json"
            with open(result_file, "w") as f:
                json.dump(res_json, f, indent=2)
            print(f"Evaluation output saved to {result_file} successfully.")
            
    except urllib.error.HTTPError as e:
        print(f"\nError: API request failed with status code {e.code}", file=sys.stderr)
        try:
            error_body = e.read().decode("utf-8")
            print(f"Response: {error_body}", file=sys.stderr)
        except Exception:
            pass
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"\nError: Could not connect to ReleaseGuard Agent: {e.reason}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
