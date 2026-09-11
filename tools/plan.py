from __future__ import annotations
import json
from agents import function_tool
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field
from app.plan import PlanStateError, plan_store


class PlanStepInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(description="One small executable step with one tool execution.")
    expected_result: str = Field(
        description="Observable evidence that completes this step."
    )


class _PlanInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    purpose: str = Field(description="Why this plan transition is needed now.")
    expected_result: str = Field(
        description="Expected plan state after this transition."
    )


class CreatePlanInput(_PlanInput):
    action: Literal["create"] = "create"
    goal: str = Field(description="Overall outcome required by the user.")
    steps: list[PlanStepInput] = Field(description="Small ordered executable steps.")


class ShowPlanInput(_PlanInput):
    action: Literal["show"] = "show"


class StartPlanInput(_PlanInput):
    action: Literal["start"] = "start"
    step_id: int = Field(description="Pending step to make current and in progress.")


class ReviewPlanInput(_PlanInput):
    action: Literal["review"] = "review"
    step_id: int = Field(
        description="Current step whose latest command result was inspected."
    )
    review_outcome: Literal["completed", "retry", "failed", "skipped"]
    summary: str = Field(
        description="Evidence-based interpretation of the command result."
    )
    evidence: str | None = Field(
        default=None,
        description="Concrete output, exit code, file, or observation supporting the review.",
    )


class RevisePlanInput(_PlanInput):
    action: Literal["revise"] = "revise"
    revision_reason: str = Field(description="Why unfinished steps must be replaced.")
    steps: list[PlanStepInput] = Field(description="New remaining executable steps.")
    goal: str | None = Field(default=None, description="Optional revised overall goal.")


class FinishPlanInput(_PlanInput):
    action: Literal["finish"] = "finish"
    summary: str = Field(
        description="Evidence-based summary proving the plan goal is complete."
    )


PlanInput = Annotated[
    CreatePlanInput
    | ShowPlanInput
    | StartPlanInput
    | ReviewPlanInput
    | RevisePlanInput
    | FinishPlanInput,
    Field(discriminator="action"),
]


def _print_plan_event(request: PlanInput, result: dict) -> None:
    print("\n" + "=" * 80)
    print(f"PLAN ACTION: {request.action}")
    print("=" * 80)
    print(f"Purpose:\n{request.purpose}")
    print(f"Expected result:\n{request.expected_result}")
    print("Plan arguments:")
    print(json.dumps(request.model_dump(), ensure_ascii=False, indent=2))
    print("Plan result:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("=" * 80 + "\n")


@function_tool
def plan(request: PlanInput) -> str:
    """Manage the mandatory persistent execution plan for every user request.

    Create a small-step plan before any execution. Start exactly one pending step, execute exactly
    one filesystem or run_command call for it, then review the complete result before any next
    execution. Retry a correctable attempt, fail a blocked step, revise unfinished work when the
    approach changes, and finish only after the requested outcome is genuinely achieved. The plan,
    step statuses, full attempt history, evidence, and current position survive application restarts.

    Args:
        request: Action-specific create, show, start, review, revise, or finish transition.
    """

    try:
        if not request.purpose.strip() or not request.expected_result.strip():
            raise PlanStateError("purpose and expected_result are required.")
        if isinstance(request, CreatePlanInput):
            result = plan_store.create_plan(
                request.goal,
                [step.model_dump() for step in request.steps],
            )
        elif isinstance(request, ShowPlanInput):
            result = plan_store.snapshot()
        elif isinstance(request, StartPlanInput):
            result = plan_store.start_step(request.step_id)
        elif isinstance(request, ReviewPlanInput):
            result = plan_store.review_step(
                step_id=request.step_id,
                outcome=request.review_outcome,
                summary=request.summary,
                evidence=request.evidence,
            )
        elif isinstance(request, RevisePlanInput):
            result = plan_store.revise_plan(
                reason=request.revision_reason,
                steps=[step.model_dump() for step in request.steps],
                goal=request.goal,
            )
        else:
            result = plan_store.finish_plan(request.summary)
        response = {"ok": True, "action": request.action, "state": result}
    except (PlanStateError, ValueError) as exc:
        response = {
            "ok": False,
            "action": request.action,
            "error": str(exc),
            "state": plan_store.snapshot(),
        }
    _print_plan_event(request, response)
    return json.dumps(response, ensure_ascii=False, indent=2)
