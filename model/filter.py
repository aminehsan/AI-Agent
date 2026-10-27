from agents import TResponseInputItem
from agents.run import CallModelData, ModelInputData


def _filter_input_items(input_items: list[TResponseInputItem]) -> list[TResponseInputItem]:
    return input_items


def _filter_instructions(instructions: str | None) -> str | None:
    return instructions


def filter_model_input(call_data: CallModelData) -> ModelInputData:
    return ModelInputData(
        input=_filter_input_items(call_data.model_data.input),
        instructions=_filter_instructions(call_data.model_data.instructions),
    )
