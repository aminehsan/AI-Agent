from openai import AsyncOpenAI
from agents import OpenAIResponsesModel, set_tracing_disabled
from settings import settings


def create_model() -> OpenAIResponsesModel:
    if settings.model_url:
        set_tracing_disabled(True)
    client = AsyncOpenAI(
        base_url=settings.model_url,
        api_key=settings.model_key.get_secret_value(),
    )
    return OpenAIResponsesModel(
        model=settings.model_name,
        openai_client=client,
    )
