from sys import stdout
from input import get_input
from settings import settings
from agent.session import create_session
from workflow.session import SQLiteWorkflowSession
from workflow.controller import WorkflowController


def run_agent() -> None:
    if hasattr(stdout, "reconfigure"):
        stdout.reconfigure(encoding="utf-8")
    controller = WorkflowController(
        workflow_session=SQLiteWorkflowSession(
            session_id=settings.session_id,
            db_path=settings.workflow_database_path,
        ),
        conversation_session=create_session(),
    )
    try:
        result = controller.run(get_input())
    except Exception as exc:
        raise SystemExit(f"Agent stopped: {type(exc).__name__}: {exc}") from exc
    print(f"\nAnswer:\n{result.answer}")
    print(
        "\n"
        "Token usage:\n"
        f"\tinput={result.input_tokens}\n"
        f"\toutput={result.output_tokens}\n"
        f"\ttotal={result.total_tokens}"
    )
