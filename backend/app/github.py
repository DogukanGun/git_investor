import asyncio
import logging
import re
from typing import Any

import httpx

from .config import settings

log = logging.getLogger("gitinvest.github")

API_BASE = "https://api.github.com"
_LAST_PAGE_RE = re.compile(r'[?&]page=(\d+)>;\s*rel="last"')


class GitHubError(Exception):
    pass


class GitHubClient:
    """Async GitHub API client with auth, pagination, and rate-limit backoff."""

    def __init__(self, token: str | None = None):
        self.token = token if token is not None else settings.github_token
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "gitinvest",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        self._client = httpx.AsyncClient(base_url=API_BASE, headers=headers, timeout=30.0)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "GitHubClient":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """Single request with retry on rate limit / transient errors."""
        for attempt in range(5):
            resp = await self._client.request(method, path, **kwargs)

            if resp.status_code in (403, 429):
                # Rate limited. Honor Retry-After or X-RateLimit-Reset.
                wait = _rate_limit_wait(resp)
                if wait is not None:
                    log.warning("Rate limited on %s; sleeping %.0fs", path, wait)
                    await asyncio.sleep(min(wait, 90))
                    continue

            if resp.status_code >= 500:
                await asyncio.sleep(2 ** attempt)
                continue

            return resp

        return resp  # final attempt's response (caller inspects status)

    async def search_repos(
        self, query: str, sort: str = "stars", order: str = "desc", page: int = 1, per_page: int = 100
    ) -> dict[str, Any]:
        resp = await self._request(
            "GET",
            "/search/repositories",
            params={"q": query, "sort": sort, "order": order, "page": page, "per_page": per_page},
        )
        if resp.status_code != 200:
            raise GitHubError(f"search failed ({resp.status_code}): {resp.text[:200]}")
        return resp.json()

    async def get_repo(self, full_name: str) -> dict[str, Any] | None:
        resp = await self._request("GET", f"/repos/{full_name}")
        if resp.status_code == 404:
            return None
        if resp.status_code != 200:
            raise GitHubError(f"get_repo failed ({resp.status_code}): {resp.text[:200]}")
        return resp.json()

    async def get_org(self, login: str) -> dict[str, Any] | None:
        resp = await self._request("GET", f"/orgs/{login}")
        if resp.status_code == 404:
            return None
        if resp.status_code != 200:
            raise GitHubError(f"get_org failed ({resp.status_code}): {resp.text[:200]}")
        return resp.json()

    async def get_contributor_count(self, full_name: str) -> int | None:
        """Cheaply estimate contributor count via the Link header's last page.

        Requests 1 contributor per page; the 'last' page number equals the total
        count. Falls back to counting the returned page when there's no Link header.
        """
        resp = await self._request(
            "GET", f"/repos/{full_name}/contributors", params={"per_page": 1, "anon": "true"}
        )
        if resp.status_code != 200:
            return None
        link = resp.headers.get("Link", "")
        match = _LAST_PAGE_RE.search(link)
        if match:
            return int(match.group(1))
        # No pagination -> 0 or 1 contributors.
        data = resp.json()
        return len(data) if isinstance(data, list) else None


def _rate_limit_wait(resp: httpx.Response) -> float | None:
    retry_after = resp.headers.get("Retry-After")
    if retry_after and retry_after.isdigit():
        return float(retry_after)
    remaining = resp.headers.get("X-RateLimit-Remaining")
    reset = resp.headers.get("X-RateLimit-Reset")
    if remaining == "0" and reset and reset.isdigit():
        import time

        return max(0.0, float(reset) - time.time()) + 1.0
    # Secondary rate limit without headers — short backoff.
    if "secondary rate limit" in resp.text.lower():
        return 30.0
    return None
