from json import dumps

from agents import TResponseInputItem
from openai.types.responses import EasyInputMessageParam

from agent.runner import run_summarizer


def _serialize_input_items(input_items: list[TResponseInputItem]) -> str:
    return dumps(input_items, ensure_ascii=False, separators=(",", ":"), default=str)


def _estimate_input_tokens(input_items: list[TResponseInputItem]) -> int:
    return len(_serialize_input_items(input_items).encode("utf-8")) // 4


def _find_current_turn_start_index(input_items: list[TResponseInputItem]) -> int:
    for index in range(len(input_items) - 1, -1, -1):
        if input_items[index].get("phase") == "final_answer":
            return index + 1
    return 1


async def compact_input_items(input_items: list[TResponseInputItem]) -> list[TResponseInputItem]:
    if _estimate_input_tokens(input_items) < 1:
        return input_items
    current_turn_start_index = _find_current_turn_start_index(input_items)
    if current_turn_start_index == 1:
        return input_items
    previous_turn_items = input_items[:current_turn_start_index]
    current_turn_items = input_items[current_turn_start_index:]
    summarizer_result = await run_summarizer(previous_turn_items)
    summary_message = EasyInputMessageParam(
        content=(
            "Previous conversation summary (context, not a new request):\n"
            f"{summarizer_result.final_output.strip()}"
        ),
        role="assistant",
        phase="final_answer",
        type="message",
    )
    return [summary_message, *current_turn_items]
