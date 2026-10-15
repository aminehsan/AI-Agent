from agents import RunConfig, Runner, SessionSettings, ToolExecutionConfig

from agent.agent import create_agent
from agent.session import create_session
from cli.input import get_input
from cli.output import set_output
from settings import settings


def run_agent():
    result = Runner.run_sync(
        starting_agent=create_agent(),
        input=get_input(),
        max_turns=settings.run_max_turns,
        session=create_session(),
        run_config=RunConfig(
            nest_handoff_history=True,
            tracing_disabled=True,
            session_settings=SessionSettings(limit=settings.run_session_limit),
            tool_execution=ToolExecutionConfig(max_function_tool_concurrency=1),
            tool_not_found_behavior="return_error_to_model",
            tool_name_collision_policy="error",
        ),
    )
    set_output(result)
