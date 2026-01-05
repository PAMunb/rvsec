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
-   **Flexible LLM Support**:
    -   **Ollama**: Easy local deployment (GGUF models).
    -   **vLLM**: High-performance production serving (OpenAI-compatible).
    -   **HuggingFace Direct**: Native execution using `transformers` (no server required).
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
    
    LLM --> Ollama[Ollama Provider]
    LLM --> vLLM[vLLM Provider]
    LLM --> HF[HF Direct Provider]
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
poetry install --extras "ollama anthropic"

# Activate virtual environment
poetry shell
```

## ⚙️ Configuration & Usage

RV-Agent can be configured via CLI arguments or environment variables.

### 1. Basic Usage (Standalone)

```bash
# Run with default settings (Ollama + Qwen3-VL)
rv-agent --package-name com.example.app --device emulator-5554
```

### 2. LLM Provider Configuration

#### Option A: Ollama (Default)
Easiest for local testing, but may suffer from token repetition bugs with some models.
```bash
# Ensure Ollama is running
ollama serve

# Run agent
rv-agent --package-name com.example.app --llm-provider ollama
```

#### Option B: vLLM (Recommended for Production)
High performance, no loop bugs.
```bash
# 1. Start vLLM server (OpenAI compatible)
python -m vllm.entrypoints.openai.api_server --model Qwen/Qwen3-VL-4B-Instruct --port 8000

# 2. Run agent pointing to vLLM
rv-agent --package-name com.example.app \
  --llm-provider vllm \
  --llm-base-url http://localhost:8000/v1
```

#### Option C: HuggingFace Direct
Runs the model natively in the agent process. Requires GPU.
```bash
export RVAGENT_LLM_PROVIDER=hf_direct
rv-agent --package-name com.example.app
```

### 3. Exploration Modes

```bash
# Pure Algorithm (Fast, no LLM)
rv-agent --package-name com.example.app --agent-mode pure_algorithm

# Hybrid (Recommended)
rv-agent --package-name com.example.app --agent-mode multimode
```

## 📊 Validation Results (Phase 0)

-   **Optimal Configuration**: Temperature 0.25, Top-P 0.8, Top-K 50.
-   **Success Rate**: Achieved **81.6%** success rate in validation benchmarks.
-   **Coordinate Enhancement**: Explicit coordinate guidance improved success rate from 30% to **100%** in complex UI scenarios.

## 📂 Project Structure

-   `src/rv_agent/core`: Main agent logic and factory.
-   `src/rv_agent/strategies`: Exploration algorithms (`rvagent_strategy`, `dfs`, etc.).
-   `src/rv_agent/llm`: LLM integration and tool definitions.
-   `src/rv_agent/memory`: State management and coverage tracking.
-   `src/rv_agent/ui`: Screen parsing and element processing.
-   `tests/`: Comprehensive unit and integration tests.

## 🐛 Troubleshooting

### Token Repetition / Infinite Loops
If you observe the LLM repeating the same text indefinitely:
1.  **Cause**: Known issue with Ollama's GGUF sampler for Qwen3-VL.
2.  **Fix**: Switch to **vLLM** or **HuggingFace Direct** provider.

### "Combobox Problem"
If the agent gets stuck re-opening a dropdown:
1.  The `SuccessorTracker` is designed to handle this.
2.  Ensure `enable_coordinate_enhancement` is True (default).