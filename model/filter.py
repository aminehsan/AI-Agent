from copy import deepcopy

from agents import TResponseInputItem
from agents.run import CallModelData, ModelInputData


def _filter_item(item: TResponseInputItem) -> TResponseInputItem | None:
    if item.get("type") == "reasoning":
        return None

    if item.get("type") == "function_call_output":
        copy_item = deepcopy(item)
        copy_item["output"] = "filtered output"
        return copy_item

    return item


def _filter_input(input: list[TResponseInputItem]) -> list[TResponseInputItem]:
    filtered_items: list[TResponseInputItem] = []
    for item in input:
        if filtered_item := _filter_item(item):
            filtered_items.append(filtered_item)
    return filtered_items


def _filter_instructions(instructions: str | None) -> str | None:
    return instructions


def filter_input(data: CallModelData) -> ModelInputData:
    return ModelInputData(
        input=_filter_input(data.model_data.input),
        instructions=_filter_instructions(data.model_data.instructions),
    )
