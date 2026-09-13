from agents import Agent, ModelSettings, RunContextWrapper
from tools.plan import plan
from tools.filesystem import edit_file, list_files, read_file, write_file

from .plan import plan_store
from .settings import settings
from .model import create_model


def _instructions(_context: RunContextWrapper[object], _agent: Agent[object]) -> str:
    return f"""
{settings.agent_instructions}

Treat the configured project directory as the project root. Use only relative paths with
filesystem tools, and always read a file before changing it.

Every user request must follow this plan lifecycle:
1. Create a small ordered plan before using a filesystem tool. If unfinished work already exists,
   inspect its current state and continue or revise it.
2. Start exactly the next pending step.
3. Execute exactly one filesystem tool for that step. Pass the current step_id and state a precise
   purpose and expected_result.
4. Inspect the complete tool result, then immediately review the step. Complete it only with
   concrete evidence; otherwise retry, fail, or revise the unfinished plan.
5. Finish the plan only after its goal is achieved. If completion is impossible, review any pending
   result and block the plan with a clear reason.
6. Do not provide a final answer while the current request or its plan is still active.

Current persistent plan state:
{plan_store.prompt_snapshot()}
""".strip()


def create_agent() -> Agent:
    return Agent(
        name=settings.agent_name,
        model=create_model(),
        instructions=_instructions,
        model_settings=ModelSettings(parallel_tool_calls=False),
        tools=[plan, list_files, read_file, write_file, edit_file],
    )
