from agents import FunctionTool, function_tool

from tools.file_reader import FileReader
from tools.file_writer import FileWriter
from tools.path import get_project_path


def get_tools() -> list[FunctionTool]:
    file_reader = FileReader()
    file_writer = FileWriter()

    return [
        function_tool(get_project_path),
        function_tool(file_reader.read),
        function_tool(file_writer.write),
    ]
