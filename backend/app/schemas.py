from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


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
    stars_7d: int | None = None
    stars_30d: int | None = None
    recent_velocity: float = 0.0
    acceleration: float = 0.0
    is_hot: bool = False
    is_company_backed: bool = False

    # Legacy rows (columns added by migration) may hold NULL; coalesce to defaults.
    @field_validator("recent_velocity", "acceleration", "star_velocity", "contributor_velocity", mode="before")
    @classmethod
    def _none_to_zero(cls, v: float | None) -> float:
        return 0.0 if v is None else v

    @field_validator("is_hot", "is_company_backed", mode="before")
    @classmethod
    def _none_to_false(cls, v: bool | None) -> bool:
        return False if v is None else v
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
