import asyncio
import json
import sqlite3
from pathlib import Path
from typing import Any, Protocol
from .models import WorkflowState


class WorkflowSession(Protocol):
    session_id: str

    async def load(self) -> WorkflowState | None: ...

    async def save(
        self,
        state: WorkflowState,
        event: str,
        data: dict[str, Any] | None = None,
    ) -> None: ...

    async def clear(self) -> None: ...


class SQLiteWorkflowSession:
    """Store one workflow snapshot and its ordered events in SQLite."""

    def __init__(self, session_id: str, db_path: str | Path) -> None:
        self.session_id = session_id
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_state (
                    session_id TEXT PRIMARY KEY,
                    state_json TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    event TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES workflow_state (session_id)
                        ON DELETE CASCADE
                )
                """
            )

    async def load(self) -> WorkflowState | None:
        def load_sync() -> WorkflowState | None:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT state_json FROM workflow_state WHERE session_id = ?",
                    (self.session_id,),
                ).fetchone()
            return WorkflowState.model_validate_json(row[0]) if row else None

        return await asyncio.to_thread(load_sync)

    async def save(
        self,
        state: WorkflowState,
        event: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        def save_sync() -> None:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO workflow_state (session_id, state_json)
                    VALUES (?, ?)
                    ON CONFLICT(session_id) DO UPDATE SET
                        state_json = excluded.state_json,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (self.session_id, state.model_dump_json()),
                )
                connection.execute(
                    """
                    INSERT INTO workflow_events (session_id, event, data_json)
                    VALUES (?, ?, ?)
                    """,
                    (
                        self.session_id,
                        event,
                        json.dumps(data or {}, ensure_ascii=False),
                    ),
                )

        await asyncio.to_thread(save_sync)

    async def clear(self) -> None:
        def clear_sync() -> None:
            with self._connect() as connection:
                connection.execute(
                    "DELETE FROM workflow_state WHERE session_id = ?",
                    (self.session_id,),
                )

        await asyncio.to_thread(clear_sync)
