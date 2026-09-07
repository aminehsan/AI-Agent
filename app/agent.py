from agents import Agent
from .settings import settings
from .model import create_model
from tools.filesystem import edit_file, list_files, read_file, write_file


def create_agent() -> Agent:
    return Agent(
        name=settings.agent_name,
        model=create_model(),
        instructions=(
            f"{settings.agent_instructions} "
            "Treat the configured project directory as the project root. "
            "Use only relative paths with filesystem tools. Read a file before changing it."
        ),
        tools=[list_files, read_file, write_file, edit_file],
    )
