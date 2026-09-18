from agents import Runner
from agents.run_config import DEFAULT_MAX_TURNS
from agent.agent import create_agent
from agent.session import create_session
from cli.input import get_input
from cli.output import set_output


def run_agent():
    result = Runner.run_sync(
        starting_agent=create_agent(),
        input=get_input(),
        max_turns=DEFAULT_MAX_TURNS,
        session=create_session(),
    )
    set_output(result)
