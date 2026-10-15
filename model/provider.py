from agents import OpenAIResponsesModel
from openai import AsyncOpenAI

from settings import settings


def create_model() -> OpenAIResponsesModel:
    return OpenAIResponsesModel(
        model=settings.model_name,
        openai_client=AsyncOpenAI(
            api_key=settings.model_api_key,
            base_url=settings.model_base_url,
        ),
    )
