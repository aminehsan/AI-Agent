from datetime import UTC, datetime
from enum import StrEnum
from pydantic import BaseModel, Field as PydanticField
from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel


def utc_now() -> datetime:
    return datetime.now(UTC)


class WorkflowStatus(StrEnum):
    running = "running"
    completed = "completed"
    blocked = "blocked"


class StepStatus(StrEnum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class PlanningMode(StrEnum):
    direct = "direct"
    plan = "plan"


class PlanningDecision(BaseModel):
    mode: PlanningMode = PydanticField(
        description="Use direct for a conversational answer and plan for project work."
    )
    answer: str = PydanticField(
        description="The final answer in direct mode; otherwise an empty string."
    )
    goal: str = PydanticField(
        description="The intended outcome in plan mode; otherwise an empty string."
    )
    success_criteria: list[str] = PydanticField(
        description="Observable completion criteria in plan mode; otherwise an empty list."
    )
    steps: list[str] = PydanticField(
        description="Small ordered execution steps in plan mode; otherwise an empty list."
    )


class PlanDraft(BaseModel):
    goal: str = PydanticField(min_length=1)
    success_criteria: list[str] = PydanticField(min_length=1)
    steps: list[str] = PydanticField(min_length=1)


class WorkflowStep(BaseModel):
    number: int
    task: str
    status: StepStatus = StepStatus.pending
    summary: str | None = None
    evidence: list[str] = PydanticField(default_factory=list)


class WorkflowState(BaseModel):
    request: str
    goal: str
    success_criteria: list[str]
    steps: list[WorkflowStep]
    status: WorkflowStatus = WorkflowStatus.running

    @classmethod
    def from_draft(cls, request: str, draft: PlanDraft) -> "WorkflowState":
        return cls(
            request=request,
            goal=draft.goal,
            success_criteria=draft.success_criteria,
            steps=[
                WorkflowStep(number=number, task=task)
                for number, task in enumerate(draft.steps, start=1)
            ],
        )

    def completed_context(self) -> list[dict[str, object]]:
        return [
            {
                "step": step.number,
                "task": step.task,
                "summary": step.summary,
                "evidence": step.evidence,
            }
            for step in self.steps
            if step.status == StepStatus.completed
        ]


class WorkflowRecord(SQLModel, table=True):
    __tablename__ = "workflows"

    session_id: str = Field(primary_key=True)
    request: str
    goal: str
    status: WorkflowStatus
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    criteria: list["WorkflowCriterionRecord"] = Relationship(
        back_populates="workflow",
        cascade_delete=True,
    )
    steps: list["WorkflowStepRecord"] = Relationship(
        back_populates="workflow",
        cascade_delete=True,
    )


class WorkflowCriterionRecord(SQLModel, table=True):
    __tablename__ = "workflow_success_criteria"
    __table_args__ = (UniqueConstraint("workflow_session_id", "position"),)

    id: int | None = Field(default=None, primary_key=True)
    workflow_session_id: str = Field(
        foreign_key="workflows.session_id",
        ondelete="CASCADE",
        index=True,
    )
    position: int
    value: str

    workflow: WorkflowRecord = Relationship(back_populates="criteria")


class WorkflowStepRecord(SQLModel, table=True):
    __tablename__ = "workflow_steps"
    __table_args__ = (UniqueConstraint("workflow_session_id", "number"),)

    id: int | None = Field(default=None, primary_key=True)
    workflow_session_id: str = Field(
        foreign_key="workflows.session_id",
        ondelete="CASCADE",
        index=True,
    )
    number: int
    task: str
    status: StepStatus
    summary: str | None = None

    workflow: WorkflowRecord = Relationship(back_populates="steps")
    evidence: list["WorkflowEvidenceRecord"] = Relationship(
        back_populates="step",
        cascade_delete=True,
    )


class WorkflowEvidenceRecord(SQLModel, table=True):
    __tablename__ = "workflow_step_evidence"
    __table_args__ = (UniqueConstraint("step_id", "position"),)

    id: int | None = Field(default=None, primary_key=True)
    step_id: int | None = Field(
        default=None,
        foreign_key="workflow_steps.id",
        nullable=False,
        ondelete="CASCADE",
        index=True,
    )
    position: int
    value: str

    step: WorkflowStepRecord = Relationship(back_populates="evidence")
