from collections.abc import Iterator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from .config import settings
from .models import Base

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _add_missing_columns()


def _add_missing_columns() -> None:
    """Add columns introduced after a table was first created (SQLite dev DBs).

    create_all() never alters existing tables, so a pre-existing gitinvest.db
    would be missing the funding columns. This adds them idempotently.
    """
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue
            present = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                col_type = column.type.compile(dialect=engine.dialect)
                default = _scalar_default(column)
                if column.name not in present:
                    ddl = f'ALTER TABLE {table.name} ADD COLUMN "{column.name}" {col_type}'
                    if default is not None:
                        ddl += f" DEFAULT {default}"
                    conn.execute(text(ddl))
                if default is not None:
                    # Backfill any NULLs left by an earlier defaultless ADD COLUMN.
                    conn.execute(
                        text(f'UPDATE {table.name} SET "{column.name}" = {default} '
                             f'WHERE "{column.name}" IS NULL')
                    )


def _scalar_default(column) -> str | None:
    """Render a column's scalar Python default as SQL, or None if not applicable."""
    if column.nullable or column.default is None or not column.default.is_scalar:
        return None
    val = column.default.arg
    if isinstance(val, bool):
        return "1" if val else "0"
    if isinstance(val, (int, float)):
        return str(val)
    return None


def get_session() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
