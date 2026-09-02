# AI-Agent
Programming agent built with the OpenAI Agents SDK. It supports OpenAI-compatible APIs.

## Run
Put the settings in `.env`
```bash
python main.py "Write a Python hello world"
python main.py "List files in this project"
```

## OpenAI-compatible API
Set `API_MODE=responses` when the provider supports the Responses API.
Use `chat_completions` for providers that only implement Chat Completions.
`API_KEY` is required. For a local endpoint without authentication.
