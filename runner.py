from agents import Runner

from agent.factory import create_agent
from agent.session import create_session
from cli.input import get_user_input
from cli.output import show_run_result
from config import create_run_config
from settings import settings


def run_agent() -> None:
    run_result = Runner.run_sync(
        starting_agent=create_agent(),
        input=get_user_input(),
        max_turns=settings.run_max_turns,
        run_config=create_run_config(),
        session=create_session(),
    )
    show_run_result(run_result)
