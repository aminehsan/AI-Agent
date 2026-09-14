# AI-Agent
Programming agent built with the OpenAI Agents SDK. It supports OpenAI-compatible APIs.

## Run
Put the settings in `.env` and set the target project path.

```bash
python main.py
```

Project-specific state is stored in `<PROJECT_ROOT>/.agent/`. Switching
`PROJECT_ROOT` switches the files and conversation history used by the agent.

## Workflow

For a simple conversational request, the planner answers directly. For work that
needs project tools, it creates a small ordered plan containing a goal, success
criteria, and executable steps. The controller then runs one step at a time and
passes completed-step summaries and tool evidence to the next step.

The current workflow snapshot and its events are stored in
`<PROJECT_ROOT>/.agent/workflow.db`. Conversation history remains separate in
`conversation.db`.

The first version is intentionally linear: it has no dependency graph, plan
revision, or separate verifier agent. A step advances only after at least one
tool reports a successful result; failures stop the workflow as blocked.

prompt: `List files in this project.`

## OpenAI-compatible API
The provider must support the Responses API at `/v1/responses`.
`MODEL_KEY` is required. For a local endpoint without authentication.
