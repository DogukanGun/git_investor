import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .collector import run_collection
from .db import get_session
from .models import Org, Repo, Snapshot, WatchItem
from .schemas import OrgOut, RefreshOut, RepoDetailOut, RepoListOut, RepoOut, SnapshotOut

log = logging.getLogger("gitinvest.api")
router = APIRouter(prefix="/api")

_SORTABLE = {
    "score": Repo.score,
    "stars": Repo.stars,
    "star_velocity": Repo.star_velocity,
    "contributors": Repo.contributors,
    "created_at": Repo.created_at,
    "funding_total": Repo.funding_total,
    "recent_velocity": Repo.recent_velocity,
    "acceleration": Repo.acceleration,
}

_refresh_lock = asyncio.Lock()


@router.get("/repos", response_model=RepoListOut)
def list_repos(
    db: Session = Depends(get_session),
    min_stars: int | None = None,
    max_stars: int | None = None,
    language: str | None = None,
    topic: str | None = None,
    company_only: bool = False,
    funded_only: bool = False,
    hot_only: bool = False,
    q: str | None = None,
    sort: str = Query(
        "score",
        pattern="^(score|stars|star_velocity|contributors|created_at|funding_total|recent_velocity|acceleration)$",
    ),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    stmt = select(Repo)
    if min_stars is not None:
        stmt = stmt.where(Repo.stars >= min_stars)
    if max_stars is not None:
        stmt = stmt.where(Repo.stars <= max_stars)
    if language:
        stmt = stmt.where(Repo.language == language)
    if topic:
        stmt = stmt.where(Repo.topics.contains(topic))
    if company_only:
        stmt = stmt.where(Repo.is_company_backed.is_(True))
    if funded_only:
        stmt = stmt.where(Repo.funding_total.is_not(None), Repo.funding_total > 0)
    if hot_only:
        stmt = stmt.where(Repo.is_hot.is_(True))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(Repo.full_name.ilike(like) | Repo.description.ilike(like))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    col = _SORTABLE[sort]
    stmt = stmt.order_by(col.asc() if order == "asc" else col.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    items = db.scalars(stmt).all()

    return RepoListOut(
        total=total,
        page=page,
        page_size=page_size,
        items=[RepoOut.model_validate(r) for r in items],
    )


@router.get("/languages", response_model=list[str])
def list_languages(db: Session = Depends(get_session)):
    rows = db.scalars(
        select(Repo.language).where(Repo.language.is_not(None)).distinct().order_by(Repo.language)
    ).all()
    return list(rows)


@router.get("/repos/{repo_id}", response_model=RepoDetailOut)
def get_repo(repo_id: int, db: Session = Depends(get_session)):
    repo = db.get(Repo, repo_id)
    if repo is None:
        raise HTTPException(404, "repo not found")
    out = RepoDetailOut.model_validate(repo)
    if repo.owner_type == "Organization":
        org = db.get(Org, repo.owner_login)
        if org is not None:
            out.org = OrgOut.model_validate(org)
    return out


@router.get("/repos/{repo_id}/history", response_model=list[SnapshotOut])
def get_history(repo_id: int, db: Session = Depends(get_session)):
    if db.get(Repo, repo_id) is None:
        raise HTTPException(404, "repo not found")
    snaps = db.scalars(
        select(Snapshot).where(Snapshot.repo_id == repo_id).order_by(Snapshot.captured_at)
    ).all()
    return [SnapshotOut.model_validate(s) for s in snaps]


@router.post("/refresh", response_model=RefreshOut)
async def refresh(
    min_stars: int | None = None,
    max_stars: int | None = None,
):
    if _refresh_lock.locked():
        return RefreshOut(status="already_running")
    asyncio.create_task(_run_refresh(min_stars, max_stars))
    return RefreshOut(status="started")


async def _run_refresh(min_stars: int | None, max_stars: int | None) -> None:
    async with _refresh_lock:
        try:
            summary = await run_collection(min_stars, max_stars)
            log.info("refresh complete: %s", summary)
        except Exception:  # noqa: BLE001 - background task must not crash silently
            log.exception("refresh failed")


@router.get("/watchlist", response_model=list[RepoOut])
def get_watchlist(db: Session = Depends(get_session)):
    repos = db.scalars(select(Repo).join(WatchItem, WatchItem.repo_id == Repo.id)).all()
    return [RepoOut.model_validate(r) for r in repos]


@router.post("/watchlist/{repo_id}", response_model=RefreshOut)
def add_watch(repo_id: int, db: Session = Depends(get_session)):
    if db.get(Repo, repo_id) is None:
        raise HTTPException(404, "repo not found")
    if db.get(WatchItem, repo_id) is None:
        db.add(WatchItem(repo_id=repo_id))
        db.commit()
    return RefreshOut(status="ok")


@router.delete("/watchlist/{repo_id}", response_model=RefreshOut)
def remove_watch(repo_id: int, db: Session = Depends(get_session)):
    item = db.get(WatchItem, repo_id)
    if item is not None:
        db.delete(item)
        db.commit()
    return RefreshOut(status="ok")
