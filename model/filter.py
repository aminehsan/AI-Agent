from agents.run import CallModelData, ModelInputData


def filter_input(data: CallModelData) -> ModelInputData:
    return ModelInputData(
        input=data.model_data.input,
        instructions=data.model_data.instructions,
    )
