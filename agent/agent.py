from agents import Agent
from settings import settings
from agent.model import create_model
from agent.instructions import get_instructions
from tools.filesystem import get_project_path


def create_agent() -> Agent:
    return Agent(
        name=settings.agent_name,
        instructions=get_instructions,
        model=create_model(),
        tools=[get_project_path],
    )
