from agents.run import CallModelData, ModelInputData

from model.compaction import compaction_input


def filter_input(data: CallModelData) -> ModelInputData:
    return ModelInputData(
        input=compaction_input(data.model_data.input),
        instructions=data.model_data.instructions,
    )
