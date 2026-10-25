from agents import OpenAIResponsesModel

from model.client import create_openai_client
from settings import settings


def create_responses_model() -> OpenAIResponsesModel:
    return OpenAIResponsesModel(
        model=settings.model_name,
        openai_client=create_openai_client(),
    )
