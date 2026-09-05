from agents import Agent
from .settings import settings
from .model import create_model
from tools.filesystem import list_files


def create_agent() -> Agent:
    return Agent(
        name=settings.agent_name,
        model=create_model(),
        instructions=settings.agent_instructions,
        tools=[list_files],
    )
