from agents import OpenAIResponsesModel, set_tracing_disabled
from openai import AsyncOpenAI

from config import settings


def create_model() -> OpenAIResponsesModel:
    set_tracing_disabled(True)
    return OpenAIResponsesModel(
        model=settings.model_name,
        openai_client=AsyncOpenAI(
            base_url=settings.model_base_url,
            api_key=settings.model_api_key,
        ),
    )
