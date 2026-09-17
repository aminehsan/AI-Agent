from agents import Runner
from agent.agent import create_agent
from agent.session import create_session
from cli_io.input import get_input
from cli_io.output import set_output


def run_agent():
    result = Runner.run_sync(
        starting_agent=create_agent(),
        input=get_input(),
        session=create_session(),
    )
    set_output(result)
