import json
from typing import Annotated, Literal

from agents import function_tool
from pydantic import BaseModel, ConfigDict, Field

from app.plan import PlanStateError, plan_store


class PlanStepInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(description="One small executable plan step.")
    expected_result: str = Field(
        description="Observable evidence required to complete the step."
    )


class _PlanActionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    purpose: str = Field(description="Why this plan transition is needed now.")
    expected_result: str = Field(
        description="The expected plan state after this transition."
    )


class CreatePlanInput(_PlanActionInput):
    action: Literal["create"] = "create"
    goal: str = Field(description="The final outcome requested by the user.")
    steps: list[PlanStepInput] = Field(description="Ordered executable steps.")


class ShowPlanInput(_PlanActionInput):
    action: Literal["show"] = "show"
    plan_id: str | None = Field(
        default=None,
        description="Optional current or historical plan ID.",
    )
    step_id: int | None = Field(
        default=None,
        description="Optional step number whose complete attempt history is needed.",
    )
    history: bool = Field(
        default=False,
        description="List plans belonging to this session.",
    )


class StartPlanInput(_PlanActionInput):
    action: Literal["start"] = "start"
    step_id: int = Field(description="The next pending step number.")


class ReviewPlanInput(_PlanActionInput):
    action: Literal["review"] = "review"
    step_id: int = Field(description="The current step number to review.")
    review_outcome: Literal["completed", "retry", "failed", "skipped"]
    summary: str = Field(description="Interpretation of the recorded tool result.")
    evidence: str | None = Field(
        default=None,
        description="Concrete output or observation supporting the review.",
    )


class RevisePlanInput(_PlanActionInput):
    action: Literal["revise"] = "revise"
    revision_reason: str = Field(
        description="Why the unfinished portion of the plan must change."
    )
    steps: list[PlanStepInput] = Field(description="Replacement remaining steps.")
    goal: str | None = Field(
        default=None,
        description="An optional revised final goal.",
    )


class FinishPlanInput(_PlanActionInput):
    action: Literal["finish"] = "finish"
    summary: str = Field(description="Evidence-based completion summary.")


class BlockPlanInput(_PlanActionInput):
    action: Literal["block"] = "block"
    summary: str = Field(description="Why the request cannot be completed.")


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


def _print_plan_transition(request: PlanInput, response: dict) -> None:
    print("\n" + "=" * 80)
    print(f"PLAN ACTION: {request.action}")
    print("=" * 80)
    print(f"Purpose:\n{request.purpose}")
    print(f"Expected result:\n{request.expected_result}")
    print("Plan result:")
    print(json.dumps(response, ensure_ascii=False, indent=2))
    print("=" * 80 + "\n")


@function_tool
def plan(request: PlanInput) -> str:
    """Create and manage the persistent execution plan for the current request.

    Create a plan before using a filesystem tool. Start one ordered step, perform exactly one
    filesystem operation for it, and review the recorded result before continuing. Retry a
    correctable attempt, revise unfinished steps when the approach changes, finish after every
    required step succeeds, or block an impossible request. Plan state and tool attempts persist
    in SQLite and can be inspected with show.

    Args:
        request: A create, show, start, review, revise, finish, or block transition.
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
            if request.step_id is not None:
                result = plan_store.step_history(request.step_id, request.plan_id)
            elif request.plan_id is not None:
                result = plan_store.plan_history(request.plan_id)
            elif request.history:
                result = plan_store.list_plans()
            else:
                result = plan_store.compact_snapshot()
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
        elif isinstance(request, FinishPlanInput):
            result = plan_store.finish_plan(request.summary)
        else:
            result = plan_store.block_plan(request.summary)

        response = {"ok": True, "action": request.action, "state": result}
    except (PlanStateError, ValueError) as exc:
        response = {
            "ok": False,
            "action": request.action,
            "error": str(exc),
            "state": plan_store.compact_snapshot(),
        }

    _print_plan_transition(request, response)
    return json.dumps(response, ensure_ascii=False, indent=2)
