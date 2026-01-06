# RVSmart Tool

LLM-driven Android testing tool with direct UIAutomator integration.

## Status

This module is not actively maintained. For LLM-driven Android testing, use **rv-agent** instead.

## Overview

RVSmart was an experimental tool that combined LLM integration with direct UIAutomator device interaction. It provided an alternative to the server-based architecture of rvandroid-tool.

### Key Differences from rv-agent

| Aspect | RVSmart | rv-agent |
|--------|---------|----------|
| Architecture | TestOrchestrator pattern | LangGraph workflow |
| Device Control | UIAutomator direct | UIAutomator direct |
| LLM Backend | Ollama/OpenAI via rv-llm | SGLang (OpenAI-compatible) |
| Exploration Strategy | LLM-only | Multimode (LLM + Algorithm) |
| State Management | Basic memory | Coordinated memory system |

## Dependencies

- rv-android-core
- rv-llm
- rv-screen-parser
- rv-tools
- rv-uiautomator

## See Also

- **rv-agent**: Main LLM-driven testing tool (`modules/rv-agent/`)
- Architecture documentation: `docs/rv_android_architecture.md`
