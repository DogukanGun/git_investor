from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    github_token: str = ""
    database_url: str = "sqlite:///./gitinvest.db"

    # SEC EDGAR is the (free) funding source. SEC's archive REQUIRES a
    # User-Agent containing a contact email, else it returns 403. Override
    # SEC_USER_AGENT with your own contact.
    sec_user_agent: str = "gitinvest funding scout dogukangundogan5@gmail.com"
    # Past this much raised, a company is treated as "already big" and the
    # early-stage funding boost decays toward zero.
    funding_big_ref: float = 50_000_000.0

    # Discovery defaults — catch repos early (low floor; momentum ranking
    # filters the extra noise).
    default_min_stars: int = 100
    default_max_stars: int = 15000

    # How far back to look for "recently created" repos, in days.
    created_lookback_days: int = 730  # ~2 years
    # Width of each created-date window when paging around the 1000-result cap.
    date_window_days: int = 30
    # Star bands used to subdivide queries so each stays under the 1000 cap.
    star_bands: list[int] = [100, 250, 500, 1000, 2000, 4000, 8000, 15000]
    # Cap on repos enriched per collection run (keeps rate-limit usage bounded).
    enrich_limit: int = 200

    # Recent-momentum tuning. We read each repo's most recent stars via the
    # stargazers `starred_at` timestamps (trailing pages) to measure attention
    # *now* rather than lifetime averages.
    recent_star_pages: int = 6  # trailing pages of 100 -> ~600 most-recent stars
    recent_velocity_ref: float = 8.0  # stars/day (30d) mapping to a strong score
    acceleration_ref: float = 2.0  # recent-rate / lifetime-rate for a strong score
    hot_7d_floor: float = 5.0  # min stars/day (7d) to be eligible for "hot"
    hot_multiple: float = 2.0  # 7d rate must exceed this x the 30d rate to be "hot"

    # Daily refresh hour (24h, server local time). None disables the scheduler.
    refresh_hour: int | None = 4

    # Composite emerging-score weights (need not sum to 1; normalized internally).
    w_recent_velocity: float = 0.35
    w_acceleration: float = 0.20
    w_recency: float = 0.10
    w_contributors: float = 0.10
    w_company: float = 0.10
    w_funding: float = 0.15


settings = Settings()
