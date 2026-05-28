import asyncio
import logging
import re
from datetime import datetime
from typing import Any

import httpx

from .config import settings
from .utils import parse_gh_datetime

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

    async def get_recent_star_dates(self, full_name: str) -> list[datetime] | None:
        """Return the most-recent stars' timestamps to measure current momentum.

        Stargazers are returned oldest-first; with the star+json media type each
        entry carries `starred_at`. We jump to the last page (Link rel="last")
        and read the trailing `recent_star_pages` pages — i.e. the newest stars.
        Returns None on failure so callers fall back to lifetime averages.
        """
        star_accept = {"Accept": "application/vnd.github.star+json"}
        first = await self._request(
            "GET",
            f"/repos/{full_name}/stargazers",
            params={"per_page": 100, "page": 1},
            headers=star_accept,
        )
        if first.status_code != 200:
            return None

        last_page = 1
        match = _LAST_PAGE_RE.search(first.headers.get("Link", ""))
        if match:
            last_page = int(match.group(1))

        # Single page: the dates are already in hand.
        if last_page == 1:
            return _extract_starred_at(first.json())

        dates: list[datetime] = []
        start = max(2, last_page - settings.recent_star_pages + 1)
        # Include page 1's data only if it falls inside our trailing window.
        if start <= 1:
            dates.extend(_extract_starred_at(first.json()))
        for page in range(start, last_page + 1):
            resp = await self._request(
                "GET",
                f"/repos/{full_name}/stargazers",
                params={"per_page": 100, "page": page},
                headers=star_accept,
            )
            if resp.status_code != 200:
                continue
            dates.extend(_extract_starred_at(resp.json()))
        return dates


def _extract_starred_at(items: Any) -> list[datetime]:
    if not isinstance(items, list):
        return []
    out: list[datetime] = []
    for it in items:
        ts = parse_gh_datetime(it.get("starred_at")) if isinstance(it, dict) else None
        if ts is not None:
            out.append(ts)
    return out


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
