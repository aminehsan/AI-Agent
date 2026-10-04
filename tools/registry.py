from agents import FunctionTool, function_tool

from tools.file_list import FileList
from tools.file_read import FileRead
from tools.file_write import FileWrite
from tools.path import project_path


def get_tools() -> list[FunctionTool]:
    return [
        function_tool(FileList().show_files_and_directories),
        function_tool(FileRead().read_file),
        function_tool(FileWrite().write_file),
        function_tool(project_path),
    ]
