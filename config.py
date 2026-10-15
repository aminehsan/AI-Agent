from agents import ModelSettings, RunConfig, SessionSettings, ToolExecutionConfig
from openai.types import Reasoning
from openai.types.responses.response_create_params import ContextManagement

from model.filter import filter_input
from settings import settings


def get_model_settings() -> ModelSettings:
    return ModelSettings(
        tool_choice="auto",
        parallel_tool_calls=False,
        truncation="auto",
        max_tokens=settings.model_max_tokens,
        reasoning=Reasoning(
            effort=settings.model_reasoning, summary="concise", context="current_turn"
        ),
        verbosity=settings.model_verbosity,
        store=False,
        context_management=[
            ContextManagement(type="compaction", compact_threshold=settings.model_context_compact)
        ],
    )


def get_run_config() -> RunConfig:
    return RunConfig(
        nest_handoff_history=True,
        tracing_disabled=True,
        call_model_input_filter=filter_input,
        session_settings=SessionSettings(limit=settings.run_session_limit),
        tool_execution=ToolExecutionConfig(max_function_tool_concurrency=1),
        tool_not_found_behavior="return_error_to_model",
        tool_name_collision_policy="error",
    )
