# RV-Android Test Framework

A specialized framework for evaluating different configurations of AI-driven Android testing tools within the RV-Android modular ecosystem.

## Overview

The RV-Android Test Framework enables systematic evaluation of various testing configurations through parallel execution with intelligent resource management. It follows the "simplicity first" principle with maximum reuse of existing infrastructure.

## Key Features

- **Parallel Execution**: Model-grouped parallel execution with automatic emulator port allocation
- **Configuration Evaluation**: Predefined configurations for systematic testing
- **Metrics Collection**: Comprehensive metrics through post-execution parsing
- **Plateau Analysis**: Automatic timeout optimization recommendations
- **Simple Architecture**: Maximum reuse of existing rv-android components

## Architecture Principles

- **Module Integration**: Uses existing module interfaces without modifying business classes
- **User Responsibility**: Users manage worker count and configuration correctness
- **Existing Infrastructure**: 90%+ reuse of rv-android components
- **Predictable Behavior**: Simple, direct operation without complex automation

## Quick Start

```bash
# Install the module
cd modules
./install.sh rv-test-framework

# Run evaluation
rv-test-framework run --configs ./configs.json --apps ./apks_examples --workers 5

# Analyze results
rv-test-framework analyze --results-dir ./test_framework_results/run_20250825
```

## Integration Points

- **rv-platform**: Uses TaskExecutor and Platform for execution
- **rv-android-core**: Uses Task, ToolConfig, and infrastructure components
- **rvandroid-tool**: Creates RVAndroidTool instances for testing
- **rv-llm**: Uses LLMConfig for model management
- **rv-coverage**: Uses existing coverage analysis tools

## User Responsibility

Following the simplicity principle:
- Users define appropriate worker count for their system capacity
- Users ensure configuration correctness
- Users manage system resources adequately
- Framework provides predictable, direct behavior

## Results Compatibility

All results follow existing rv-experiment patterns and are compatible with existing analysis tools and report generators.