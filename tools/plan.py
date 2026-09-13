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
    plan_id: str | None = Field(
        default=None, description="Inspect a current or historical plan by ID."
    )
    step_id: int | None = Field(
        default=None,
        description="Show the complete attempt history for this step; omit for compact state.",
    )
    history: bool = Field(
        default=False, description="List plan IDs and summaries for this session."
    )


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


class BlockPlanInput(_PlanInput):
    action: Literal["block"] = "block"
    summary: str = Field(
        description="Why the request cannot be completed, after reviewing any command result."
    )


PlanInput = Annotated[
    CreatePlanInput
    | ShowPlanInput
    | StartPlanInput
    | ReviewPlanInput
    | RevisePlanInput
    | FinishPlanInput
    | BlockPlanInput,
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

    Create a small-step plan before any execution. Start exactly one pending step, execute one
    filesystem or run_command attempt at a time, then review the complete result before any next
    execution. Retry a correctable attempt, revise unfinished work when the approach changes,
    finish only after success, or block an impossible request. Use show with step_id to inspect
    complete attempt history. State and full results survive application restarts in SQLite.

    Args:
        request: Action-specific create, show, start, review, revise, finish, or block transition.
    """

    try:
        if not request.purpose.strip() or not request.expected_result.strip():
            raise PlanStateError("purpose and expected_result are required.")
        if isinstance(request, CreatePlanInput):
            plan_store.create_plan(
                request.goal,
                [step.model_dump() for step in request.steps],
            )
        elif isinstance(request, ShowPlanInput):
            if request.step_id is not None:
                result = plan_store.step_history(request.step_id, request.plan_id)
            elif request.plan_id is not None:
                result = plan_store.plan_history(request.plan_id)
            elif request.history:
                result = plan_store.list_plans()
            else:
                result = plan_store.compact_snapshot()
        elif isinstance(request, StartPlanInput):
            plan_store.start_step(request.step_id)
        elif isinstance(request, ReviewPlanInput):
            plan_store.review_step(
                step_id=request.step_id,
                outcome=request.review_outcome,
                summary=request.summary,
                evidence=request.evidence,
            )
        elif isinstance(request, RevisePlanInput):
            plan_store.revise_plan(
                reason=request.revision_reason,
                steps=[step.model_dump() for step in request.steps],
                goal=request.goal,
            )
        elif isinstance(request, FinishPlanInput):
            plan_store.finish_plan(request.summary)
        else:
            plan_store.block_plan(request.summary)
        if not isinstance(request, ShowPlanInput):
            result = plan_store.compact_snapshot()
        response = {"ok": True, "action": request.action, "state": result}
    except (PlanStateError, ValueError) as exc:
        response = {
            "ok": False,
            "action": request.action,
            "error": str(exc),
            "state": plan_store.compact_snapshot(),
        }
    _print_plan_event(request, response)
    return json.dumps(response, ensure_ascii=False, indent=2)
