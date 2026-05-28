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

    # Discovery defaults (the "famous but not most famous" band).
    default_min_stars: int = 500
    default_max_stars: int = 15000

    # How far back to look for "recently created" repos, in days.
    created_lookback_days: int = 730  # ~2 years
    # Width of each created-date window when paging around the 1000-result cap.
    date_window_days: int = 30
    # Star bands used to subdivide queries so each stays under the 1000 cap.
    star_bands: list[int] = [500, 1000, 2000, 4000, 8000, 15000]
    # Cap on repos enriched per collection run (keeps rate-limit usage bounded).
    enrich_limit: int = 150

    # Daily refresh hour (24h, server local time). None disables the scheduler.
    refresh_hour: int | None = 4

    # Composite emerging-score weights (need not sum to 1; normalized internally).
    w_velocity: float = 0.40
    w_recency: float = 0.15
    w_contributors: float = 0.15
    w_company: float = 0.10
    w_funding: float = 0.20


settings = Settings()
