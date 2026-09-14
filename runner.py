from app.input import get_input
from app.settings import settings
from app.session import create_session
from app.project import get_workflow_database_path
from workflow.session import SQLiteWorkflowSession
from workflow.controller import WorkflowController


def run_agent() -> None:
    user_input = get_input()
    controller = WorkflowController(
        workflow_session=SQLiteWorkflowSession(
            session_id=settings.session_id,
            db_path=get_workflow_database_path(),
        ),
        conversation_session=create_session(),
    )
    try:
        result = controller.run(user_input)
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
