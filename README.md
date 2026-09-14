# AI-Agent
Programming agent built with the OpenAI Agents SDK. It supports OpenAI-compatible APIs.

## Run
Put the settings in `.env` and set the target project path.

```bash
python main.py
```

Project-specific state is stored in `<PROJECT_ROOT>/.agent/`. Switching
`PROJECT_ROOT` switches the files and conversation history used by the agent.

prompt: `List files in this project.`

## OpenAI-compatible API
The provider must support the Responses API at `/v1/responses`.
`MODEL_KEY` is required. For a local endpoint without authentication.
