from agents import Agent

from agent.instructions import get_instructions
from agent.model import create_model
from settings import settings
from tools.registry import get_tools


def create_agent() -> Agent:
    return Agent(
        name=settings.agent_name,
        instructions=get_instructions,
        model=create_model(),
        tools=get_tools(),
    )
