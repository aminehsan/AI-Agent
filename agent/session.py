import json
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any
from sqlalchemy import event
from sqlalchemy.engine import Engine, URL
from sqlmodel import Field, Relationship, Session, SQLModel, create_engine, select
from settings import settings


def _utc_now() -> datetime:
    return datetime.now(UTC)


class ConversationRecord(SQLModel, table=True):
    __tablename__ = "agent_sessions"

    session_id: str = Field(primary_key=True)
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

    messages: list["ConversationMessageRecord"] = Relationship(
        back_populates="conversation",
        cascade_delete=True,
    )


class ConversationMessageRecord(SQLModel, table=True):
    __tablename__ = "agent_messages"

    id: int | None = Field(default=None, primary_key=True)
    session_id: str = Field(
        foreign_key="agent_sessions.session_id",
        ondelete="CASCADE",
        index=True,
    )
    message_data: str
    created_at: datetime = Field(default_factory=_utc_now)

    conversation: ConversationRecord = Relationship(back_populates="messages")


@lru_cache(maxsize=16)
def _create_engine(database_path: Path) -> Engine:
    engine = create_engine(
        URL.create("sqlite", database=str(database_path)),
        connect_args={"timeout": 10},
    )

    @event.listens_for(engine, "connect")
    def configure_sqlite(connection: Any, _record: Any) -> None:
        cursor = connection.cursor()
        try:
            cursor.execute("PRAGMA busy_timeout = 10000")
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute("PRAGMA journal_mode = WAL")
        finally:
            cursor.close()

    SQLModel.metadata.create_all(
        engine,
        tables=[
            ConversationRecord.__table__,
            ConversationMessageRecord.__table__,
        ],
    )
    return engine


class ConversationSession:
    """Persist user and assistant messages with SQLModel."""

    def __init__(self, session_id: str, db_path: str | Path) -> None:
        self.session_id = session_id
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = _create_engine(self.db_path.resolve())

    def get_messages(self, limit: int = 12) -> list[dict[str, Any]]:
        statement = (
            select(ConversationMessageRecord)
            .where(ConversationMessageRecord.session_id == self.session_id)
            .order_by(ConversationMessageRecord.id.desc())
            .limit(limit)
        )
        with Session(self.engine) as session:
            messages = list(session.exec(statement).all())
        messages.reverse()
        return [json.loads(message.message_data) for message in messages]

    def add_exchange(self, user_input: str, answer: str) -> None:
        messages = [
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": answer},
        ]
        with Session(self.engine) as session:
            with session.begin():
                conversation = session.get(ConversationRecord, self.session_id)
                if conversation is None:
                    conversation = ConversationRecord(session_id=self.session_id)
                else:
                    conversation.updated_at = _utc_now()
                session.add(conversation)
                session.add_all(
                    [
                        ConversationMessageRecord(
                            session_id=self.session_id,
                            message_data=json.dumps(message, ensure_ascii=False),
                        )
                        for message in messages
                    ]
                )


def create_session() -> ConversationSession:
    return ConversationSession(
        session_id=settings.session_id,
        db_path=settings.conversation_database_path,
    )
