from agents import SQLiteSession

from settings import settings


def create_session() -> SQLiteSession:
    return SQLiteSession(
        session_id=settings.agent_session_id,
        db_path=settings.conversation_database_path,
    )
