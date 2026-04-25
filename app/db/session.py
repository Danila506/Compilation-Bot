from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import ensure_runtime_dirs, settings

ensure_runtime_dirs()
engine = create_engine(settings.database_url, future=True, echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


def get_session() -> Session:
    return SessionLocal()
