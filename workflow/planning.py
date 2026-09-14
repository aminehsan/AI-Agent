from dataclasses import dataclass
from agents import RunContextWrapper, function_tool
from .models import PlanDraft


@dataclass
class PlanningContext:
    plan: PlanDraft | None = None
    direct_answer: str | None = None


def _required_text(value: str, name: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{name} cannot be empty.")
    return value


@function_tool
def answer_directly(
    context: RunContextWrapper[PlanningContext],
    answer: str,
) -> str:
    """Answer a request that needs no project inspection, file change, or command execution."""
    context.context.direct_answer = _required_text(answer, "answer")
    return "Direct answer accepted."


@function_tool
def submit_plan(
    context: RunContextWrapper[PlanningContext],
    goal: str,
    success_criteria: list[str],
    steps: list[str],
) -> str:
    """Submit an ordered execution plan for a request that needs project tools.

    Each step must describe an executable outcome and how it will be verified. Keep the plan as
    small as possible while still covering implementation and final verification.
    """
    context.context.plan = PlanDraft(
        goal=_required_text(goal, "goal"),
        success_criteria=[
            _required_text(item, "success criterion") for item in success_criteria
        ],
        steps=[_required_text(item, "step") for item in steps],
    )
    return "Plan accepted."
