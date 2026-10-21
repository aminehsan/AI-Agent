from openai import AsyncOpenAI

from settings import settings


def create_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.model_api_key,
        base_url=settings.model_base_url,
    )
