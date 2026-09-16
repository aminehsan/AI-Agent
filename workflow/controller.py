from typing import Any
from dataclasses import dataclass
from json import JSONDecodeError, dumps, loads
from agents import (
    Runner,
    MaxTurnsExceeded,
    ModelBehaviorError,
    ToolCallOutputItem,
)
from .session import SQLiteWorkflowSession
from .models import (
    PlanDraft,
    PlanningDecision,
    PlanningMode,
    StepStatus,
    WorkflowState,
    WorkflowStatus,
)
from agent.factory import create_executor_agent, create_planner_agent
from agent.session import ConversationSession


@dataclass
class WorkflowResult:
    answer: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class WorkflowController:
    """Plan a request, execute its steps in order, and persist each transition."""

    def __init__(
        self,
        workflow_session: SQLiteWorkflowSession,
        conversation_session: ConversationSession,
    ) -> None:
        self.workflow_session = workflow_session
        self.conversation_session = conversation_session

    def run(self, user_input: str) -> WorkflowResult:
        self.workflow_session.clear()
        planner_input = self._planner_input(user_input)
        print("Planning...")
        planning_result, outcome = self._run_planner(planner_input)
        result = WorkflowResult(answer="")
        self._add_usage(result, planning_result)
        if isinstance(outcome, str):
            result.answer = outcome
            self._remember_exchange(user_input, result.answer)
            return result
        state = WorkflowState.from_draft(user_input, outcome)
        self.workflow_session.save(state)
        print(f"Goal: {state.goal}")
        for step in state.steps:
            print(f"[{step.number}/{len(state.steps)}] {step.task}")
            step.status = StepStatus.running
            self.workflow_session.save(state)
            try:
                execution_result = Runner.run_sync(
                    starting_agent=create_executor_agent(state, step),
                    input="Execute the current workflow step now.",
                    max_turns=12,
                )
            except Exception as exc:
                step.status = StepStatus.failed
                step.summary = f"{type(exc).__name__}: {exc}"
                state.status = WorkflowStatus.blocked
                self.workflow_session.save(state)
                result.answer = (
                    f"Workflow stopped at step {step.number}: {step.task}\n"
                    f"Reason: {step.summary}"
                )
                self._remember_exchange(user_input, result.answer)
                return result
            self._add_usage(result, execution_result)
            evidence = self._successful_tool_outputs(execution_result.new_items)
            if not evidence:
                step.status = StepStatus.failed
                step.summary = "No successful tool result was produced."
                state.status = WorkflowStatus.blocked
                self.workflow_session.save(state)
                result.answer = (
                    f"Workflow stopped at step {step.number}: {step.task}\n"
                    f"Reason: {step.summary}"
                )
                self._remember_exchange(user_input, result.answer)
                return result
            step.status = StepStatus.completed
            step.summary = str(execution_result.final_output).strip()
            step.evidence = evidence
            self.workflow_session.save(state)
            print(f"[{step.number}/{len(state.steps)}] completed")
        state.status = WorkflowStatus.completed
        self.workflow_session.save(state)
        summaries = "\n".join(f"{step.number}. {step.summary}" for step in state.steps)
        result.answer = f"Goal completed: {state.goal}\n{summaries}"
        self._remember_exchange(user_input, result.answer)
        return result

    def _planner_input(self, user_input: str) -> list[dict[str, Any]]:
        messages = [
            message
            for message in self.conversation_session.get_messages(limit=12)
            if message.get("role") in {"user", "assistant"}
        ]
        messages.append({"role": "user", "content": user_input})
        return messages

    def _run_planner(
        self,
        planner_input: list[dict[str, Any]],
    ) -> tuple[Any, str | PlanDraft]:
        for attempt in range(1, 4):
            try:
                result = Runner.run_sync(
                    starting_agent=create_planner_agent(),
                    input=planner_input,
                    max_turns=4,
                )
                decision = result.final_output_as(
                    PlanningDecision,
                    raise_if_incorrect_type=True,
                )
                return result, self._planning_outcome(decision)
            except (MaxTurnsExceeded, ModelBehaviorError, TypeError, ValueError) as exc:
                if attempt == 3:
                    raise RuntimeError(
                        "Planner could not produce a valid structured decision "
                        "after 3 attempts."
                    ) from exc
                print(f"Invalid planning output; retrying ({attempt}/3)...")
        raise RuntimeError("Planner retry loop ended unexpectedly.")

    @classmethod
    def _planning_outcome(cls, decision: PlanningDecision) -> str | PlanDraft:
        if decision.mode == PlanningMode.direct:
            return cls._required_text(decision.answer, "direct answer")
        return PlanDraft(
            goal=cls._required_text(decision.goal, "goal"),
            success_criteria=[
                cls._required_text(item, "success criterion")
                for item in decision.success_criteria
            ],
            steps=[cls._required_text(item, "step") for item in decision.steps],
        )

    def _remember_exchange(self, user_input: str, answer: str) -> None:
        self.conversation_session.add_exchange(user_input, answer)

    @staticmethod
    def _successful_tool_outputs(items: list[Any]) -> list[str]:
        evidence: list[str] = []
        for item in items:
            if not isinstance(item, ToolCallOutputItem):
                continue
            try:
                output = loads(str(item.output))
            except (TypeError, JSONDecodeError):
                continue
            if isinstance(output, dict) and output.get("ok") is True:
                evidence.append(dumps(output, ensure_ascii=False)[:2000])
        return evidence

    @staticmethod
    def _add_usage(result: WorkflowResult, run_result: Any) -> None:
        usage = run_result.context_wrapper.usage
        result.input_tokens += usage.input_tokens
        result.output_tokens += usage.output_tokens
        result.total_tokens += usage.total_tokens

    @staticmethod
    def _required_text(value: str, name: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError(f"Planner returned an empty {name}.")
        return value
