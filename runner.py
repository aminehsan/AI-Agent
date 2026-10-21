from agents import Runner

from agent.factory import create_agent
from agent.session import create_compaction_session
from cli.input import get_input
from cli.output import show_output
from config import get_run_config
from settings import settings


def run() -> None:
    result = Runner.run_sync(
        starting_agent=create_agent(),
        input=get_input(),
        max_turns=settings.run_max_turns,
        run_config=get_run_config(),
        session=create_compaction_session(),
    )
    show_output(result)
