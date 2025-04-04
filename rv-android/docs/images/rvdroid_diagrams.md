# RVDroid Architecture Diagrams

This document provides a list of all PlantUML diagrams for the RVDroid architecture documentation.

## Overview Diagrams

- **rvdroid_system_overview.puml**: High-level overview of RVDroid within the Android testing ecosystem
- **rvdroid_high_level_architecture.puml**: Main component architecture of RVDroid
- **rvdroid_data_flow.puml**: Data flow through the entire RVDroid system
- **rvdroid_component_interactions.puml**: Detailed component interactions sequence diagram

## Core Components

- **rvdroid_core_service.puml**: Core service architecture
- **rvdroid_memory_system.puml**: Memory system architecture with short-term and long-term storage
- **rvdroid_execution_system.puml**: Execution system architecture for interacting with Android devices
- **rvdroid_analysis_system.puml**: Analysis system for processing application states
- **rvdroid_strategy_framework.puml**: Testing strategy framework and implementations
- **rvdroid_llm_integration.puml**: LLM integration for AI-guided testing
- **rvdroid_orchestration_system.puml**: Lifecycle and resource management
- **rvdroid_extension_points.puml**: Extension points for customizing RVDroid

## Process Diagrams

- **rvdroid_testing_lifecycle.puml**: Complete testing lifecycle with all phases
- **rvdroid_action_generation.puml**: Action generation and execution process
- **rvdroid_memory_exploration.puml**: Memory-enhanced exploration process
- **rvdroid_llm_guided_testing.puml**: Process for LLM-guided testing decisions
- **rvdroid_recovery_process.puml**: Error recovery process flow

## Advanced Features

- **rvdroid_security_testing.puml**: Targeted security testing process
- **rvdroid_adaptive_strategy.puml**: Adaptive strategy selection process
- **rvdroid_form_completion.puml**: Intelligent form detection and completion

## Viewing and Editing

These diagrams can be viewed with any PlantUML viewer:

1. Online PlantUML server: http://www.plantuml.com/plantuml/
2. IntelliJ/VSCode with PlantUML plugins
3. Command line with PlantUML JAR

To convert to image formats (PNG or SVG), use:

```bash
# Using PlantUML JAR
java -jar plantuml.jar -tsvg rvdroid_*.puml

# Using Python module
python -m plantuml rvdroid_*.puml
```

## Online Viewing

To view these diagrams online, you can encode the PlantUML source and view it in the PlantUML server:

1. Open the PlantUML file
2. Compress and encode the source (tools like https://plantuml-editor.kkeisuke.dev/ can help)
3. View at: http://www.plantuml.com/plantuml/uml/{encoded-data}

## References in Documentation

To reference these diagrams in the architecture documentation, use:

```markdown
![Diagram Title](../images/diagram_filename.puml)
```

When converted to images, these references will be updated to point to the image files instead.