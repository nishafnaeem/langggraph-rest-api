# LangGraph REST API

A REST API for creating, managing, and executing LangGraph workflows using the official LangGraph Python SDK. This API allows you to build dynamic graph-based applications with nodes and edges through HTTP endpoints, perfect for creating complex AI agent workflows and data processing pipelines.

## 🚀 Features

- ✅ **Create and manage graphs** using LangGraph StateGraph
- ✅ **Add nodes** with Function or Agent configurations  
- ✅ **Manage edges** between nodes dynamically
- ✅ **Execute graphs** with custom input data
- ✅ **Visual graph representation** via ASCII output
- ✅ **In-memory storage** for fast development and testing

## 📋 Requirements

- Python 3.11+
- FastAPI
- LangGraph
- Pydantic
- uvicorn

## 🛠️ Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd langgraph-rest-api
   ```

2. **Install dependencies using uv (recommended):**
   ```bash
   uv sync
   ```

   Or with pip:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables (optional):**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys (OpenAI, Groq, etc.)
   ```

## 🏃 Running the Server

Start the API server:

```bash
# Using uv
uv run python -m api.main

# Or directly
python -m api.main
```

The server will start on `http://localhost:8000`

### API Documentation

Once running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 📚 API Reference

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check |
| `POST` | `/graph` | Create a new graph |
| `GET` | `/graph/{graph_id}` | Get graph ASCII visualization |
| `POST` | `/graph/{graph_id}/run` | Execute graph with input data |
| `POST` | `/graph/{graph_id}/node` | Add a node to the graph |
| `DELETE` | `/graph/{graph_id}/node` | Add a node to the graph |
| `POST` | `/graph/{graph_id}/edge` | Add an edge between nodes |
| `PUT` | `/graph/{graph_id}/edge` | Update an edge between nodes |
| `PUT` | `/graph/{graph_id}/node/{node_name}` | Update node configuration |
| `DELETE` | `/graph/{graph_id}/edge` | Remove an edge |

### Data Models

#### GraphState
The state object that flows through your graph:

```python
class GraphState(TypedDict):
    input: Annotated[list[str], add]        # Input data for nodes
    output: Annotated[dict[str, Any], update_dict]  # Shared outputs from all nodes
```

#### Node Types

**Function Node:**
```python
class FunctionNodeConfig(BaseModel):
    name: str
    output: str | None = None
```

**Agent Node:**
```python  
class AgentNodeConfig(BaseModel):
    name: str
    prompt: str | None = None
```

#### Edge Operations
```python
class EdgeRequest(BaseModel):
    source: str  # Source node name
    target: str  # Target node name
```

## Example Usage

### Creating a Simple Linear Workflow

```python
import requests

# 1. Create graph
response = requests.post("http://localhost:8000/graphs", json={
    "name": "Text Processing Pipeline",
    "description": "A linear text processing workflow"
})
graph_id = response.json()["graph_id"]

# 2. Add first node (no connections needed)
validate_code = '''
def validate_input(state):
    data = state.get("data", {})
    text = data.get("input", "")
    if not text: raise ValueError("No input provided")
    return {**state, "data": {**data, "validated": True}}
'''
requests.post(f"http://localhost:8000/graphs/{graph_id}/nodes", json={
    "node_id": "validator",
    "function_name": "validate_input",
    "function_code": validate_code
})

# 3. Add second node that comes AFTER validator  
process_code = '''
def process_text(state):
    data = state.get("data", {})
    text = data.get("input", "")
    processed = text.upper()
    return {
        "messages": state.get("messages", []) + [f"Processed: {processed}"],
        "data": {**data, "output": processed}
    }
'''
requests.post(f"http://localhost:8000/graphs/{graph_id}/nodes", json={
    "node_id": "processor", 
    "function_name": "process_text",
    "function_code": process_code,
    "before_node": "validator"  # Creates: validator → processor
})

# 4. Insert a quality check node between validator and processor
quality_code = '''
def quality_check(state):
    data = state.get("data", {})
    return {**state, "data": {**data, "quality_checked": True}}
'''
requests.post(f"http://localhost:8000/graphs/{graph_id}/nodes", json={
    "node_id": "quality_checker",
    "function_name": "quality_check", 
    "function_code": quality_code,
    "before_node": "validator",    # validator → quality_checker
    "after_node": "processor"      # quality_checker → processor
    # This automatically removes the direct validator → processor edge
})

# 5. Check the graph structure
structure = requests.get(f"http://localhost:8000/graphs/{graph_id}/structure")
print("Graph flow:", " -> ".join([f"{e['from']} -> {e['to']}" for e in structure.json()['edges']]))

# 6. Invoke the graph
result = requests.post(f"http://localhost:8000/graphs/{graph_id}/invoke", json={
    "input_data": {"input": "hello world"}
})
print(result.json())
```

### Advanced Connection Examples

```python
# Example 1: Linear chain - add nodes sequentially
requests.post(f"http://localhost:8000/graphs/{graph_id}/nodes", json={
    "node_id": "step_2",
    "function_name": "step_2_func",
    "function_code": "def step_2_func(state): return state",
    "before_node": "step_1"  # step_1 → step_2
})

# Example 2: Create parallel paths - same before_node, different after_nodes
# First create: A → B → D
requests.post(f"http://localhost:8000/graphs/{graph_id}/nodes", json={
    "node_id": "node_c",
    "function_name": "process_c",
    "function_code": "def process_c(state): return state", 
    "before_node": "node_a",  # A → C
    "after_node": "node_d"    # C → D (creates parallel path A→C→D alongside A→B→D)
})

# Example 3: Insert middleware between existing nodes
requests.post(f"http://localhost:8000/graphs/{graph_id}/nodes", json={
    "node_id": "middleware",
    "function_name": "middleware_func", 
    "function_code": "def middleware_func(state): return state",
    "before_node": "existing_node_1",  # existing_node_1 → middleware
    "after_node": "existing_node_2"    # middleware → existing_node_2
    # Removes direct existing_node_1 → existing_node_2 if it exists
})

### Node Function Requirements

Node functions must:
1. Accept a `state` parameter (dictionary)
2. Return a dictionary with `messages` and `data` keys
3. Be valid Python code that can be executed with `exec()`

Example node function:
```python
def my_node_function(state):
    # Access current state
    data = state.get("data", {})
    messages = state.get("messages", [])
    
    # Process data
    result = "some processing result"
    
    # Return updated state
    return {
        "messages": messages + ["Processing complete"],
        "data": {**data, "result": result}
    }
```

## State Structure

The graph state follows this structure:
```python
{
    "messages": [],  # List of messages/logs
    "data": {}       # Arbitrary data dictionary
}
```

## 🧪 Testing

### Comprehensive Test Suite

Run the comprehensive test example to see all features in action:

```bash
python examples/comprehensive_test.py
```

This test script demonstrates:

- ✅ **Server health checks**
- ✅ **Graph creation and management**  
- ✅ **Adding multiple node types**
- ✅ **Edge management (add/remove)**
- ✅ **Node configuration updates**
- ✅ **Graph execution with real data**
- ✅ **Error handling and validation**
- ✅ **Complete workflow examples**

### Other Examples

Explore additional examples in the `examples/` folder:

```bash
# Simple parallel processing example
python examples/parallel_graph_example.py

# Enhanced workflow example  
python examples/enhanced_example.py

# Graph creation patterns
python examples/graph_creation_example.py
```

## 🏗️ Architecture

### Project Structure
```
langgraph-rest-api/
├── api/
│   ├── __init__.py
│   ├── main.py          # FastAPI application
│   └── _types.py        # Pydantic models and types
├── examples/
│   ├── comprehensive_test.py     # Full test suite
│   ├── parallel_graph_example.py
│   └── ...
├── .env.example         # Environment template
├── pyproject.toml       # Dependencies
└── README.md
```

### Key Components

1. **StateGraph Management**: Uses LangGraph's `StateGraph` for workflow orchestration
2. **Type Safety**: Pydantic models ensure API contract compliance  
3. **Dynamic Node Creation**: Support for both function and agent nodes
4. **Real-time Execution**: Compile and execute graphs on-demand
5. **ASCII Visualization**: Built-in graph structure visualization

## 🔧 Configuration

### Environment Variables

Create a `.env` file for API keys and configuration:

```bash
ANTHROPIC_API_KEY=your_key_here
```


🎉 **Ready to build powerful LangGraph workflows with REST APIs!**

Start by running `python examples/comprehensive_test.py` to see the full capabilities in action.
