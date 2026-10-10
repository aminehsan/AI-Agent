from agents import Agent

from agent.instructions import get_instructions
from agent.model import create_model
from agent.settings import get_settings
from config import settings
from tools.registry import get_tools


def create_agent() -> Agent:
    return Agent(
        name=settings.agent_name,
        instructions=get_instructions,
        model=create_model(),
        model_settings=get_settings(),
        tools=get_tools(),
    )
