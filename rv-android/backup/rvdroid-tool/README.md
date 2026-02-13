# RVDroid Tool

Android testing tool with LLM guidance using UIAutomator.

## Status

This module is not actively maintained. For LLM-driven Android testing, use **rv-agent** instead.

## Overview

RVDroid was an experimental tool that used LLM as guidance for exploration decisions rather than direct action generation. It explored an alternative approach where algorithmic exploration is enhanced by LLM suggestions.

### Key Differences from rv-agent

| Aspect | RVDroid | rv-agent |
|--------|---------|----------|
| LLM Role | Guidance only | Action generation |
| Architecture | Plugin-based | LangGraph workflow |
| Device Control | UIAutomator | UIAutomator |
| Exploration Strategy | Algorithm with LLM hints | Multimode (LLM + Algorithm) |

## Dependencies

- rv-android-core
- rv-screen-parser
- rv-llm
- rv-tools
- rv-uiautomator

## See Also

- **rv-agent**: Main LLM-driven testing tool (`modules/rv-agent/`)
- Architecture documentation: `docs/rv_android_architecture.md`
