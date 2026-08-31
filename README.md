# AI-Agent

Minimal programming agent built with the OpenAI Agents SDK. It supports OpenAI
and OpenAI-compatible APIs.

## Run

Use the project virtual environment for every Python and pip command.

```powershell
$env:OPENAI_API_KEY = "your-api-key"
.\.venv\Scripts\python.exe .\main.py "Write a Python hello world"
.\.venv\Scripts\python.exe .\main.py "List files in this project"
```

To use another model:

```powershell
$env:OPENAI_MODEL = "gpt-5.6-sol"
.\.venv\Scripts\python.exe .\main.py "Explain this error"
```

## OpenAI-compatible API

Use `responses` when the provider supports the Responses API:

```powershell
$env:OPENAI_BASE_URL = "http://localhost:8000/v1"
$env:OPENAI_API_KEY = "provider-api-key"
$env:OPENAI_MODEL = "provider-model-name"
$env:OPENAI_API_MODE = "responses"
.\.venv\Scripts\python.exe .\main.py "List files in this project"
```

Use `chat_completions` for providers that only implement Chat Completions:

```powershell
$env:OPENAI_API_MODE = "chat_completions"
.\.venv\Scripts\python.exe .\main.py "List files in this project"
```

`OPENAI_API_KEY` is optional for a local endpoint without authentication. The
provider must support function tools for `list_files` to work.
