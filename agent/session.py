import json
import sqlite3
from typing import Any
from pathlib import Path
from settings import get_session_database_path, settings


class ConversationSession:
    """Store user and assistant messages for one session."""

    def __init__(self, session_id: str, db_path: str | Path) -> None:
        self.session_id = session_id
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    message_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES agent_sessions (session_id)
                        ON DELETE CASCADE
                )
                """
            )

    def get_messages(self, limit: int = 12) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT message_data
                FROM (
                    SELECT id, message_data
                    FROM agent_messages
                    WHERE session_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                )
                ORDER BY id
                """,
                (self.session_id, limit),
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def add_exchange(self, user_input: str, answer: str) -> None:
        messages = [
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": answer},
        ]
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO agent_sessions (session_id)
                VALUES (?)
                ON CONFLICT(session_id) DO UPDATE SET
                    updated_at = CURRENT_TIMESTAMP
                """,
                (self.session_id,),
            )
            connection.executemany(
                """
                INSERT INTO agent_messages (session_id, message_data)
                VALUES (?, ?)
                """,
                [
                    (self.session_id, json.dumps(message, ensure_ascii=False))
                    for message in messages
                ],
            )


def create_session() -> ConversationSession:
    return ConversationSession(
        session_id=settings.session_id,
        db_path=get_session_database_path(),
    )
