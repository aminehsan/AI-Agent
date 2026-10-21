from agents import OpenAIResponsesModel

from model.client import create_client
from settings import settings


def create_model() -> OpenAIResponsesModel:
    return OpenAIResponsesModel(
        model=settings.model_name,
        openai_client=create_client(),
    )
