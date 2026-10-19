from agents import ModelSettings
from openai.types import Reasoning
from openai.types.responses.response_create_params import ContextManagement

from settings import settings


def get_compaction_model_settings() -> ModelSettings:
    return ModelSettings(
        tool_choice="none",
        parallel_tool_calls=False,
        truncation="auto",
        max_tokens=None,
        reasoning=Reasoning(effort="high", summary="concise", context="current_turn"),
        verbosity="high",
        store=False,
        context_management=[ContextManagement(type="compaction")],
    )


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
