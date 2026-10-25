from agents import Runner

from agent.factory import create_agent
from agent.session import create_conversation_session
from cli.input import read_user_input
from cli.output import print_run_result
from config import create_run_config
from settings import settings


def run_agent() -> None:
    run_result = Runner.run_sync(
        starting_agent=create_agent(),
        input=read_user_input(),
        max_turns=settings.agent_max_turns,
        run_config=create_run_config(),
        session=create_conversation_session(),
    )
    print_run_result(run_result)
