from agents import OpenAIResponsesCompactionSession, SQLiteSession

from model.client import create_client
from settings import settings


def create_session() -> SQLiteSession:
    return SQLiteSession(
        session_id=settings.agent_session_id,
        db_path=settings.conversation_database_path,
    )


def create_compaction_session() -> OpenAIResponsesCompactionSession:
    return OpenAIResponsesCompactionSession(
        session_id=settings.agent_session_id,
        underlying_session=create_session(),
        client=create_client(),
        model=settings.model_name,
        should_trigger_compaction=lambda _: True,
    )
