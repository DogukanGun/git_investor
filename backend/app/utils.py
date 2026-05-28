from datetime import datetime, timezone


def parse_gh_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    # GitHub timestamps look like "2023-01-02T03:04:05Z".
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def days_between(later: datetime, earlier: datetime) -> float:
    return max((later - earlier).total_seconds() / 86400.0, 0.0)
