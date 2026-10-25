from agents import Agent

from model.provider import create_responses_model
from model.settings import create_model_settings, create_summarizer_model_settings
from settings import settings
from tools.registry import create_tools

from .instructions import build_instructions, build_summarizer_instructions


def create_agent() -> Agent:
    return Agent(
        name=settings.agent_name,
        tools=create_tools(),
        instructions=build_instructions,
        model=create_responses_model(),
        model_settings=create_model_settings(),
    )


def create_summarizer_agent() -> Agent:
    return Agent(
        name="Input Summarizer",
        instructions=build_summarizer_instructions,
        model=create_responses_model(),
        model_settings=create_summarizer_model_settings(),
    )
