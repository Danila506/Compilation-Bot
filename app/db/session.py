from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import ensure_runtime_dirs, settings

ensure_runtime_dirs()


def _database_url() -> str:
    if settings.database_url.startswith("postgresql://"):
        return settings.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return settings.database_url


engine = create_engine(_database_url(), future=True, echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


def get_session() -> Session:
    return SessionLocal()
