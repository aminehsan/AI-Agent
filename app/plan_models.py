from uuid import uuid4
from enum import StrEnum
from datetime import UTC, datetime
from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel


def new_id() -> str:
    return uuid4().hex


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class PlanStatus(StrEnum):
    active = "active"
    completed = "completed"
    blocked = "blocked"


class StepStatus(StrEnum):
    pending = "pending"
    in_progress = "in_progress"
    awaiting_review = "awaiting_review"
    completed = "completed"
    failed = "failed"
    skipped = "skipped"


class AttemptStatus(StrEnum):
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    interrupted = "interrupted"


class PlanRequest(SQLModel, table=True):
    __tablename__ = "plan_requests"

    id: str = Field(default_factory=new_id, primary_key=True)
    session_id: str = Field(index=True)
    input: str
    status: str = Field(default=PlanStatus.active)
    started_at: str = Field(default_factory=utc_now)
    finished_at: str | None = None

    inputs: list["RequestInput"] = Relationship(back_populates="request")
    plan: "ExecutionPlan" = Relationship(back_populates="request")


class RequestInput(SQLModel, table=True):
    __tablename__ = "plan_request_inputs"

    id: str = Field(default_factory=new_id, primary_key=True)
    request_id: str = Field(foreign_key="plan_requests.id", index=True)
    input: str
    received_at: str = Field(default_factory=utc_now)

    request: PlanRequest = Relationship(back_populates="inputs")


class ExecutionPlan(SQLModel, table=True):
    __tablename__ = "execution_plans"
    __table_args__ = (UniqueConstraint("request_id"),)

    id: str = Field(default_factory=new_id, primary_key=True)
    session_id: str = Field(index=True)
    request_id: str = Field(foreign_key="plan_requests.id", index=True)
    goal: str
    status: str = Field(default=PlanStatus.active)
    revision: int = 1
    current_step_number: int | None = None
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)
    completed_at: str | None = None
    final_summary: str | None = None

    request: PlanRequest = Relationship(back_populates="plan")
    steps: list["PlanStep"] = Relationship(back_populates="plan")
    revisions: list["PlanRevision"] = Relationship(back_populates="plan")


class PlanStep(SQLModel, table=True):
    __tablename__ = "plan_steps"
    __table_args__ = (UniqueConstraint("plan_id", "number"),)

    id: str = Field(default_factory=new_id, primary_key=True)
    plan_id: str = Field(foreign_key="execution_plans.id", index=True)
    number: int
    title: str
    expected_result: str
    status: str = Field(default=StepStatus.pending)
    attempt_count: int = 0
    latest_exit_code: int | None = None
    started_at: str | None = None
    completed_at: str | None = None
    result_summary: str | None = None
    evidence: str | None = None

    plan: ExecutionPlan = Relationship(back_populates="steps")
    attempts: list["PlanAttempt"] = Relationship(back_populates="step")


class PlanAttempt(SQLModel, table=True):
    __tablename__ = "plan_attempts"
    __table_args__ = (UniqueConstraint("step_id", "number"),)

    id: str = Field(default_factory=new_id, primary_key=True)
    step_id: str = Field(foreign_key="plan_steps.id", index=True)
    number: int
    status: str = Field(default=AttemptStatus.running)
    tool: str
    action: str
    purpose: str
    expected_result: str
    request_json: str
    result_json: str | None = None
    started_at: str = Field(default_factory=utc_now)
    finished_at: str | None = None
    lease_until: float | None = None

    step: PlanStep = Relationship(back_populates="attempts")


class PlanRevision(SQLModel, table=True):
    __tablename__ = "plan_revisions"
    __table_args__ = (UniqueConstraint("plan_id", "number"),)

    id: str = Field(default_factory=new_id, primary_key=True)
    plan_id: str = Field(foreign_key="execution_plans.id", index=True)
    number: int
    reason: str
    goal: str
    created_at: str = Field(default_factory=utc_now)

    plan: ExecutionPlan = Relationship(back_populates="revisions")


class PlanPointer(SQLModel, table=True):
    """The current request and plan for one session in the shared database."""

    __tablename__ = "plan_pointer"

    session_id: str = Field(primary_key=True)
    version: int = 0
    request_id: str | None = Field(default=None, foreign_key="plan_requests.id")
    plan_id: str | None = Field(default=None, foreign_key="execution_plans.id")
