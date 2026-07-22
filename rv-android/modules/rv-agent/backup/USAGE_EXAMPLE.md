# RVAgent Usage Examples

This document demonstrates how to use the refactored RVAgent with the new modular architecture.

## Quick Start (AgentFactory)

The simplest way to create and run an agent:

```python
from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.core.agent_factory import AgentFactory

# Create configuration
config = RVAgentConfig(
    device_id="emulator-5554",
    package_name="br.unb.cic.cryptoapp",
    timeout=300,  # 5 minutes
    mode="pure_algorithm",  # or "llm_only", "multimode"
    strategy="dfs",
    llm_probability=0.5  # For multimode
)

# Create agent using factory
agent = AgentFactory.create_agent(config=config)

# Run exploration
results = agent.run()

# Check results
print(f"Status: {results['status']}")
print(f"Iterations: {results['iterations']}")
print(f"Unique states: {results['unique_states']}")
print(f"Execution time: {results['execution_time_s']:.1f}s")
```

## Mode Examples

### Pure Algorithm Mode (No LLM)
```python
config = RVAgentConfig(
    device_id="emulator-5554",
    package_name="com.example.app",
    mode="pure_algorithm",  # No LLM calls
    strategy="dfs",
    timeout=600
)

agent = AgentFactory.create_agent(config=config)
results = agent.run()
```

### LLM-Only Mode
```python
config = RVAgentConfig(
    device_id="emulator-5554",
    package_name="com.example.app",
    mode="llm_only",  # All decisions from LLM
    llm_model="qwen2-vl:7b",
    timeout=600
)

agent = AgentFactory.create_agent(config=config)
results = agent.run()
```

### Multimode (LLM + Algorithm with Fallback)
```python
config = RVAgentConfig(
    device_id="emulator-5554",
    package_name="com.example.app",
    mode="multimode",  # Mix of LLM and algorithm
    strategy="dfs",
    llm_model="qwen2-vl:7b",
    llm_probability=0.7,  # 70% LLM, 30% algorithm
    timeout=600
)

agent = AgentFactory.create_agent(config=config)
results = agent.run()

# Check decision distribution
print(f"LLM decisions: {results['llm_decisions']}")
print(f"Algorithm decisions: {results['algorithm_decisions']}")
```

## Advanced Usage

### With Static Analysis Data
```python
from rv_android_core.domain.static import StaticAnalysisData

# Load static analysis data
static_data = StaticAnalysisData.from_file("app_static_analysis.json")

# Create agent with static data
config = RVAgentConfig(
    device_id="emulator-5554",
    package_name="com.example.app",
    mode="pure_algorithm",
    strategy="dfs"
)

agent = AgentFactory.create_agent(
    config=config,
    static_data=static_data  # MOP guidance enabled
)

results = agent.run()
```

### With Custom Device (Testing)
```python
from rv_agent.core.device_interface import DeviceInterface

# Create custom device interface (e.g., mock for testing)
class MockDevice(DeviceInterface):
    def __init__(self):
        pass

    def launch_app(self, package_name):
        print(f"Mock: Launching {package_name}")

    # ... implement other methods

# Use custom device
config = RVAgentConfig(
    device_id="mock",
    package_name="com.example.app",
    mode="pure_algorithm"
)

mock_device = MockDevice()
agent = AgentFactory.create_agent(
    config=config,
    device=mock_device  # Inject custom device
)

results = agent.run()
```

## Manual Component Creation (Advanced)

For maximum control, you can instantiate components manually:

```python
from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.core.rv_agent import RVAgent
from rv_agent.core.device_interface import DeviceInterface
from rv_agent.core.dynamic_state_graph import DynamicStateGraph
from rv_agent.strategies.dfs_strategy import DFSStrategy
from rv_agent.vision.image_handler import ImageHandler
from rv_agent.ui.screen_processor import ScreenProcessor
from rv_agent.routing.routing_manager import RoutingManager
from rv_agent.routing.loop_detector import LoopDetector
from rv_agent.routing.fallback_manager import FallbackManager
from rv_agent.execution.tool_executor import ToolExecutor
from rv_agent.memory.memory_coordinator import MemoryCoordinator
from rv_agent.memory.agent_memory import AgentMemoryManager
from rv_agent.memory.short_term import ShortTermMemory
from rv_agent.memory.long_term import LongTermMemory
from rv_agent.memory.ui_coverage import UICoverageTracker
from rv_screen_parser.parser.screen.uiautomator.uiautomator_parser import UIAutomator2Parser
from rv_screen_parser.parser.screen.visitor.default_visitor import DefaultTextVisitor

# Create configuration
config = RVAgentConfig(device_id="emulator-5554", package_name="com.example.app")

# Create components manually
device = DeviceInterface(device_id=config.device_id)
dynamic_graph = DynamicStateGraph()
strategy = DFSStrategy(graph=dynamic_graph, static_data=None, coordinate_converter=None)
image_handler = ImageHandler(screenshot_dir="/tmp/screenshots")
parser = UIAutomator2Parser(DefaultTextVisitor)
screen_processor = ScreenProcessor(device=device, parser=parser)

# ... create remaining components

# Create agent
agent = RVAgent(
    config=config,
    device=device,
    dynamic_graph=dynamic_graph,
    exploration_strategy=strategy,
    image_handler=image_handler,
    screen_processor=screen_processor,
    llm_client=None,  # pure_algorithm mode
    routing_manager=routing_manager,
    tool_executor=tool_executor,
    memory_coordinator=memory_coordinator
)

results = agent.run()
```

## Configuration Options

### RVAgentConfig Parameters

```python
config = RVAgentConfig(
    # Required
    device_id="emulator-5554",
    package_name="com.example.app",

    # Mode selection
    mode="multimode",  # "pure_algorithm", "llm_only", "multimode"
    strategy="dfs",    # "dfs", "bfs", etc.

    # LLM configuration (for llm_only/multimode)
    llm_model="qwen2-vl:7b",
    llm_probability=0.5,  # Multimode: probability of using LLM
    prompt_version="v10",

    # Timeouts and limits
    timeout=600,  # Exploration timeout in seconds
    screenshot_rotation_limit=50,

    # Dimensions
    device_dimensions=(1080, 1920),
    optimized_dimensions=(704, 1248),  # For Qwen3-VL

    # Loop detection thresholds
    loop_threshold_click=3,
    loop_threshold_back=2,
    loop_threshold_scroll=4,

    # Paths
    screenshot_dir="/tmp/agent_screenshots"
)
```

## Result Structure

The `run()` method returns a dictionary with exploration metrics:

```python
results = agent.run()

# Results structure:
{
    "status": "completed",           # "completed", "error"
    "iterations": 150,               # Number of iterations
    "execution_time_s": 298.5,      # Execution time in seconds
    "unique_states": 45,            # Unique screens discovered
    "total_transitions": 120,       # State transitions
    "llm_tokens_input": 125000,     # LLM input tokens (if LLM used)
    "llm_tokens_output": 8500,      # LLM output tokens (if LLM used)
    "llm_time_ms": 45000.0,         # LLM time in milliseconds (if LLM used)
    "llm_decisions": 75,            # Decisions made by LLM
    "algorithm_decisions": 75       # Decisions made by algorithm
}
```

## Error Handling

```python
from rv_agent.core.agent_factory import AgentFactory

try:
    config = RVAgentConfig(
        device_id="emulator-5554",
        package_name="com.example.app",
        mode="llm_only"
    )

    agent = AgentFactory.create_agent(config=config)
    results = agent.run()

    if results["status"] == "error":
        print(f"Execution failed: {results.get('error')}")
    else:
        print(f"Success: {results['iterations']} iterations")

except ValueError as e:
    print(f"Configuration error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Best Practices

1. **Use AgentFactory for standard usage**
   - Simplest and most reliable way to create agents
   - Handles all component dependencies automatically
   - Validates configuration before creation

2. **Choose appropriate mode**
   - `pure_algorithm`: Fast, deterministic, no LLM costs
   - `llm_only`: Maximum intelligence, higher costs
   - `multimode`: Balanced approach with fallback

3. **Set reasonable timeouts**
   - Start with 5-10 minutes for initial exploration
   - Adjust based on app complexity
   - Monitor iteration count vs. timeout

4. **Monitor metrics**
   - Track unique states vs. iterations
   - Check LLM token usage for cost estimation
   - Analyze decision distribution in multimode

5. **Use static analysis when available**
   - Improves MOP-guided exploration
   - Prioritizes security-relevant paths
   - Enhances coverage quality
