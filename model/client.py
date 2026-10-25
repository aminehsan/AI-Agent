from openai import AsyncOpenAI

from settings import settings


def create_openai_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.model_api_key.get_secret_value(),
        base_url=settings.model_base_url,
    )
