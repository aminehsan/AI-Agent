from agents import function_tool
from settings import settings


@function_tool
def get_project_path() -> str:
    """The path of the project you are working on."""
    return settings.project_root
