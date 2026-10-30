from agents import FunctionTool, function_tool

from .directory_creator import DirectoryCreator
from .file_creator import FileCreator
from .file_reader import FileReader
from .file_tree import FileTree
from .project_path import get_project_path


def create_tools() -> list[FunctionTool]:
    return [
        function_tool(FileTree().list_directory),
        function_tool(FileReader().read_file),
        function_tool(FileCreator().create_file),
        function_tool(DirectoryCreator().create_directory),
        function_tool(get_project_path),
    ]
