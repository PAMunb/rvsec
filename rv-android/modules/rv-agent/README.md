# RV-Agent

Autonomous Android testing agent with LangChain and ReAct pattern.

## Overview

RV-Agent represents the next evolution of AI-driven Android testing tools in the RV-Android ecosystem. It uses LangChain framework with ReAct (Reasoning and Acting) patterns to autonomously explore Android applications.

## Key Features

- **Autonomous Testing**: ReAct pattern for intelligent exploration
- **Coordinate Enhancement**: 100% success rate with explicit coordinate guidance
- **Process Isolation**: Standalone execution with full framework support
- **LangChain Integration**: Direct integration with Ollama, Anthropic, OpenAI
- **Scientific Validation**: Based on Phase 0 validation results

## Installation

```bash
cd modules/rv-agent
poetry install --extras "ollama anthropic"
```

## Usage

### Standalone Mode
```bash
rv-agent --package-name com.example.app --device emulator-5554 --timeout 300
```

### With Custom Configuration
```bash
rv-agent --package-name com.example.app --llm-model qwen2.5vl:7b --temperature 0.25
```

## Architecture

- **MVP-First Strategy**: Standalone client with optional server integration
- **Memory Components**: Long-term and short-term memory for context
- **UI Coverage Tracking**: Smart element discovery and testing
- **Debug Logging**: Extensive logging with `[RVAGENT_DEBUG]` prefixes

## Phase 0 Validation Results

- **Medium Scale**: 72.1% success rate (43 test cases)
- **Extensive Prototype**: 65.2% success rate (2,250 tests)
- **Overnight Analysis**: 68.7% success rate (9,855 tests)
- **Optimal Configuration**: T0.25_P0.8_K50 with 81.6% success rate
- **Coordinate Enhancement**: 100% vs 30% success rate with explicit coordinates