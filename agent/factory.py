from agents import Agent

from model.provider import create_model
from model.settings import get_model_settings, get_summarizer_model_settings
from settings import settings
from tools.registry import get_tools

from .instructions import get_instructions, get_summarizer_instructions


def create_agent() -> Agent:
    return Agent(
        name=settings.agent_name,
        tools=get_tools(),
        instructions=get_instructions,
        model=create_model(),
        model_settings=get_model_settings(),
    )


def create_summarizer_agent() -> Agent:
    return Agent(
        name="Input Summarizer",
        instructions=get_summarizer_instructions,
        model=create_model(),
        model_settings=get_summarizer_model_settings(),
    )
