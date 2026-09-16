from json import dumps
from agents import Agent, ModelSettings
from settings import settings
from .model import create_model
from workflow.models import PlanningDecision, WorkflowState, WorkflowStep
from tools.filesystem import edit_file, list_files, read_file, run_command, write_file


def create_planner_agent() -> Agent[None]:
    return Agent(
        name=f"{settings.agent_name} Planner",
        model=create_model(),
        instructions=(
            "Decide whether the user's request needs project inspection, file changes, or "
            "command execution. Return mode direct when it does not; put the complete answer "
            "in answer and leave all plan fields empty. Return mode plan otherwise; leave "
            "answer empty and provide the intended goal, observable success criteria, and the "
            "smallest useful sequence of ordered steps. Each step must produce or verify an "
            "outcome. Do not include thinking, planning, or reporting as separate steps. Use "
            "the same language as the user's request. Requests to write, say, translate, "
            "explain, or generate text are direct unless the user explicitly asks to save, "
            "create, edit, inspect, or execute something in the project."
        ),
        output_type=PlanningDecision,
    )


def create_executor_agent(state: WorkflowState, step: WorkflowStep) -> Agent[None]:
    execution_context = {
        "request": state.request,
        "goal": state.goal,
        "success_criteria": state.success_criteria,
        "current_step": {
            "number": step.number,
            "task": step.task,
        },
        "completed_steps": state.completed_context(),
    }
    return Agent(
        name=f"{settings.agent_name} Executor",
        model=create_model(),
        model_settings=ModelSettings(
            tool_choice="required",
            parallel_tool_calls=False,
        ),
        instructions=(
            f"{settings.agent_instructions} "
            "Use the same language as the user's request.\n\n"
            "You are executing exactly one step of an approved workflow. Use the available "
            "tools to complete only current_step. You may call several tools and must inspect "
            "their results, correct failures, and gather observable evidence before finishing. "
            "Treat the configured project directory as the project root. Use only relative "
            "paths and read an existing file before changing it. End with a short factual "
            "summary of what was completed and verified.\n\n"
            f"Workflow context:\n{dumps(execution_context, ensure_ascii=False, indent=2)}"
        ),
        tools=[list_files, read_file, write_file, edit_file, run_command],
    )
