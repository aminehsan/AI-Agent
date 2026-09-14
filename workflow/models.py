from enum import StrEnum
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


class PlanningMode(StrEnum):
    direct = "direct"
    plan = "plan"


class PlanningDecision(BaseModel):
    mode: PlanningMode = Field(
        description="Use direct for a conversational answer and plan for project work."
    )
    answer: str = Field(
        description="The final answer in direct mode; otherwise an empty string."
    )
    goal: str = Field(
        description="The intended outcome in plan mode; otherwise an empty string."
    )
    success_criteria: list[str] = Field(
        description="Observable completion criteria in plan mode; otherwise an empty list."
    )
    steps: list[str] = Field(
        description="Small ordered execution steps in plan mode; otherwise an empty list."
    )


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
