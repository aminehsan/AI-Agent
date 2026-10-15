from agents import FunctionTool, function_tool

from .file_creator import FileCreator
from .file_reader import FileReader
from .file_tree import FileTree
from .project_path import project_path


def get_tools() -> list[FunctionTool]:
    return [
        function_tool(FileTree().file_tree),
        function_tool(FileReader().file_reader),
        function_tool(FileCreator().file_creator),
        function_tool(project_path),
    ]
