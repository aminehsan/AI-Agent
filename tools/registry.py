from agents import FunctionTool, function_tool
from tools.file import FileReader
from tools.path import get_project_path


def get_tools() -> list[FunctionTool]:
    return [
        function_tool(get_project_path),
        function_tool(FileReader().read_file),
    ]
