from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class AgentTool(ABC):
    """Base contract for an agent tool.

    Subclasses set ``name``, ``description`` and ``input_model`` and implement
    ``execute``. ``tool_schema`` returns a provider-agnostic dict ready to be
    adapted to an LLM function/tool definition later.
    """

    name: str
    description: str
    input_model: type[BaseModel]

    @abstractmethod
    def execute(self, payload: BaseModel) -> Any:
        """Run the tool against the given validated input."""

    def tool_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_model.model_json_schema(),
        }
