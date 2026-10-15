from agents import Agent

from model.model import create_model
from settings import settings
from tools.registry import get_tools

from .config import get_model_settings
from .instructions import get_instructions


def create_agent() -> Agent:
    return Agent(
        name=settings.agent_name,
        tools=get_tools(),
        instructions=get_instructions,
        model=create_model(),
        model_settings=get_model_settings(),
    )
