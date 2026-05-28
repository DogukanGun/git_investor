from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OrgOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    login: str
    name: str | None = None
    website: str | None = None
    location: str | None = None
    funding_total: int | None = None
    last_funding_at: datetime | None = None
    funding_source: str | None = None
    funding_url: str | None = None


class RepoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    name: str
    owner_login: str
    owner_type: str
    description: str | None = None
    html_url: str
    homepage: str | None = None
    language: str | None = None
    topics: str | None = None
    stars: int
    forks: int
    contributors: int | None = None
    created_at: datetime
    pushed_at: datetime | None = None
    star_velocity: float
    contributor_velocity: float
    is_company_backed: bool
    funding_total: int | None = None
    last_funding_at: datetime | None = None
    score: float
    last_updated: datetime


class RepoDetailOut(RepoOut):
    org: OrgOut | None = None


class SnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    stars: int
    forks: int
    contributors: int | None = None
    captured_at: datetime


class RepoListOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[RepoOut]


class RefreshOut(BaseModel):
    status: str
    detail: str | None = None
