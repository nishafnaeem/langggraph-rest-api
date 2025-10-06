from fastapi import FastAPI, HTTPException
from typing import Any
from langgraph.graph import StateGraph, START, END
from langgraph.config import RunnableConfig
from _types import (
    AgentNodeConfig,
    AddEdgeRequest,
    FunctionNodeConfig,
    GraphState,
    AddNodeRequest,
    UpdateEdgeRequest,
    RuntimeContext,
)
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv
from langgraph.runtime import Runtime
from config import settings


load_dotenv(".env")
# FastAPI instance

app = FastAPI()

# In-memory storage for LangGraph objects and metadata
graphs: dict[int, StateGraph] = {}  # Store metadata and node functions
graphs_runnable_config: dict[int, dict[str, Any]] = (
    {}
)  # Store runnable config for each graph
graph_id: int = 0


@app.get("/")
def main():
    return {"message": "LangGraph REST API is running"}


@app.post("/graphs/{graph_id}/node/{node_id}/config/update")
def create_or_update_config(
    graph_id: int, node_id: str, config: FunctionNodeConfig | AgentNodeConfig
):
    if graph_id not in graphs:
        raise HTTPException(status_code=404, detail="Graph not found")

    graph = graphs[graph_id]
    graph.nodes[node_id].metadata = config.__dict__

    return {"message": f"Config for graph {graph_id} created/updated successfully."}


@app.post("/create_graph")
def create_graph():
    global graph_id
    graph_id += 1
    builder = StateGraph(GraphState)
    graphs[graph_id] = builder
    return {"graph_id": graph_id}


@app.post("/graphs/{graph_id}/add_node")
def add_node(
    graph_id: int,
    request: AddNodeRequest,
):
    if graph_id not in graphs:
        raise HTTPException(status_code=404, detail="Graph not found")

    graph = graphs[graph_id]

    def function_node(
        state: GraphState, config: RunnableConfig, runtime: Runtime[RuntimeContext]
    ) -> GraphState:
        if "output" not in state:
            state["output"] = {}
        state["output"][config["metadata"]["name"]] = config["metadata"].get("output")
        return state

    def agent_node(
        state: GraphState, config: RunnableConfig, runtime: Runtime[RuntimeContext]
    ) -> GraphState:
        input_messages = []
        if config["metadata"].get("input_nodes"):
            for input_node in config["metadata"]["input_nodes"]:
                input_messages.append(
                    {"role": "user", "content": state["output"][input_node]}
                )

        agent = create_react_agent(
            model=f"{runtime.context.llm_provider}:{runtime.context.llm_model}",
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

    add_edges(
        graph_id,
        request.config.name,
        UpdateEdgeRequest(
            before_nodes=request.before_nodes, after_nodes=request.after_nodes
        ),
    )
    graph.compile()
    return {"message": f"Node {request.config.name} added to graph {graph_id}"}


@app.post("/graphs/{graph_id}/node/{node_id}/edges/add")
def add_edges(graph_id: int, node_id: str, request: AddEdgeRequest):
    if graph_id not in graphs:
        raise HTTPException(status_code=404, detail="Graph not found")

    graph = graphs[graph_id]
    before_nodes = request.before_nodes
    after_nodes = request.after_nodes

    if before_nodes:
        for before_node in before_nodes:
            if before_node == "START":
                before_node = START
            graph.add_edge(before_node, node_id)
    if after_nodes:
        for after_node in after_nodes:
            if after_node == "END":
                after_node = END
            graph.add_edge(node_id, after_node)

    return {"message": f"Edges added for node {node_id} in graph {graph_id}"}


@app.post("/graphs/{graph_id}/node/{node_id}/edges/update")
def update_edges(graph_id: int, node_id: str, request: UpdateEdgeRequest):
    if graph_id not in graphs:
        raise HTTPException(status_code=404, detail="Graph not found")

    remove_edges(graph_id, node_id)
    add_edges(
        graph_id,
        node_id,
        AddEdgeRequest(
            before_nodes=request.before_nodes, after_nodes=request.after_nodes
        ),
    )
    return {"message": f"Edges updated for node {node_id} in graph {graph_id}"}


@app.post("/graphs/{graph_id}/node/{node_id}/edges/remove")
def remove_edges(graph_id: int, node_id: str):
    if graph_id not in graphs:
        raise HTTPException(status_code=404, detail="Graph not found")

    graph = graphs[graph_id]
    final_edges = set()
    for edge in graph.edges:
        if node_id in edge[0] or node_id in edge[1]:
            continue

        final_edges.add(edge)
    graph.edges = final_edges
    return {"message": f"Edges removed for node {node_id} in graph {graph_id}"}


@app.post("/graphs/{graph_id}/run")
def run_graph(graph_id: int, input_data: dict[str, Any]):
    if graph_id not in graphs:
        raise HTTPException(status_code=404, detail="Graph not found")

    graph = graphs[graph_id]

    try:
        initial_state: GraphState = {"input": [input_data["text"]]}

        compiled_graph = graph.compile()
        result = compiled_graph.invoke(
            initial_state,
            context=RuntimeContext(
                llm_provider=settings.llm_provider, llm_model=settings.llm_model
            ),
        )
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph execution failed: {str(e)}")


@app.post("/graphs/{graph_id}")
def get_graph(graph_id: int):
    if graph_id not in graphs:
        raise HTTPException(status_code=404, detail="Graph not found")

    compiled_graph = graphs[graph_id].compile()
    graph = compiled_graph.get_graph().draw_ascii()
    return {"graph": graph}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
