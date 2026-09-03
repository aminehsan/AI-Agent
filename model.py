from openai import AsyncOpenAI
from agents import OpenAIResponsesModel, set_tracing_disabled
from settings import settings


def create_model() -> OpenAIResponsesModel:
    if settings.base_url:
        set_tracing_disabled(True)
    client = AsyncOpenAI(
        base_url=settings.base_url,
        api_key=settings.api_key.get_secret_value(),
    )
    return OpenAIResponsesModel(
        model=settings.model,
        openai_client=client,
    )
