import asyncio
import sqlite3
from pathlib import Path
from .models import WorkflowState


class SQLiteWorkflowSession:
    """Store one workflow snapshot per agent session in SQLite."""

    def __init__(self, session_id: str, db_path: str | Path) -> None:
        self.session_id = session_id
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, timeout=10)

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
    async def save(self, state: WorkflowState) -> None:
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

        await asyncio.to_thread(save_sync)

    async def clear(self) -> None:
        def clear_sync() -> None:
            with self._connect() as connection:
                connection.execute(
                    "DELETE FROM workflow_state WHERE session_id = ?",
                    (self.session_id,),
                )

        await asyncio.to_thread(clear_sync)
