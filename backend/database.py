import os
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@localhost:5432/sibs",
)

engine = None
SessionLocal: sessionmaker | None = None
_engine_error: Exception | None = None

try:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except ModuleNotFoundError as exc:
    _engine_error = exc
except Exception as exc:  # noqa: BLE001
    _engine_error = exc

# Base model
class Base(DeclarativeBase):
    pass

# context manager to get a database session
def get_db() -> Generator[Session, None, None]:
    if SessionLocal is None:
        raise RuntimeError(
            "Database session factory is unavailable. "
            "Check that the required database driver is installed "
            "and DATABASE_URL is correctly configured."
        ) from _engine_error

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

