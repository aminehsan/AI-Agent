# AI-Agent

A transparent, plan-driven programming agent built with the OpenAI Agents SDK and the Responses
API. It uses the host operating system's default shell and supports OpenAI-compatible endpoints.

## Runtime

The agent detects the environment when it starts:

- Windows: `powershell.exe`
- Debian-based Linux: `/bin/bash`
- macOS: `/bin/zsh`

If the operating system is unsupported or the required shell is missing, startup stops with a clear
error. Every command runs in a new process. Its default working directory is `PROJECT_ROOT`, and a
relative or absolute `cwd` can be supplied for a particular execution.

## Tools

The model receives three tools:

- `plan`: creates and advances the mandatory persistent execution plan.
- `filesystem`: generates standard native commands for inspect, write, remove, transfer, and search.
- `run_command`: executes unrestricted native-shell commands, including pipelines and redirects.

The filesystem tool uses the same command executor as the raw command tool. There is no path
boundary, approval, timeout, or output limit. Commands should use non-interactive flags; complete
standard input can be supplied before execution.

Only one tool process runs at a time. Standard output and standard error stream live to the terminal
and are also returned in full to the model after the process exits. Every result includes the OS,
shell, working directory, command, invocation, stdin, environment overrides, process ID, timestamps,
duration, exit code, stdout, stderr, and launch error.

## Mandatory plan lifecycle

Every request follows this state machine:

```text
create plan -> start step -> execute one command -> review result -> next step -> finish plan
```

The execution tools reject calls without a current `in_progress` step. After a command, that step is
`awaiting_review`, and no next command can run until the model reviews the result. If the model tries
to answer before the plan is finished, the runner continues the agent with the persisted plan state.
Steps must start in order, and a failed step requires an explicit plan revision before work continues.

Plan state and full command attempts are stored per `SESSION_ID` in `<PROJECT_ROOT>/.agent/` and
survive application restarts.

## Configuration

Copy `.env.example` to `.env` and set the model and project values:

```dotenv
MODEL_URL=http://localhost:11434/v1/
MODEL_KEY=ollama
MODEL_NAME=your-responses-model
AGENT_NAME='Coding Assistant'
AGENT_INSTRUCTIONS='You are a programming assistant.'
PROJECT_ROOT=C:/path/to/project
```

The provider must support the Responses API at `/v1/responses` and function calling.

## Run

Use the project's virtual environment:

```powershell
.\.venv\Scripts\python.exe .\main.py
```

## Tests

Run the complete suite with the same virtual environment:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

The suite executes the Windows command and filesystem path end to end. It validates Debian and
macOS detection and command generation without pretending to execute those operating systems on a
Windows host.
