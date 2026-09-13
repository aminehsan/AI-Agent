from agents import SQLiteSession
from settings import get_session_database_path, settings


def create_session() -> SQLiteSession:
    return SQLiteSession(
        session_id=settings.session_id,
        db_path=get_session_database_path(),
    )
