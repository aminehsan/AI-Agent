from agents import SQLiteSession
from .settings import settings
from .project import get_session_database_path


def create_session() -> SQLiteSession:
    return SQLiteSession(
        session_id=settings.session_id,
        db_path=get_session_database_path(),
    )
