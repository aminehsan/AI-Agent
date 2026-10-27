from agents import RunConfig, SessionSettings, ToolExecutionConfig

from agent.combiner import combines_input_items
from model.filter import filter_model_input
from settings import settings
from tools.error import format_tool_error


def create_run_config() -> RunConfig:
    return RunConfig(
        nest_handoff_history=True,
        tracing_disabled=True,
        session_input_callback=combines_input_items,
        call_model_input_filter=filter_model_input,
        tool_error_formatter=format_tool_error,
        session_settings=SessionSettings(limit=settings.session_history_limit),
        tool_execution=ToolExecutionConfig(max_function_tool_concurrency=1),
        tool_not_found_behavior="return_error_to_model",
        tool_name_collision_policy="error",
    )
