import json
from dataclasses import dataclass
from typing import Any
from agents import Runner, SQLiteSession, ToolCallOutputItem
from app.agent import create_executor_agent, create_planner_agent
from .models import StepStatus, WorkflowState, WorkflowStatus
from .planning import PlanningContext
from .session import SQLiteWorkflowSession


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
        conversation_session: SQLiteSession,
    ) -> None:
        self.workflow_session = workflow_session
        self.conversation_session = conversation_session

    async def run(self, user_input: str) -> WorkflowResult:
        await self.workflow_session.clear()
        planner_input = await self._planner_input(user_input)
        planning_context = PlanningContext()

        print("Planning...")
        planning_result = await Runner.run(
            starting_agent=create_planner_agent(),
            input=planner_input,
            context=planning_context,
            max_turns=4,
        )
        result = WorkflowResult(answer="")
        self._add_usage(result, planning_result)

        if planning_context.direct_answer is not None:
            result.answer = planning_context.direct_answer
            await self._remember_exchange(user_input, result.answer)
            return result

        if planning_context.plan is None:
            raise RuntimeError("The planner returned neither an answer nor a plan.")

        state = WorkflowState.from_draft(user_input, planning_context.plan)
        await self.workflow_session.save(state)
        print(f"Goal: {state.goal}")

        for step in state.steps:
            print(f"[{step.number}/{len(state.steps)}] {step.task}")
            step.status = StepStatus.running
            await self.workflow_session.save(state)

            try:
                execution_result = await Runner.run(
                    starting_agent=create_executor_agent(state, step),
                    input="Execute the current workflow step now.",
                    max_turns=12,
                )
            except Exception as exc:
                step.status = StepStatus.failed
                step.summary = f"{type(exc).__name__}: {exc}"
                state.status = WorkflowStatus.blocked
                await self.workflow_session.save(state)
                result.answer = (
                    f"Workflow stopped at step {step.number}: {step.task}\n"
                    f"Reason: {step.summary}"
                )
                await self._remember_exchange(user_input, result.answer)
                return result

            self._add_usage(result, execution_result)
            evidence = self._successful_tool_outputs(execution_result.new_items)

            if not evidence:
                step.status = StepStatus.failed
                step.summary = "No successful tool result was produced."
                state.status = WorkflowStatus.blocked
                await self.workflow_session.save(state)
                result.answer = (
                    f"Workflow stopped at step {step.number}: {step.task}\n"
                    f"Reason: {step.summary}"
                )
                await self._remember_exchange(user_input, result.answer)
                return result

            step.status = StepStatus.completed
            step.summary = str(execution_result.final_output).strip()
            step.evidence = evidence
            await self.workflow_session.save(state)
            print(f"[{step.number}/{len(state.steps)}] completed")

        state.status = WorkflowStatus.completed
        await self.workflow_session.save(state)
        summaries = "\n".join(
            f"{step.number}. {step.summary}" for step in state.steps
        )
        result.answer = f"Goal completed: {state.goal}\n{summaries}"
        await self._remember_exchange(user_input, result.answer)
        return result

    async def _planner_input(self, user_input: str) -> list[dict[str, Any]]:
        history = await self.conversation_session.get_items(limit=12)
        messages = [
            item
            for item in history
            if isinstance(item, dict) and item.get("role") in {"user", "assistant"}
        ]
        messages.append({"role": "user", "content": user_input})
        return messages

    async def _remember_exchange(self, user_input: str, answer: str) -> None:
        await self.conversation_session.add_items(
            [
                {"role": "user", "content": user_input},
                {"role": "assistant", "content": answer},
            ]
        )

    @staticmethod
    def _successful_tool_outputs(items: list[Any]) -> list[str]:
        evidence: list[str] = []
        for item in items:
            if not isinstance(item, ToolCallOutputItem):
                continue
            try:
                output = json.loads(str(item.output))
            except (TypeError, json.JSONDecodeError):
                continue
            if isinstance(output, dict) and output.get("ok") is True:
                evidence.append(json.dumps(output, ensure_ascii=False)[:2000])
        return evidence

    @staticmethod
    def _add_usage(result: WorkflowResult, run_result: Any) -> None:
        usage = run_result.context_wrapper.usage
        result.input_tokens += usage.input_tokens
        result.output_tokens += usage.output_tokens
        result.total_tokens += usage.total_tokens
