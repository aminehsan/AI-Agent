import tempfile
import unittest
from pathlib import Path
from app.settings import settings
from app.plan import PlanStateError, PlanStore


class PlanStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.original_root = settings.project_root
        self.original_session = settings.session_id
        settings.project_root = Path(self.temporary.name)
        settings.session_id = "plan-tests"
        self.store = PlanStore()
        self.store.begin_request("change the project")

    def tearDown(self) -> None:
        settings.project_root = self.original_root
        settings.session_id = self.original_session
        self.temporary.cleanup()

    @staticmethod
    def _steps() -> list[dict[str, str]]:
        return [
            {"title": "Inspect", "expected_result": "Project state is known"},
            {"title": "Change", "expected_result": "Requested change is verified"},
        ]

    def test_full_plan_lifecycle_and_persistence(self) -> None:
        self.store.create_plan("Complete the request", self._steps())
        self.store.start_step(1)
        reservation = self.store.begin_execution(
            step_id=1,
            tool_name="run_command",
            action="run",
            purpose="Inspect current state",
            expected_result="State is printed",
            details={"command": "example"},
        )
        self.store.finish_execution(
            step_id=1,
            attempt_number=reservation["attempt_number"],
            result={"exit_code": 0, "stdout": "ok", "stderr": ""},
        )
        self.store.review_step(1, "completed", "Inspection succeeded", "exit_code=0")
        self.store.start_step(2)
        reservation = self.store.begin_execution(
            step_id=2,
            tool_name="filesystem",
            action="write",
            purpose="Apply requested change",
            expected_result="File is updated",
            details={"path": "file.txt"},
        )
        self.store.finish_execution(
            step_id=2,
            attempt_number=reservation["attempt_number"],
            result={"exit_code": 0, "stdout": "", "stderr": ""},
        )
        self.store.review_step(2, "completed", "Change succeeded", "exit_code=0")
        state = self.store.finish_plan("All requested work is complete")
        self.assertTrue(self.store.current_request_is_complete())
        self.assertEqual(state["active_plan"]["status"], "completed")
        self.assertEqual(
            PlanStore().snapshot()["active_plan"]["final_summary"],
            "All requested work is complete",
        )

    def test_execution_requires_current_started_step(self) -> None:
        self.store.create_plan("Complete the request", self._steps())
        with self.assertRaisesRegex(PlanStateError, "not current"):
            self.store.begin_execution(
                step_id=1,
                tool_name="run_command",
                action="run",
                purpose="Try too early",
                expected_result="It fails",
                details={},
            )

    def test_steps_must_start_in_order(self) -> None:
        self.store.create_plan("Complete the request", self._steps())
        with self.assertRaisesRegex(PlanStateError, "out of order"):
            self.store.start_step(2)

    def test_next_execution_waits_for_review(self) -> None:
        self.store.create_plan("Complete the request", self._steps())
        self.store.start_step(1)
        reservation = self.store.begin_execution(
            step_id=1,
            tool_name="run_command",
            action="run",
            purpose="Run once",
            expected_result="Result exists",
            details={},
        )
        self.store.finish_execution(
            step_id=1,
            attempt_number=reservation["attempt_number"],
            result={"exit_code": 1, "stdout": "", "stderr": "failed"},
        )
        with self.assertRaisesRegex(PlanStateError, "must be in_progress"):
            self.store.begin_execution(
                step_id=1,
                tool_name="run_command",
                action="run",
                purpose="Run again without review",
                expected_result="It fails",
                details={},
            )

    def test_retry_keeps_the_same_step_current(self) -> None:
        self.store.create_plan("Complete the request", self._steps())
        self.store.start_step(1)
        reservation = self.store.begin_execution(
            step_id=1,
            tool_name="run_command",
            action="run",
            purpose="First attempt",
            expected_result="Command succeeds",
            details={},
        )
        self.store.finish_execution(
            step_id=1,
            attempt_number=reservation["attempt_number"],
            result={"exit_code": 1},
        )
        state = self.store.review_step(1, "retry", "The error is correctable")
        self.assertEqual(state["active_plan"]["current_step_id"], 1)
        self.assertEqual(state["active_plan"]["steps"][0]["status"], "in_progress")

    def test_failed_step_requires_plan_revision(self) -> None:
        self.store.create_plan("Complete the request", self._steps())
        self.store.start_step(1)
        reservation = self.store.begin_execution(
            step_id=1,
            tool_name="run_command",
            action="run",
            purpose="Run a blocked command",
            expected_result="Command succeeds",
            details={},
        )
        self.store.finish_execution(
            step_id=1,
            attempt_number=reservation["attempt_number"],
            result={"exit_code": 1},
        )
        self.store.review_step(1, "failed", "The step is blocked")
        with self.assertRaisesRegex(PlanStateError, "revising the plan"):
            self.store.start_step(2)

    def test_interrupted_execution_is_recovered_for_review(self) -> None:
        self.store.create_plan("Complete the request", self._steps())
        self.store.start_step(1)
        self.store.begin_execution(
            step_id=1,
            tool_name="run_command",
            action="run",
            purpose="Start a command",
            expected_result="A result is returned",
            details={"command": "example"},
        )

        state = self.store.begin_request("resume after restart")
        step = state["active_plan"]["steps"][0]
        attempt = step["attempts"][0]
        self.assertEqual(step["status"], "awaiting_review")
        self.assertEqual(attempt["status"], "failed")
        self.assertIn("stopped", attempt["result"]["launch_error"])
