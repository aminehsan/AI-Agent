from functools import lru_cache
from pathlib import Path
from typing import Any
from sqlalchemy import event
from sqlalchemy.engine import Engine, URL
from sqlmodel import Session, SQLModel, create_engine
from .models import (
    WorkflowCriterionRecord,
    WorkflowEvidenceRecord,
    WorkflowRecord,
    WorkflowState,
    WorkflowStepRecord,
    utc_now,
)


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
            WorkflowRecord.__table__,
            WorkflowCriterionRecord.__table__,
            WorkflowStepRecord.__table__,
            WorkflowEvidenceRecord.__table__,
        ],
    )
    return engine


class SQLiteWorkflowSession:
    """Persist one normalized workflow per agent session with SQLModel."""

    def __init__(self, session_id: str, db_path: str | Path) -> None:
        self.session_id = session_id
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = _create_engine(self.db_path.resolve())

    def save(self, state: WorkflowState) -> None:
        with Session(self.engine) as session:
            with session.begin():
                existing = session.get(WorkflowRecord, self.session_id)
                created_at = existing.created_at if existing is not None else utc_now()
                if existing is not None:
                    session.delete(existing)
                    session.flush()

                workflow = WorkflowRecord(
                    session_id=self.session_id,
                    request=state.request,
                    goal=state.goal,
                    status=state.status,
                    created_at=created_at,
                    updated_at=utc_now(),
                    criteria=[
                        WorkflowCriterionRecord(
                            workflow_session_id=self.session_id,
                            position=position,
                            value=value,
                        )
                        for position, value in enumerate(
                            state.success_criteria,
                            start=1,
                        )
                    ],
                    steps=[
                        WorkflowStepRecord(
                            workflow_session_id=self.session_id,
                            number=step.number,
                            task=step.task,
                            status=step.status,
                            summary=step.summary,
                            evidence=[
                                WorkflowEvidenceRecord(
                                    position=position,
                                    value=value,
                                )
                                for position, value in enumerate(
                                    step.evidence,
                                    start=1,
                                )
                            ],
                        )
                        for step in state.steps
                    ],
                )
                session.add(workflow)

    def clear(self) -> None:
        with Session(self.engine) as session:
            with session.begin():
                workflow = session.get(WorkflowRecord, self.session_id)
                if workflow is not None:
                    session.delete(workflow)
