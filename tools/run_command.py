from __future__ import annotations
import json
from agents import function_tool
from pydantic import BaseModel, ConfigDict, Field
from .executor import execute_command
from .models import EnvironmentVariable


class RunCommandInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_id: int = Field(description="Current in-progress plan step.")
    purpose: str = Field(description="Why this single execution is needed now.")
    expected_result: str = Field(
        description="Concrete evidence expected from this execution."
    )
    command: str = Field(
        description="Complete native-shell command, including any pipelines."
    )
    cwd: str | None = Field(
        default=None,
        description="Process working directory. Null uses PROJECT_ROOT.",
    )
    stdin: str | None = Field(
        default=None,
        description="Complete standard input supplied before execution. Null closes stdin.",
    )
    environment: list[EnvironmentVariable] | None = Field(
        default=None,
        description="Environment-variable overrides for this process.",
    )


@function_tool
async def run_command(request: RunCommandInput) -> str:
    """Execute one unrestricted native-shell process and return every execution detail.

    Use this tool for Git, dependencies, tests, builds, pipelines, redirects, permissions, archives,
    and work not covered by filesystem. The shell is powershell.exe on Windows, bash on Debian-based
    Linux, and zsh on macOS. A current in-progress plan step is mandatory. Each call starts a fresh
    process in cwd, which defaults to PROJECT_ROOT; directory changes do not persist. Paths are
    unrestricted. There is no approval, timeout, output limit, or live interactive prompt. Supply
    stdin up front and prefer non-interactive flags. Nonzero exit codes and stderr are returned as
    data so the model can review the result before its next decision.

    Args:
        request: Command, plan context, cwd, stdin, and environment overrides for one process.
    """

    arguments = request.model_dump()
    if not request.command.strip():
        return json.dumps(
            {
                "ok": False,
                "stage": "command_generation",
                "error": "command cannot be empty.",
                "arguments": arguments,
            },
            ensure_ascii=False,
            indent=2,
        )
    environment_overrides = {
        item.name: item.value for item in request.environment or []
    }
    result = await execute_command(
        step_id=request.step_id,
        tool_name="run_command",
        action="run",
        purpose=request.purpose,
        expected_result=request.expected_result,
        command=request.command,
        cwd=request.cwd,
        stdin=request.stdin,
        environment_overrides=environment_overrides,
        tool_arguments=arguments,
    )
    return json.dumps(result, ensure_ascii=False, indent=2)
