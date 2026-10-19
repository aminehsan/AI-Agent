from agents.run import CallModelData, ModelInputData

from .compaction import compact_inputs


async def filter_input(data: CallModelData) -> ModelInputData:
    compacted_inputs = await compact_inputs(data.model_data.input)
    return ModelInputData(
        input=compacted_inputs,
        instructions=data.model_data.instructions,
    )
