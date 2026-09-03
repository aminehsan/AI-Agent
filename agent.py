from agents import Agent
from model import create_model
from tools.filesystem import list_files


def create_agent() -> Agent:
    return Agent(
        name="Coding Assistant",
        model=create_model(),
        tools=[list_files],
        instructions=(
            "Answer programming questions with simple, practical steps.\n"
            "Use list_files when the user asks about the project files."
        ),
    )
