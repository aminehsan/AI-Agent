from agents import Agent

from settings import settings
from tools.registry import get_tools

from .config import get_settings
from .instructions import get_instructions
from .model import create_model


def create_agent() -> Agent:
    return Agent(
        name=settings.agent_name,
        instructions=get_instructions,
        model=create_model(),
        model_settings=get_settings(),
        tools=get_tools(),
    )
