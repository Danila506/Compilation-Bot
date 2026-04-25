from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.engine import make_url

from app.config import ensure_runtime_dirs, settings

ensure_runtime_dirs()


def _database_url() -> str:
    raw_url = settings.database_url
    if raw_url.startswith("postgres://"):
        raw_url = raw_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif raw_url.startswith("postgresql://"):
        raw_url = raw_url.replace("postgresql://", "postgresql+psycopg://", 1)

    if raw_url.startswith("postgresql+psycopg://"):
        url = make_url(raw_url)
        query = dict(url.query)
        query.setdefault("sslmode", "require")
        return url.set(query=query).render_as_string(hide_password=False)

    return raw_url


def database_url_info() -> dict:
    url = make_url(_database_url())
    return {
        "driver": url.drivername,
        "username": url.username or "",
        "host": url.host or "",
        "port": url.port,
        "database": url.database or "",
        "sslmode": url.query.get("sslmode", ""),
    }


engine = create_engine(_database_url(), future=True, echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


def get_session() -> Session:
    return SessionLocal()
