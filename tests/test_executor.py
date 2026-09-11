import uuid
import tempfile
import unittest
from pathlib import Path
from app.plan import plan_store
from app.settings import settings
from tools.executor import execute_command
from tools.environment import get_runtime_environment
from tools.commands import FilesystemRequest, build_filesystem_command


class CommandExecutorTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.original_root = settings.project_root
        self.original_session = settings.session_id
        settings.project_root = Path(self.temporary.name)
        settings.session_id = f"executor-{uuid.uuid4().hex}"
        plan_store.begin_request("exercise the executor")

    async def asyncTearDown(self) -> None:
        settings.project_root = self.original_root
        settings.session_id = self.original_session
        self.temporary.cleanup()

    def _create_plan(self, count: int) -> None:
        plan_store.create_plan(
            "Exercise the command executor",
            [
                {
                    "title": f"Command {index}",
                    "expected_result": f"Command {index} returns observable output",
                }
                for index in range(1, count + 1)
            ],
        )

    async def _execute(self, step_id: int, command: str, stdin: str | None = None):
        plan_store.start_step(step_id)
        result = await execute_command(
            step_id=step_id,
            tool_name="run_command",
            action="run",
            purpose=f"Execute test command {step_id}",
            expected_result="The complete command result is captured",
            command=command,
            stdin=stdin,
        )
        plan_store.review_step(
            step_id,
            "completed",
            "The executor returned a complete result",
            f"exit_code={result.get('exit_code')}",
        )
        return result

    async def test_stdout_stderr_and_exit_code_are_captured(self) -> None:
        self._create_plan(1)
        family = get_runtime_environment().family
        command = (
            "Write-Output 'stdout-value'; [Console]::Error.WriteLine('stderr-value')"
            if family == "windows"
            else "printf 'stdout-value\\n'; printf 'stderr-value\\n' >&2"
        )
        result = await self._execute(1, command)
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("stdout-value", result["stdout"])
        self.assertIn("stderr-value", result["stderr"])

    async def test_stdin_is_supplied_in_full(self) -> None:
        self._create_plan(1)
        command = (
            "[Console]::In.ReadToEnd()"
            if get_runtime_environment().family == "windows"
            else "cat"
        )
        result = await self._execute(1, command, stdin="hello from stdin")
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("hello from stdin", result["stdout"])

    async def test_nonzero_exit_is_returned_instead_of_raised(self) -> None:
        self._create_plan(1)
        command = (
            "Write-Error 'boom'"
            if get_runtime_environment().family == "windows"
            else "printf 'boom\\n' >&2; exit 7"
        )
        result = await self._execute(1, command)
        self.assertFalse(result["ok"])
        self.assertNotEqual(result["exit_code"], 0)
        self.assertIn("boom", result["stderr"])

    async def test_pipeline_runs_as_one_process(self) -> None:
        self._create_plan(1)
        command = (
            "1..3 | ForEach-Object { $_ } | Select-String '2'"
            if get_runtime_environment().family == "windows"
            else "printf '1\\n2\\n3\\n' | grep 2"
        )
        result = await self._execute(1, command)
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("2", result["stdout"])

    async def test_each_process_starts_from_the_requested_cwd(self) -> None:
        self._create_plan(2)
        child = Path(self.temporary.name) / "child"
        child.mkdir()
        family = get_runtime_environment().family
        first_command = (
            "Set-Location -LiteralPath 'child'; (Get-Location).Path"
            if family == "windows"
            else "cd 'child' && pwd"
        )
        second_command = "(Get-Location).Path" if family == "windows" else "pwd"
        first = await self._execute(1, first_command)
        second = await self._execute(2, second_command)
        self.assertIn("child", first["stdout"])
        self.assertEqual(
            Path(second["stdout"].strip()).resolve(),
            Path(self.temporary.name).resolve(),
        )

    async def test_standard_filesystem_commands_work_end_to_end(self) -> None:
        self._create_plan(5)
        runtime = get_runtime_environment()
        root = settings.project_root.resolve()
        source = root / "nested" / "نمونه.txt"
        copied = root / "copies" / "نمونه.txt"

        requests = [
            FilesystemRequest(action="write", path=source, content="سلام UTF-8\nagent"),
            FilesystemRequest(action="inspect", path=source, view="content"),
            FilesystemRequest(
                action="search",
                path=root,
                query="agent",
                search_target="content",
                pattern_type="literal",
                recursive=True,
            ),
            FilesystemRequest(
                action="transfer",
                path=source,
                destination=copied,
                transfer_mode="copy",
            ),
            FilesystemRequest(action="remove", path=copied),
        ]

        results = []
        for step_id, request in enumerate(requests, start=1):
            spec = build_filesystem_command(runtime, request)
            results.append(await self._execute(step_id, spec.command, spec.stdin))

        self.assertTrue(all(result["exit_code"] == 0 for result in results))
        self.assertIn("سلام UTF-8", results[1]["stdout"])
        self.assertIn("agent", results[2]["stdout"])
        self.assertFalse(copied.exists())
