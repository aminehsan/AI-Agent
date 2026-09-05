from agents import SQLiteSession
from .settings import settings


def create_session() -> SQLiteSession:
    return SQLiteSession(
        session_id=settings.session_id,
        db_path=settings.session_db_path,
    )
