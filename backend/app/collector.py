import logging
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .db import SessionLocal
from .funding import FundingClient
from .github import GitHubClient
from .models import Org, Repo, Snapshot
from .scoring import compute_score, lifetime_velocity
from .utils import days_between, parse_gh_datetime, utcnow

log = logging.getLogger("gitinvest.collector")

SEARCH_PAGE_LIMIT = 10  # 10 pages * 100 = 1000-result API cap


def _star_band_queries(min_stars: int, max_stars: int) -> list[str]:
    """Subdivide the star range into bands so each search stays under 1000 results."""
    edges = [b for b in settings.star_bands if min_stars <= b <= max_stars]
    edges = sorted(set([min_stars, *edges, max_stars]))
    bands: list[str] = []
    for low, high in zip(edges, edges[1:]):
        bands.append(f"stars:{low}..{high}")
    if not bands:
        bands.append(f"stars:{min_stars}..{max_stars}")
    return bands


def _date_windows(lookback_days: int, window_days: int) -> list[str]:
    """Created-date windows (newest first) to page around the 1000-result cap."""
    now = utcnow().date()
    windows: list[str] = []
    start = now - timedelta(days=lookback_days)
    cursor = now
    while cursor > start:
        lo = max(start, cursor - timedelta(days=window_days))
        windows.append(f"created:{lo.isoformat()}..{cursor.isoformat()}")
        cursor = lo - timedelta(days=1)
    return windows


async def discover(
    client: GitHubClient,
    db: Session,
    min_stars: int | None = None,
    max_stars: int | None = None,
) -> int:
    """Enumerate candidate repos across (date window x star band) and upsert them."""
    min_stars = min_stars if min_stars is not None else settings.default_min_stars
    max_stars = max_stars if max_stars is not None else settings.default_max_stars

    seen = 0
    for window in _date_windows(settings.created_lookback_days, settings.date_window_days):
        for band in _star_band_queries(min_stars, max_stars):
            query = f"{band} {window} is:public sort:stars"
            page = 1
            while page <= SEARCH_PAGE_LIMIT:
                result = await client.search_repos(query, page=page)
                items = result.get("items", [])
                if not items:
                    break
                for item in items:
                    _upsert_repo(db, item)
                    seen += 1
                db.commit()
                if len(items) < 100:
                    break
                page += 1
    return seen


def _upsert_repo(db: Session, item: dict) -> Repo:
    repo = db.get(Repo, item["id"])
    owner = item.get("owner") or {}
    topics = ",".join(item.get("topics", []) or [])
    if repo is None:
        repo = Repo(id=item["id"])
        db.add(repo)
    repo.full_name = item["full_name"]
    repo.name = item["name"]
    repo.owner_login = owner.get("login", "")
    repo.owner_type = owner.get("type", "")
    repo.description = item.get("description")
    repo.html_url = item["html_url"]
    repo.homepage = item.get("homepage")
    repo.language = item.get("language")
    repo.topics = topics
    repo.stars = item.get("stargazers_count", 0)
    repo.forks = item.get("forks_count", 0)
    repo.created_at = parse_gh_datetime(item.get("created_at")) or utcnow()
    repo.pushed_at = parse_gh_datetime(item.get("pushed_at"))
    repo.last_updated = utcnow()
    # Bootstrap a provisional score so every discovered repo ranks immediately
    # (refined later in enrich() once recent momentum is measured).
    repo.score = compute_score(repo)
    return repo


def _record_snapshot_and_velocity(db: Session, repo: Repo) -> None:
    """Write a snapshot and recompute velocity from prior history (or bootstrap)."""
    now = utcnow()
    prev = db.scalars(
        select(Snapshot).where(Snapshot.repo_id == repo.id).order_by(Snapshot.captured_at.desc())
    ).first()

    if prev is not None:
        dt = days_between(now, prev.captured_at)
        if dt >= 0.5:  # avoid noisy intra-day deltas
            repo.star_velocity = max((repo.stars - prev.stars) / dt, 0.0)
            if repo.contributors is not None and prev.contributors is not None:
                repo.contributor_velocity = max((repo.contributors - prev.contributors) / dt, 0.0)
    else:
        # Bootstrap from lifetime averages until real history accumulates.
        age = days_between(now, repo.created_at) or 1.0
        repo.star_velocity = repo.stars / age
        if repo.contributors is not None:
            repo.contributor_velocity = repo.contributors / age

    db.add(
        Snapshot(
            repo_id=repo.id,
            stars=repo.stars,
            forks=repo.forks,
            contributors=repo.contributors,
            captured_at=now,
        )
    )


# GitHub only exposes the first 40,000 stargazers, so for repos past that the
# "last page" is an old star, not a recent one — recent counts would be wrong.
STARGAZER_CAP = 40_000


async def _compute_trend(client: GitHubClient, repo: Repo) -> None:
    """Measure current momentum from the repo's most recent stargazer timestamps."""
    repo.trend_checked_at = utcnow()
    if repo.stars > STARGAZER_CAP:
        # Beyond the API cap; leave momentum to the lifetime fallback in scoring.
        return
    dates = await client.get_recent_star_dates(repo.full_name)
    if dates is None:
        return
    now = utcnow()
    repo.stars_7d = sum(1 for d in dates if days_between(now, d) <= 7)
    repo.stars_30d = sum(1 for d in dates if days_between(now, d) <= 30)
    repo.recent_velocity = repo.stars_30d / 30.0
    rate_7d = repo.stars_7d / 7.0
    lifetime = lifetime_velocity(repo) or 1e-6
    repo.acceleration = repo.recent_velocity / lifetime
    repo.is_hot = rate_7d >= max(settings.hot_7d_floor, settings.hot_multiple * repo.recent_velocity)


async def enrich(
    client: GitHubClient,
    db: Session,
    funding_client: FundingClient,
    limit: int | None = None,
) -> int:
    """Measure momentum + contributor/org/funding signals for promising repos."""
    limit = limit if limit is not None else settings.enrich_limit
    # Never-checked repos first (NULLs sort first in SQLite), then by provisional
    # score — so the strongest candidates get measured, round-robining across runs.
    repos = db.scalars(
        select(Repo).order_by(Repo.trend_checked_at.asc(), Repo.score.desc()).limit(limit)
    ).all()

    enriched = 0
    for repo in repos:
        await _compute_trend(client, repo)

        count = await client.get_contributor_count(repo.full_name)
        if count is not None:
            repo.contributors = count

        if repo.owner_type == "Organization":
            await _enrich_org(client, funding_client, db, repo)
            _apply_funding(db, repo)

        repo.is_company_backed = _is_company_backed(db, repo)
        _record_snapshot_and_velocity(db, repo)
        repo.score = compute_score(repo)
        enriched += 1
        db.commit()
    return enriched


async def _enrich_org(
    client: GitHubClient, funding_client: FundingClient, db: Session, repo: Repo
) -> None:
    org = db.get(Org, repo.owner_login)
    # Refetch at most once per week; orgs change slowly.
    fresh = org is not None and org.fetched_at is not None and days_between(utcnow(), org.fetched_at) < 7
    if not fresh:
        data = await client.get_org(repo.owner_login)
        if data is None:
            return
        if org is None:
            org = Org(login=repo.owner_login)
            db.add(org)
        org.name = data.get("name")
        org.website = data.get("blog") or None
        org.email = data.get("email")
        org.location = data.get("location")
        org.is_company = bool(data.get("blog"))
        org.fetched_at = utcnow()

    await _enrich_funding(funding_client, org)


async def _enrich_funding(funding_client: FundingClient, org: Org) -> None:
    # Refetch funding at most once per week.
    if org.funding_fetched_at is not None and days_between(utcnow(), org.funding_fetched_at) < 7:
        return
    info = await funding_client.lookup(org.name or org.login)
    org.funding_fetched_at = utcnow()
    if info is None:
        return
    org.funding_total = info.total or None
    org.last_funding_at = info.last_at
    org.funding_source = info.source
    org.funding_url = info.url


def _apply_funding(db: Session, repo: Repo) -> None:
    org = db.get(Org, repo.owner_login)
    if org is not None:
        repo.funding_total = org.funding_total
        repo.last_funding_at = org.last_funding_at


def _is_company_backed(db: Session, repo: Repo) -> bool:
    if repo.owner_type != "Organization":
        return False
    org = db.get(Org, repo.owner_login)
    if org is not None and (org.website or org.is_company):
        return True
    # Fall back to the repo's own homepage as a weak signal.
    return bool(repo.homepage)


async def run_collection(min_stars: int | None = None, max_stars: int | None = None) -> dict:
    """Full pipeline: discover -> enrich -> snapshot -> score. Returns a summary."""
    db = SessionLocal()
    async with GitHubClient() as client, FundingClient() as funding_client:
        try:
            discovered = await discover(client, db, min_stars, max_stars)
            enriched = await enrich(client, db, funding_client)
            log.info("collection done: discovered=%d enriched=%d", discovered, enriched)
            return {"discovered": discovered, "enriched": enriched}
        finally:
            db.close()
