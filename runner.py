from __future__ import annotations
from agents import RawResponsesStreamEvent, RunConfig, Runner, ToolExecutionConfig
from openai.types.responses import (
    ResponseReasoningSummaryTextDeltaEvent,
    ResponseTextDeltaEvent,
)
from app.agent import create_agent
from app.input import get_input
from app.plan import plan_store
from app.session import create_session
from app.settings import settings
from tools.environment import (
    EnvironmentDetectionError,
    configure_utf8_stdio,
    get_runtime_environment,
)


async def _stream_run(agent, prompt: str, session, run_config: RunConfig):
    result = Runner.run_streamed(
        starting_agent=agent,
        input=prompt,
        session=session,
        max_turns=None,
        run_config=run_config,
    )
    reasoning_started = False
    message_started = False
    async for event in result.stream_events():
        if not isinstance(event, RawResponsesStreamEvent):
            continue
        if isinstance(event.data, ResponseReasoningSummaryTextDeltaEvent):
            if not reasoning_started:
                print("\nReasoning:")
                reasoning_started = True
            print(event.data.delta, end="", flush=True)
        elif isinstance(event.data, ResponseTextDeltaEvent):
            if not message_started:
                print("\n\nAgent message:")
                message_started = True
            print(event.data.delta, end="", flush=True)
    if reasoning_started or message_started:
        print()
    return result


async def run_agent() -> None:
    configure_utf8_stdio()
    try:
        environment = get_runtime_environment()
    except EnvironmentDetectionError as exc:
        raise SystemExit(f"Environment detection failed: {exc}") from exc
    print("Runtime environment:")
    print(f"\toperating_system={environment.os_name}")
    print(f"\tdistribution={environment.distribution or 'not applicable'}")
    print(f"\tshell={environment.shell}")
    print(f"\tproject_root={settings.project_root}")
    print("\ttool_execution=sequential")
    print("\tcommand_timeout=disabled")
    print("\toutput_limit=disabled\n")
    user_input = await get_input()
    plan_store.begin_request(user_input)
    agent = create_agent()
    session = create_session()
    run_config = RunConfig(
        tool_execution=ToolExecutionConfig(max_function_tool_concurrency=1)
    )
    prompt = user_input
    input_tokens = 0
    output_tokens = 0
    total_tokens = 0
    continuation = 0
    while True:
        result = await _stream_run(agent, prompt, session, run_config)
        usage = result.context_wrapper.usage
        input_tokens += usage.input_tokens
        output_tokens += usage.output_tokens
        total_tokens += usage.total_tokens
        if plan_store.current_request_is_complete():
            break
        continuation += 1
        print("\n" + "!" * 80)
        print("PLAN GATE: The model stopped before completing the current request.")
        print(
            "The response above is not final. The agent will continue from this plan state:"
        )
        print(plan_store.prompt_snapshot())
        print("!" * 80 + "\n")
        prompt = (
            "Continue the current request. Your previous response was not accepted because the "
            "persistent plan is incomplete. Inspect the current plan state in your instructions, "
            "perform the next required plan transition or execution, review every result, finish "
            "the plan only when the original goal is achieved, and then provide the final answer."
        )
    print(
        "\n"
        "Token usage:\n"
        f"\tinput={input_tokens}\n"
        f"\toutput={output_tokens}\n"
        f"\ttotal={total_tokens}\n"
        f"\tcontinuations={continuation}"
    )
