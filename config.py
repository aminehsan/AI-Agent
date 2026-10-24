from agents import RunConfig, SessionSettings, ToolExecutionConfig

from model.filter import filter_input
from settings import settings
from tools.error import error_formatter


def get_run_config() -> RunConfig:
    return RunConfig(
        nest_handoff_history=True,
        tracing_disabled=True,
        call_model_input_filter=filter_input,
        tool_error_formatter=error_formatter,
        session_settings=SessionSettings(limit=settings.run_session_limit),
        tool_execution=ToolExecutionConfig(max_function_tool_concurrency=1),
        tool_not_found_behavior="return_error_to_model",
        tool_name_collision_policy="error",
    )
