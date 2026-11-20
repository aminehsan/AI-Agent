from settings import settings

from .utility import format_path


class ProjectPath:
    @staticmethod
    def show_project_path() -> str:
        """
        Show the absolute root path of the current project.
        Returns:
            The formatted absolute project path.
        """

        return format_path(settings.project_root)
