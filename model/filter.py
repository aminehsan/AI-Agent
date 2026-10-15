from agents.run import CallModelData, ModelInputData

from .compaction import compact_input


def filter_input(data: CallModelData) -> ModelInputData:
    return ModelInputData(
        input=compact_input(data.model_data.input),
        instructions=data.model_data.instructions,
    )
