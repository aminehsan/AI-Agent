from app.input import get_input
from app.project import get_workflow_database_path
from app.session import create_session
from app.settings import settings
from workflow.controller import WorkflowController
from workflow.session import SQLiteWorkflowSession


async def run_agent() -> None:
    user_input = await get_input()
    controller = WorkflowController(
        workflow_session=SQLiteWorkflowSession(
            session_id=settings.session_id,
            db_path=get_workflow_database_path(),
        ),
        conversation_session=create_session(),
    )
    try:
        result = await controller.run(user_input)
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
