from agents import FunctionTool, function_tool

from .file_creator import FileCreator
from .file_reader import FileReader
from .files_list import FilesList
from .project_path import project_path


def get_tools() -> list[FunctionTool]:
    return [
        function_tool(FilesList().show_files),
        function_tool(FileReader().read_file),
        function_tool(FileCreator().create_file),
        function_tool(project_path),
    ]
