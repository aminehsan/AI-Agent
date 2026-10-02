from abc import ABC, abstractmethod
from typing import Any


class Tool(ABC):
    @abstractmethod
    def run(self, *args: Any, **kwargs: Any) -> Any:
        """Run the tool."""
