# RV-Agent: Autonomous Android Testing Agent

RV-Agent is an advanced, autonomous Android testing tool designed to explore applications using a combination of algorithmic strategies and Large Language Models (LLMs). It leverages the **LangChain** framework and **ReAct** (Reasoning and Acting) patterns to intelligently navigate, interact with, and test Android apps.

## 🚀 Key Features

-   **Autonomous Exploration**: Uses a coverage-optimized Depth-First Search (DFS) combined with LLM reasoning.
-   **Intelligent Strategy (`RVAgentStrategy`)**:
    -   **Successor Tracking**: Solves the "combobox problem" by tracking state transitions and re-enabling actions if successors are not fully explored.
    -   **Plateau Detection**: Automatically detects exploration stagnation and terminates or adjusts strategy.
    -   **MOP Prioritization**: Prioritizes actions that lead to Monitored Operations (security-sensitive methods).
-   **Multi-Mode Execution**:
    -   **`pure_algorithm`**: Fast, deterministic exploration without LLMs.
    -   **`llm_only`**: Pure LLM-driven exploration (experimental).
    -   **`multimode`**: Hybrid approach using algorithms for structure and LLMs for complex reasoning.
-   **SGLang Backend**:
    -   Uses **SGLang** with **Qwen3-VL-4B-Instruct** for multimodal inference
    -   OpenAI-compatible API for easy integration
    -   Native tool calling support via `--tool-call-parser qwen`
-   **Robust Architecture**: Built on `LangGraph` for stateful, resilient workflow orchestration.

## 🏗️ Architecture

The project follows a modular, component-based architecture:

```mermaid
graph TD
    CLI[CLI / Entry Point] --> Factory[AgentFactory]
    Factory --> Agent[RVAgent (LangGraph)]
    
    Agent --> Strategy[Exploration Strategy]
    Agent --> Memory[Memory Coordinator]
    Agent --> LLM[LLM Client]
    Agent --> Device[Device Interface]
    
    Strategy --> Tracker[Successor Tracker]
    Strategy --> Plateau[Plateau Detector]
    Strategy --> Metrics[Coverage Metrics]
    
    Memory --> Graph[Dynamic State Graph]
    Memory --> UI[UI Coverage Tracker]
    
    LLM --> SGLang[SGLang Server]
```

### Core Components

-   **`RVAgent`**: The central orchestrator using LangGraph. Manages the `parse -> decide -> execute -> learn` loop.
-   **`RVAgentStrategy`**: The default exploration brain. It maintains a `DynamicStateGraph` and decides the next best action based on coverage and priorities.
-   **`LLMClient`**: Handles multimodal interactions (text + screenshots) with various LLM backends.
-   **`MemoryCoordinator`**: Manages short-term (recent actions) and long-term (state graph) memory to prevent loops and ensure coverage.

## 🛠️ Installation

Prerequisites:
-   Python 3.12+
-   `poetry`
-   Android SDK (adb)

```bash
# Navigate to the module directory
cd modules/rv-agent

# Install dependencies
poetry install

# Activate virtual environment
poetry shell
```

## ⚙️ Configuration & Usage

RV-Agent can be configured via CLI arguments or environment variables.

### 1. Basic Usage (Standalone)

```bash
# Run with default settings (SGLang + Qwen3-VL)
rv-agent --package-name com.example.app --device emulator-5554
```

### 2. SGLang Server Configuration

RV-Agent uses **SGLang** with **Qwen3-VL-4B-Instruct** as the LLM backend. SGLang provides:
- OpenAI-compatible API
- Native tool calling via `--tool-call-parser qwen`
- High performance with FlashInfer attention

#### Starting the SGLang Server

```bash
# Install SGLang (if not already installed)
pip install sglang[all]

# Start SGLang server with Qwen3-VL
python -m sglang.launch_server \
    --model-path Qwen/Qwen3-VL-4B-Instruct \
    --port 30000 \
    --attention-backend flashinfer \
    --tool-call-parser qwen \
    --trust-remote-code
```

#### Connecting RV-Agent to SGLang

```bash
# Default configuration (localhost:30000)
rv-agent --package-name com.example.app

# Remote SGLang server
rv-agent --package-name com.example.app \
  --llm-base-url http://192.168.0.21:30000/v1

# Environment variable configuration
export RVAGENT_LLM_BASE_URL=http://192.168.0.21:30000/v1
rv-agent --package-name com.example.app
```

### 3. Exploration Modes

```bash
# Pure Algorithm (Fast, no LLM)
rv-agent --package-name com.example.app --agent-mode pure_algorithm

# Hybrid (Recommended)
rv-agent --package-name com.example.app --agent-mode multimode
```

## 📊 Validation Results

Based on comprehensive validation with **2,847 tests** from the rvsec-vision-llm benchmark:

-   **Model**: Qwen/Qwen3-VL-4B-Instruct via SGLang
-   **Hit Rate**: 57.7% (elements correctly identified)
-   **Tool Call Rate**: 90.3% (valid structured outputs)
-   **Coordinate System**: Normalized [0, 1000) with conversion to device space
-   **Optimal Configuration**: Temperature 0.25, Top-P 0.8, Top-K 50

## 📂 Project Structure

-   `src/rv_agent/agent/`: Main agent orchestration
    -   `rv_agent.py`: Central LangGraph orchestrator
    -   `nodes/`: Externalized workflow nodes (parse, decision, algorithm, llm, execute, learn)
-   `src/rv_agent/core/`: Core components (factory, dynamic graph, device interface)
-   `src/rv_agent/strategies/`: Exploration algorithms (`rvagent_strategy`, `dfs`, `bfs`, `greedy`)
-   `src/rv_agent/llm/`: LLM integration and tool definitions
-   `src/rv_agent/routing/`: Decision routing between LLM and algorithm paths
-   `src/rv_agent/memory/`: State management and coverage tracking
-   `src/rv_agent/ui/`: Screen parsing and element processing
-   `tests/`: Comprehensive unit and integration tests

## 🐛 Troubleshooting

### SGLang Connection Issues
If the agent cannot connect to SGLang:
1.  **Verify server is running**: `curl http://localhost:30000/health`
2.  **Check firewall**: Ensure port 30000 is accessible
3.  **Verify model loaded**: Check SGLang logs for model initialization

### Tool Calling Not Working
If the LLM outputs text instead of tool calls:
1.  **Ensure `--tool-call-parser qwen`** is passed to SGLang server
2.  **Check model**: Only Qwen3-VL models support native tool calling

### "Combobox Problem"
If the agent gets stuck re-opening a dropdown:
1.  The `SuccessorTracker` is designed to handle this.
2.  Ensure `enable_coordinate_enhancement` is True (default).