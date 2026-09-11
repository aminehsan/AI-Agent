from __future__ import annotations
import os
import sys
import json
import codecs
import asyncio
from typing import Any
from time import monotonic
from datetime import UTC, datetime
from .environment import (
    configure_utf8_stdio,
    get_runtime_environment,
    resolve_working_directory,
)
from app.plan import PlanStateError, plan_store


_execution_lock: asyncio.Lock | None = None
_execution_lock_loop: asyncio.AbstractEventLoop | None = None


def _get_execution_lock() -> asyncio.Lock:
    """Return one lock for the active event loop without leaking it across test/app loops."""

    global _execution_lock, _execution_lock_loop
    loop = asyncio.get_running_loop()
    if _execution_lock is None or _execution_lock_loop is not loop:
        _execution_lock = asyncio.Lock()
        _execution_lock_loop = loop
    return _execution_lock


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()


def _print_block(title: str, value: Any) -> None:
    print(f"{title}:")
    if isinstance(value, (dict, list)):
        print(json.dumps(value, ensure_ascii=False, indent=2))
    elif value is None or value == "":
        print("<empty>")
    else:
        print(value)


async def _stream_pipe(
    stream: asyncio.StreamReader,
    destination: Any,
) -> str:
    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
    chunks: list[str] = []
    while True:
        data = await stream.read(4096)
        if not data:
            break
        text = decoder.decode(data)
        if text:
            chunks.append(text)
            print(text, end="", file=destination, flush=True)
    tail = decoder.decode(b"", final=True)
    if tail:
        chunks.append(tail)
        print(tail, end="", file=destination, flush=True)
    return "".join(chunks)


async def execute_command(
    *,
    step_id: int,
    tool_name: str,
    action: str,
    purpose: str,
    expected_result: str,
    command: str,
    cwd: str | None = None,
    stdin: str | None = None,
    environment_overrides: dict[str, str] | None = None,
    tool_arguments: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute one shell process, stream its output, and attach it to the current plan step."""

    configure_utf8_stdio()
    runtime = get_runtime_environment()
    working_directory = resolve_working_directory(cwd)
    overrides = environment_overrides or {}
    request_details = {
        "tool": tool_name,
        "action": action,
        "purpose": purpose,
        "expected_result": expected_result,
        "arguments": tool_arguments or {},
        "os": runtime.os_name,
        "distribution": runtime.distribution,
        "shell": runtime.shell,
        "cwd": str(working_directory),
        "command": command,
        "stdin": stdin,
        "environment_overrides": overrides,
    }
    async with _get_execution_lock():
        try:
            reservation = plan_store.begin_execution(
                step_id=step_id,
                tool_name=tool_name,
                action=action,
                purpose=purpose,
                expected_result=expected_result,
                details=request_details,
            )
        except PlanStateError as exc:
            return {
                "ok": False,
                "stage": "plan_gate",
                "error": str(exc),
                "request": request_details,
                "plan": json.loads(plan_store.prompt_snapshot()),
            }
        invocation = runtime.invocation(command)
        started_at = _timestamp()
        started_clock = monotonic()
        print("\n" + "=" * 80)
        print(
            f"COMMAND STEP {step_id} / ATTEMPT {reservation['attempt_number']} / "
            f"TOOL {tool_name}"
        )
        print("=" * 80)
        _print_block("Purpose", purpose)
        _print_block("Expected result", expected_result)
        _print_block("Tool arguments", tool_arguments or {})
        _print_block("Operating system", runtime.os_name)
        _print_block("Distribution", runtime.distribution)
        _print_block("Shell", runtime.shell)
        _print_block("Working directory", str(working_directory))
        _print_block("Command", command)
        _print_block("Shell invocation", invocation)
        _print_block("Standard input", stdin)
        _print_block("Environment overrides", overrides)
        _print_block("Started at", started_at)
        print("Live output follows (stdout and stderr retain their native streams):")
        process_environment = os.environ.copy()
        process_environment.update(overrides)
        process: asyncio.subprocess.Process | None = None
        try:
            process = await asyncio.create_subprocess_exec(
                *invocation,
                cwd=str(working_directory),
                env=process_environment,
                stdin=(
                    asyncio.subprocess.PIPE
                    if stdin is not None
                    else asyncio.subprocess.DEVNULL
                ),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _print_block("Process ID", process.pid)
            assert process.stdout is not None
            assert process.stderr is not None
            stdout_task = asyncio.create_task(_stream_pipe(process.stdout, sys.stdout))
            stderr_task = asyncio.create_task(_stream_pipe(process.stderr, sys.stderr))
            if process.stdin is not None:
                try:
                    process.stdin.write(stdin.encode("utf-8"))
                    await process.stdin.drain()
                except (BrokenPipeError, ConnectionResetError):
                    pass
                finally:
                    process.stdin.close()
                    try:
                        await process.stdin.wait_closed()
                    except (BrokenPipeError, ConnectionResetError):
                        pass
            stdout, stderr = await asyncio.gather(stdout_task, stderr_task)
            exit_code = await process.wait()
            launch_error = None
        except asyncio.CancelledError:
            if process and process.returncode is None:
                process.terminate()
                await process.wait()
            raise
        except Exception as exc:
            stdout = ""
            stderr = ""
            exit_code = None
            launch_error = f"{type(exc).__name__}: {exc}"
        finished_at = _timestamp()
        duration_seconds = monotonic() - started_clock
        result = {
            "ok": exit_code == 0 and launch_error is None,
            "plan_id": reservation["plan_id"],
            "step_id": step_id,
            "attempt_number": reservation["attempt_number"],
            "tool": tool_name,
            "action": action,
            "purpose": purpose,
            "expected_result": expected_result,
            "os": runtime.os_name,
            "distribution": runtime.distribution,
            "shell": runtime.shell,
            "cwd": str(working_directory),
            "command": command,
            "invocation": invocation,
            "stdin": stdin,
            "environment_overrides": overrides,
            "pid": process.pid if process else None,
            "started_at": started_at,
            "finished_at": finished_at,
            "duration_seconds": duration_seconds,
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "launch_error": launch_error,
        }
        plan_store.finish_execution(
            step_id=step_id,
            attempt_number=reservation["attempt_number"],
            result=result,
        )
        print()
        _print_block("Finished at", finished_at)
        _print_block("Duration seconds", duration_seconds)
        _print_block("Exit code", exit_code)
        _print_block("Launch error", launch_error)
        print("=" * 80 + "\n")
        return result
