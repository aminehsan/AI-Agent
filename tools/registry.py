from agents import FunctionTool, function_tool

from tools.file_list import FileList
from tools.file_read import FileRead
from tools.file_writ import FileWrit
from tools.path import get_project_path


def get_tools() -> list[FunctionTool]:
    file_list = FileList()
    file_reader = FileRead()
    file_writer = FileWrit()

    return [
        function_tool(file_list.run),
        function_tool(file_reader.run),
        function_tool(file_writer.run),
        function_tool(get_project_path),
    ]
