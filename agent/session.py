from agents import SQLiteSession, Session
from settings import settings


def create_session() -> Session:
    return SQLiteSession(
        session_id=settings.session_id,
        db_path=settings.conversation_database_path,
    )
