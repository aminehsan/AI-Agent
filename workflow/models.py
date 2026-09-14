from enum import StrEnum
from uuid import uuid4
from pydantic import BaseModel, Field


class WorkflowStatus(StrEnum):
    running = "running"
    completed = "completed"
    blocked = "blocked"


class StepStatus(StrEnum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class PlanDraft(BaseModel):
    goal: str = Field(min_length=1)
    success_criteria: list[str] = Field(min_length=1)
    steps: list[str] = Field(min_length=1)


class WorkflowStep(BaseModel):
    number: int
    task: str
    status: StepStatus = StepStatus.pending
    summary: str | None = None
    evidence: list[str] = Field(default_factory=list)


class WorkflowState(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
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
