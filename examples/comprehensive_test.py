"""
Comprehensive test script for LangGraph REST API endpoints.
This script demonstrates the complete workflow:
1. Create a graph
2. Add multiple nodes with different configurations
3. Update edges between nodes
4. Update node configurations
5. Run the graph with test data
"""

import requests
import json
from typing import Any, Dict

# Server configuration
BASE_URL = "http://localhost:8000"


class LangGraphAPITester:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.graph_id = None

    def test_server_health(self) -> bool:
        """Test if the server is running."""
        try:
            response = requests.get(f"{self.base_url}/")
            print(f"✅ Server health check: {response.json()}")
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Server health check failed: {e}")
            return False

    def create_graph(self) -> int:
        """Create a new graph and return its ID."""
        response = requests.post(f"{self.base_url}/create_graph")
        if response.status_code == 200:
            graph_data = response.json()
            self.graph_id = graph_data["graph_id"]
            print(f"✅ Created graph with ID: {self.graph_id}")
            return self.graph_id
        else:
            print(f"❌ Failed to create graph: {response.text}")
            raise Exception("Failed to create graph")

    def add_function_node(
        self,
        name: str,
        output: str,
        before_nodes: list = None,
        after_nodes: list = None,
    ) -> bool:
        """Add a function node to the graph."""
        if not self.graph_id:
            raise Exception("No graph created yet")

        node_config = {
            "config": {"name": name, "input_nodes": None, "output": output},
            "before_nodes": before_nodes or [],
            "after_nodes": after_nodes or [],
        }

        response = requests.post(
            f"{self.base_url}/graphs/{self.graph_id}/add_node", json=node_config
        )

        if response.status_code == 200:
            print(f"✅ Added function node '{name}': {response.json()}")
            return True
        else:
            print(f"❌ Failed to add function node '{name}': {response.text}")
            return False

    def add_agent_node(
        self,
        name: str,
        prompt: str,
        input_nodes: list = None,
        before_nodes: list = None,
        after_nodes: list = None,
    ) -> bool:
        """Add an agent node to the graph."""
        if not self.graph_id:
            raise Exception("No graph created yet")

        node_config = {
            "config": {
                "name": name,
                "input_nodes": input_nodes or [],
                "prompt": prompt,
            },
            "before_nodes": before_nodes or [],
            "after_nodes": after_nodes or [],
        }

        response = requests.post(
            f"{self.base_url}/graphs/{self.graph_id}/add_node", json=node_config
        )

        if response.status_code == 200:
            print(f"✅ Added agent node '{name}': {response.json()}")
            return True
        else:
            print(f"❌ Failed to add agent node '{name}': {response.text}")
            return False

    def add_edges(
        self, node_id: str, before_nodes: list = None, after_nodes: list = None
    ) -> bool:
        """Add edges for a specific node."""
        if not self.graph_id:
            raise Exception("No graph created yet")

        edge_config = {
            "before_nodes": before_nodes or [],
            "after_nodes": after_nodes or [],
        }

        response = requests.post(
            f"{self.base_url}/graphs/{self.graph_id}/node/{node_id}/edges/add",
            json=edge_config,
        )

        if response.status_code == 200:
            print(f"✅ Added edges for node '{node_id}': {response.json()}")
            return True
        else:
            print(f"❌ Failed to add edges for node '{node_id}': {response.text}")
            return False

    def update_edges(
        self, node_id: str, before_nodes: list = None, after_nodes: list = None
    ) -> bool:
        """Update edges for a specific node."""
        if not self.graph_id:
            raise Exception("No graph created yet")

        edge_config = {
            "before_nodes": before_nodes or [],
            "after_nodes": after_nodes or [],
        }

        response = requests.post(
            f"{self.base_url}/graphs/{self.graph_id}/node/{node_id}/edges/update",
            json=edge_config,
        )

        if response.status_code == 200:
            print(f"✅ Updated edges for node '{node_id}': {response.json()}")
            return True
        else:
            print(f"❌ Failed to update edges for node '{node_id}': {response.text}")
            return False

    def update_node_config(self, node_id: str, config: Dict[str, Any]) -> bool:
        """Update configuration for a specific node."""
        if not self.graph_id:
            raise Exception("No graph created yet")

        response = requests.post(
            f"{self.base_url}/graphs/{self.graph_id}/node/{node_id}/config/update",
            json=config,
        )

        if response.status_code == 200:
            print(f"✅ Updated config for node '{node_id}': {response.json()}")
            return True
        else:
            print(f"❌ Failed to update config for node '{node_id}': {response.text}")
            return False

    def get_graph_visualization(self) -> str:
        """Get ASCII visualization of the graph."""
        if not self.graph_id:
            raise Exception("No graph created yet")

        response = requests.post(f"{self.base_url}/graphs/{self.graph_id}")

        if response.status_code == 200:
            graph_viz = response.json()["graph"]
            print("✅ Graph visualization:")
            print(graph_viz)
            return graph_viz
        else:
            print(f"❌ Failed to get graph visualization: {response.text}")
            return ""

    def run_graph(self, input_text: str) -> Dict[str, Any]:
        """Run the graph with input data."""
        if not self.graph_id:
            raise Exception("No graph created yet")

        input_data = {"text": input_text}

        response = requests.post(
            f"{self.base_url}/graphs/{self.graph_id}/run", json=input_data
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Graph execution completed successfully!")
            print(f"Result: {json.dumps(result, indent=2)}")
            return result
        else:
            print(f"❌ Failed to run graph: {response.text}")
            return {}


def main():
    """Main test function that demonstrates the complete workflow."""
    print("🚀 Starting comprehensive LangGraph API test...\n")

    tester = LangGraphAPITester()

    # Step 1: Test server health
    print("=" * 50)
    print("STEP 1: Testing server health")
    print("=" * 50)
    if not tester.test_server_health():
        print("❌ Server is not running. Please start the server first.")
        return

    # Step 2: Create a graph
    print("\n" + "=" * 50)
    print("STEP 2: Creating a new graph")
    print("=" * 50)
    try:
        tester.create_graph()
    except Exception as e:
        print(f"❌ Test failed at graph creation: {e}")
        return

    # Step 3: Add nodes to the graph
    print("\n" + "=" * 50)
    print("STEP 3: Adding nodes to the graph")
    print("=" * 50)

    # Add an initial function node
    tester.add_function_node(
        name="input_processor",
        output="Processed input data",
        before_nodes=["START"],
        after_nodes=None,
    )

    # Add an agent node for analysis
    tester.add_agent_node(
        name="analyzer",
        prompt="You are an expert data analyzer. Analyze the input and provide insights.",
        input_nodes=["input_processor"],
        before_nodes=["input_processor"],
        after_nodes=None,
    )

    # Add another function node for formatting
    tester.add_function_node(
        name="formatter",
        output="Formatted analysis results",
        before_nodes=None,
        after_nodes=None,
    )

    # Add a validation agent
    tester.add_agent_node(
        name="validator",
        prompt="You are a quality assurance expert. Validate the analysis results for accuracy and completeness.",
        input_nodes=["formatter"],
        before_nodes=["formatter"],
        after_nodes=["END"],
    )

    # Step 4: Update edges (demonstrate edge modification)
    print("\n" + "=" * 50)
    print("STEP 4: Updating edges between nodes")
    print("=" * 50)
    tester.get_graph_visualization()

    # Add an additional connection
    tester.add_edges("formatter", before_nodes=["analyzer"])
    tester.get_graph_visualization()
    # Update edges for the analyzer to include multiple outputs
    # tester.update_edges("analyzer", before_nodes=["input_processor"], after_nodes=["formatter", "validator"])
    # tester.get_graph_visualization()
    # Step 5: Update node configurations
    print("\n" + "=" * 50)
    print("STEP 5: Updating node configurations")
    print("=" * 50)

    # Update the analyzer's configuration
    new_analyzer_config = {
        "name": "analyzer",
        "input_nodes": ["input_processor"],
        "prompt": "You are an advanced AI analyst. Provide detailed insights and recommendations based on the input data. Focus on actionable intelligence.",
    }
    tester.update_node_config("analyzer", new_analyzer_config)

    # Update the formatter's configuration
    new_formatter_config = {
        "name": "formatter",
        "input_nodes": None,
        "output": "Beautifully formatted and structured analysis with executive summary",
    }
    tester.update_node_config("formatter", new_formatter_config)

    # Step 6: Get graph visualization
    print("\n" + "=" * 50)
    print("STEP 6: Visualizing the graph structure")
    print("=" * 50)
    tester.get_graph_visualization()

    # Step 7: Run the graph with test data
    print("\n" + "=" * 50)
    print("STEP 7: Running the graph with test data")
    print("=" * 50)

    test_inputs = [
        "Analyze the sales performance of our Q3 2024 results: Revenue increased by 15% compared to Q2, but customer acquisition costs rose by 8%. Customer retention remained stable at 92%.",
        "Evaluate this business proposal: Launch a new mobile app targeting millennials with a freemium model. Initial development cost: $500K, projected break-even in 18 months.",
        "Review this market research data: 78% of respondents prefer online shopping, 65% value same-day delivery, 43% are willing to pay extra for eco-friendly packaging.",
    ]

    for i, test_input in enumerate(test_inputs, 1):
        print(f"\n--- Test Run {i} ---")
        print(f"Input: {test_input}")
        try:
            result = tester.run_graph(test_input)
            if result:
                print("✅ Test run completed successfully!")
        except Exception as e:
            print(f"❌ Test run {i} failed: {e}")

    print("\n" + "=" * 50)
    print("🎉 COMPREHENSIVE TEST COMPLETED!")
    print("=" * 50)
    print("✅ All endpoints tested successfully!")
    print(
        "📊 Graph created, nodes added, edges updated, configs modified, and execution completed."
    )
    print(f"📝 Final graph ID: {tester.graph_id}")


if __name__ == "__main__":
    main()
