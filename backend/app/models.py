from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Org(Base):
    __tablename__ = "orgs"

    login: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    website: Mapped[str | None] = mapped_column(String, nullable=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    is_company: Mapped[bool] = mapped_column(default=False)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Funding (from SEC EDGAR Form D filings).
    funding_total: Mapped[int | None] = mapped_column(Integer, nullable=True)  # largest disclosed offering, USD
    last_funding_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    funding_source: Mapped[str | None] = mapped_column(String, nullable=True)
    funding_url: Mapped[str | None] = mapped_column(String, nullable=True)
    funding_fetched_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Repo(Base):
    __tablename__ = "repos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # GitHub repo id
    full_name: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String)
    owner_login: Mapped[str] = mapped_column(String, index=True)
    owner_type: Mapped[str] = mapped_column(String)  # "User" | "Organization"
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    html_url: Mapped[str] = mapped_column(String)
    homepage: Mapped[str | None] = mapped_column(String, nullable=True)
    language: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    topics: Mapped[str | None] = mapped_column(Text, nullable=True)  # comma-separated

    stars: Mapped[int] = mapped_column(Integer, default=0, index=True)
    forks: Mapped[int] = mapped_column(Integer, default=0)
    contributors: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime)
    pushed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Derived signals.
    star_velocity: Mapped[float] = mapped_column(Float, default=0.0)  # lifetime stars/day
    contributor_velocity: Mapped[float] = mapped_column(Float, default=0.0)  # contributors/day
    # Recent momentum, read live from stargazer timestamps.
    stars_7d: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stars_30d: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recent_velocity: Mapped[float] = mapped_column(Float, default=0.0)  # stars/day over 30d
    acceleration: Mapped[float] = mapped_column(Float, default=0.0)  # recent rate / lifetime rate
    is_hot: Mapped[bool] = mapped_column(default=False)  # 7d rate spiking
    trend_checked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_company_backed: Mapped[bool] = mapped_column(default=False)
    # Denormalized from the owning org for list display + scoring.
    funding_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_funding_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    score: Mapped[float] = mapped_column(Float, default=0.0, index=True)

    first_seen: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_updated: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    snapshots: Mapped[list["Snapshot"]] = relationship(
        back_populates="repo", cascade="all, delete-orphan", order_by="Snapshot.captured_at"
    )


class Snapshot(Base):
    __tablename__ = "snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repo_id: Mapped[int] = mapped_column(ForeignKey("repos.id", ondelete="CASCADE"), index=True)
    stars: Mapped[int] = mapped_column(Integer)
    forks: Mapped[int] = mapped_column(Integer)
    contributors: Mapped[int | None] = mapped_column(Integer, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime, index=True)

    repo: Mapped["Repo"] = relationship(back_populates="snapshots")


class WatchItem(Base):
    __tablename__ = "watchlist"

    repo_id: Mapped[int] = mapped_column(ForeignKey("repos.id", ondelete="CASCADE"), primary_key=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
