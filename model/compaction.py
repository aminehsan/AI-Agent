from copy import copy

from agents import TResponseInputItem
from openai.types.responses import EasyInputMessageParam

from agent.runner import run_compaction

# def _compact_item(item: TResponseInputItem) -> TResponseInputItem | None:
#     if item.get("type") == "reasoning":
#         return None
#
#     if item.get("type") == "function_call_output":
#         compacted = copy(item)
#         compacted["output"] = "summarized output"
#         return compacted
#
#     return item
#
#
# def compact_inputs(input_items: list[TResponseInputItem]) -> list[TResponseInputItem]:
#     compacted_items: list[TResponseInputItem] = []
#     for item in input_items:
#         compacted_item = _compact_item(item)
#         if compacted_item is not None:
#             compacted_items.append(compacted_item)
#     return compacted_items


async def compact_inputs(input_items: list[TResponseInputItem]) -> list[TResponseInputItem]:
    compacted = await run_compaction(copy(input_items))
    compacted_items = [EasyInputMessageParam(role="user", content=compacted.final_output.strip())]
    return compacted_items
