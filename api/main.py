from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Any
from langgraph.runtime import Runtime
from langgraph.graph import StateGraph, START, END
from langgraph.config import RunnableConfig
from _types import (
    AgentNodeConfig,
    AddNodeRequest,
    AddEdgeRequest,
    DeleteEdgeRequest,
    FunctionNodeConfig,
    GraphState,
    RuntimeContext,
)
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage
from config import settings


app = FastAPI()
origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for LangGraph objects and metadata
graphs: dict[int, StateGraph] = {}  # Store metadata and node functions
# graphs_runnable_config: dict[int, dict[str, Any]] = (
#     {}
# )  # Store runnable config for each graph
graph_id: int = 0


@app.get("/")
def main():
    return {"message": "LangGraph REST API is running"}


@app.post("/graph")
def create_graph():
    global graph_id
    graph_id += 1
    builder = StateGraph(GraphState)
    graphs[graph_id] = builder
    return {"graph_id": graph_id}


@app.get("/graph/{graph_id}")
def get_graph(graph_id: int):
    if graph_id not in graphs:
        raise HTTPException(status_code=404, detail="Graph not found")

    compiled_graph = graphs[graph_id].compile()
    graph = compiled_graph.get_graph().draw_ascii()
    return {"graph": graph}


@app.post("/graph/{graph_id}/run")
def run_graph(graph_id: int, input_data: dict[str, Any]):
    if graph_id not in graphs:
        raise HTTPException(status_code=404, detail="Graph not found")

    graph = graphs[graph_id]

    try:
        print("Running graph with input:", input_data)
        initial_state: GraphState = {
            "input": [input_data["text"]],
            "context": RuntimeContext(
                llm_provider=settings.llm_provider, llm_model=settings.llm_model
            ),
        }
        compiled_graph = graph.compile()
        print("compiled!")
        result = compiled_graph.invoke(initial_state)
        print("finished!")
        print(result)
        return {"result": result}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=f"Graph execution failed: {str(e)}")


@app.post("/graph/{graph_id}/node")
def add_node(
    graph_id: int,
    request: AddNodeRequest,
):
    if graph_id not in graphs:
        raise HTTPException(status_code=404, detail="Graph not found")

    graph = graphs[graph_id]

    def function_node(
        state: GraphState, config: RunnableConfig, runtime: Runtime
    ) -> GraphState:
        if "output" not in state:
            state["output"] = {}
        state["output"][config["metadata"]["name"]] = config["metadata"].get("output")
        return state

    def agent_node(
        state: GraphState, config: RunnableConfig, runtime: Runtime
    ) -> GraphState:
        input_messages = []

        # Read the outputs from GraphState for nodes that target this node with an edge,
        # then push them into input_messages as user messages
        current_node_name = config["metadata"]["name"]

        # Find all edges that target this node
        for edge in graph.edges:
            source_node, target_node = edge

            # Check if this edge targets our current node
            if target_node == current_node_name:
                # Get the output from the source node if it exists in state
                if "output" in state and source_node in state["output"]:
                    source_output = state["output"][source_node]
                    if source_output:  # Only add if there's actual content
                        input_messages.append(HumanMessage(content=str(source_output)))

        # If no incoming messages and there's a general input, use that
        if not input_messages and "input" in state and state["input"]:
            input_messages.append(HumanMessage(content=state["input"]))

        print("input_messages")
        print(input_messages)
        agent = create_react_agent(
            # model="anthropic:claude-3-7-sonnet-latest",
            model=f"{runtime.context['llm_provider']}:{runtime.context['llm_model']}",
            tools=[],
            prompt=config["metadata"].get("prompt"),
        )

        response = agent.invoke({"messages": input_messages})
        if len(response["messages"]) == 0:
            raise HTTPException(
                status_code=500, detail="Agent did not return any messages"
            )

        last_message = response["messages"][-1]
        if hasattr(last_message, "content"):
            last_message = last_message.content

        state["output"][config["metadata"]["name"]] = last_message
        return state

    # Add the node to the graph
    if isinstance(request.config, AgentNodeConfig):
        graph.add_node(
            request.config.name, agent_node, metadata=request.config.__dict__
        )
    else:
        graph.add_node(
            request.config.name, function_node, metadata=request.config.__dict__
        )

    return {"message": f"Node {request.config.name} added to graph {graph_id}"}


@app.put("/graph/{graph_id}/node/{node_id}")
def update_node(
    graph_id: int, node_id: str, config: FunctionNodeConfig | AgentNodeConfig
):
    if graph_id not in graphs:
        raise HTTPException(status_code=404, detail="Graph not found")

    graph = graphs[graph_id]

    # Check if the node exists
    if node_id not in graph.nodes:
        raise HTTPException(status_code=404, detail="Node not found")

    # Preserve all edges connected to this node
    preserved_edges = []
    for edge in graph.edges:
        source, target = edge
        # Convert START/END back to string representations for consistency
        source_str = "start" if source == START else source
        target_str = "end" if target == END else target

        # Save edges where this node is either source or target
        if source == node_id or target == node_id:
            preserved_edges.append((source_str, target_str))

    delete_node(graph_id, node_id)
    updated_config = config.model_copy(update={"name": node_id})
    add_node(graph_id, AddNodeRequest(config=updated_config))

    # Restore all preserved edges
    for source, target in preserved_edges:
        try:
            graph.add_edge(
                START if source == "start" else source,
                END if target == "end" else target,
            )
        except Exception as e:
            # Log the error but continue with other edges
            print(f"Warning: Could not restore edge {source} -> {target}: {e}")

    return {"message": f"Config for graph {graph_id} created/updated successfully."}


@app.delete("/graph/{graph_id}/node/{node_id}")
def delete_node(graph_id: int, node_id: str):
    if graph_id not in graphs:
        raise HTTPException(status_code=404, detail="Graph not found")

    graph = graphs[graph_id]
    if node_id not in graph.nodes:
        raise HTTPException(status_code=404, detail="Node not found")

    # Remove the node from the nodes dictionary
    graph.nodes.pop(node_id)

    # Remove any edges that reference this node
    edges_to_remove = []
    for edge in graph.edges:
        source, target = edge
        if source == node_id or target == node_id:
            edges_to_remove.append(edge)

    for edge in edges_to_remove:
        graph.edges.remove(edge)

    return {"message": f"Node {node_id} deleted from graph {graph_id}"}


@app.post("/graph/{graph_id}/edge")
def add_edge(graph_id: int, request: AddEdgeRequest):
    if graph_id not in graphs:
        raise HTTPException(status_code=404, detail="Graph not found")

    graphs[graph_id].add_edge(
        START if request.source == "start" else request.source,
        END if request.target == "end" else request.target,
    )

    return {"message": f"Edge {request.source} to {request.target} added."}


@app.delete("/graph/{graph_id}/edge")
def delete_edge(graph_id: int, request: DeleteEdgeRequest):
    if graph_id not in graphs:
        raise HTTPException(status_code=404, detail="Graph not found")

    graph = graphs[graph_id]
    graph.edges.remove(
        (
            START if request.source == "start" else request.source,
            END if request.target == "end" else request.target,
        )
    )

    return {"message": f"Edge {request.source} to {request.target} removed."}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
