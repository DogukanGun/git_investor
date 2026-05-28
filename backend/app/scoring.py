import math

from .config import settings
from .models import Repo
from .utils import days_between, utcnow

# Reference points for squashing raw signals into a 0..1 range.
_VELOCITY_REF = 20.0  # stars/day that maps to a strong score
_CONTRIB_VELOCITY_REF = 0.2  # contributors/day that maps to a strong score
_RECENCY_HALFLIFE_DAYS = 365.0  # age at which recency score halves


def _squash(value: float, ref: float) -> float:
    """Map a non-negative value to 0..1 with diminishing returns."""
    if value <= 0:
        return 0.0
    return 1.0 - math.exp(-value / ref)


def recency_score(repo: Repo) -> float:
    age_days = days_between(utcnow(), repo.created_at)
    return 0.5 ** (age_days / _RECENCY_HALFLIFE_DAYS)


def funding_score(repo: Repo) -> float:
    """Favor venture-backed-but-still-early companies.

    Having raised is a positive validation signal, but the boost decays as the
    total raised grows past funding_big_ref — a company that's already raised
    big is past the "invest before they get big" window.
    """
    total = repo.funding_total or 0
    if total <= 0:
        return 0.0
    return math.exp(-total / settings.funding_big_ref)


def compute_score(repo: Repo) -> float:
    """Composite emerging score in 0..1, blending the signals."""
    velocity = _squash(repo.star_velocity, _VELOCITY_REF)
    recency = recency_score(repo)
    contributors = _squash(repo.contributor_velocity, _CONTRIB_VELOCITY_REF)
    company = 1.0 if repo.is_company_backed else 0.0
    funding = funding_score(repo)

    weights = [
        settings.w_velocity,
        settings.w_recency,
        settings.w_contributors,
        settings.w_company,
        settings.w_funding,
    ]
    signals = [velocity, recency, contributors, company, funding]
    total_w = sum(weights) or 1.0
    return sum(w * s for w, s in zip(weights, signals)) / total_w
