from agents import FunctionTool, function_tool

from .directory_creator import DirectoryCreator
from .directory_deleter import DirectoryDeleter
from .file_creator import FileCreator
from .file_deleter import FileDeleter
from .file_directory_tree import FileDirectoryTree
from .file_reader import FileReader
from .file_searcher import FileSearcher
from .project_path import get_project_path


def create_tools() -> list[FunctionTool]:
    return [
        function_tool(FileDirectoryTree().list_file_directory),
        function_tool(FileReader().read_file),
        function_tool(FileSearcher().search_files),
        function_tool(FileCreator().create_file),
        function_tool(DirectoryCreator().create_directory),
        function_tool(DirectoryDeleter().delete_directory),
        function_tool(FileDeleter().delete_file),
        function_tool(get_project_path),
    ]
