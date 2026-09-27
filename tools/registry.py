from agents import FunctionTool, function_tool
from tools.file_reader import FileReader
from tools.path import get_project_path


def get_tools() -> list[FunctionTool]:
    file_reader = FileReader()

    return [
        function_tool(get_project_path),
        function_tool(file_reader.read),
    ]
