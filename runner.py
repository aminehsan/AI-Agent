from agents import Runner

from agent.agent import create_agent
from agent.config import get_config
from agent.session import create_session
from cli.input import get_input
from cli.output import set_output
from settings import settings


def run_agent():
    result = Runner.run_sync(
        starting_agent=create_agent(),
        input=get_input(),
        max_turns=settings.run_max_turns,
        run_config=get_config(),
        session=create_session(),
    )
    set_output(result)
