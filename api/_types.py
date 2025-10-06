from pydantic import BaseModel
from typing import Any, Annotated
from typing_extensions import TypedDict
from operator import add


def update_dict(a: dict, b: dict) -> dict:
    """Merges dictionary 'b' into dictionary 'a'."""
    a.update(b)
    return a

# This is our graph state for now
class GraphState(TypedDict):
    # Represents the input for the currently executing node - it's up to the executing node to set this value
    input: Annotated[list[str], add]
    # Shared dict to store the outputs of every node
    output: Annotated[dict[str, Any], update_dict]

class BaseNodeConfig(BaseModel):
    name: str


class FunctionNodeConfig(BaseNodeConfig):
    output: str | None = None


class AgentNodeConfig(BaseNodeConfig):
    prompt: str | None = None


class AddNodeRequest(BaseModel):
    config: FunctionNodeConfig | AgentNodeConfig


class EdgeRequest(BaseModel):
    source: str
    target: str


class AddEdgeRequest(EdgeRequest):
    ...


class DeleteEdgeRequest(EdgeRequest):
    ...


class RuntimeContext(BaseModel):
    llm_provider: str
    llm_model: str
