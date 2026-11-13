"""
backend/integrations/github_client.py
GitHub API client for inspecting recent repository commits on affected services.
Features exponential backoff retry and a clearly labelled mock fallback.
Records fallback events in the incident audit trail.
"""
import os
import time
import httpx
from typing import Dict, Any, List, Tuple


class GitHubClient:
    """Client for querying GitHub API commits with retry and transparent fallback."""

    def __init__(self, token: str = None, repo: str = None):
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.repo = repo or os.getenv("GITHUB_REPOSITORY", "pagerpal/e-commerce-microservices")
        self.base_url = "https://api.github.com"

    def get_recent_commits(
        self,
        service: str,
        max_retries: int = 2
    ) -> Tuple[List[Dict[str, Any]], bool, str]:
        """
        Fetches recent commits for a given microservice.
        Returns: (commits_list, is_fallback, audit_note)
        """
        if not self.token or "mock" in self.token or "test" in self.token:
            fallback = self._get_mock_commits(service)
            return fallback, True, "GitHub API fallback: GITHUB_TOKEN not configured or in test mode"

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "PagerPal-Incident-Response"
        }
        url = f"{self.base_url}/repos/{self.repo}/commits"
        params = {"path": f"services/{service}", "per_page": 5}

        for attempt in range(max_retries + 1):
            try:
                with httpx.Client(timeout=2.0) as client:
                    resp = client.get(url, headers=headers, params=params)
                    if resp.status_code == 200:
                        commits_data = resp.json()
                        formatted = [
                            {
                                "sha": c["sha"][:7],
                                "author": c["commit"]["author"]["name"],
                                "message": c["commit"]["message"].split("\n")[0],
                                "date": c["commit"]["author"]["date"],
                                "source": "github_api_live"
                            }
                            for c in commits_data
                        ]
                        return formatted, False, "Live GitHub API commits retrieved successfully"
                    elif resp.status_code in [401, 403, 404]:
                        # Non-retryable API error
                        reason = f"GitHub API responded with status {resp.status_code}"
                        return self._get_mock_commits(service), True, f"GitHub API fallback: {reason}"
            except Exception as ex:
                if attempt < max_retries:
                    time.sleep(0.1 * (2 ** attempt))
                    continue
                else:
                    reason = f"Network timeout/error ({type(ex).__name__})"
                    return self._get_mock_commits(service), True, f"GitHub API fallback: {reason}"

        return self._get_mock_commits(service), True, "GitHub API fallback: max retries exceeded"

    def _get_mock_commits(self, service: str) -> List[Dict[str, Any]]:
        """Returns clearly labelled mock commits for the service."""
        return [
            {
                "sha": "a1b2c3d",
                "author": "DevOps Engineer [MOCK]",
                "message": f"[MOCK_GITHUB_COMMIT] chore({service}): bump dependency version and connection pool limits",
                "date": "2026-11-13T09:30:00Z",
                "source": "mock_fallback"
            },
            {
                "sha": "f9e8d7c",
                "author": "Core Platform [MOCK]",
                "message": f"[MOCK_GITHUB_COMMIT] feat({service}): update request handler retry timeout",
                "date": "2026-11-13T08:15:00Z",
                "source": "mock_fallback"
            }
        ]


# Global singleton
github_client = GitHubClient()

