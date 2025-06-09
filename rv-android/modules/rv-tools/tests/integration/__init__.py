"""
Integration tests for RV-Tools registry and plugin system workflows.

This package contains comprehensive integration tests that validate
end-to-end workflows and component interactions within the monitored
operations testing tool registry and plugin system.

### Integration Test Categories:
- **test_registry_integration.py**: End-to-end registry workflows and tool management
- **test_plugin_integration.py**: Plugin system integration and external tool workflows

### Integration Testing Strategy:
- Tests complete workflows from tool registration to execution
- Validates component interactions and data flow
- Tests real-world usage patterns and scenarios
- Verifies system behavior under load and stress conditions
- Tests error recovery and resilience patterns

### Key Integration Areas:
- Registry-Factory-Tool creation workflows
- Plugin discovery-loading-registration pipelines
- Tool configuration inheritance and merging
- Multi-tool execution and coordination
- Error propagation and recovery across components
- Performance and scalability under realistic loads

### Architectural Compliance:
- Tests rv-android-core infrastructure integration
- Validates "monitored operations" terminology consistency
- Tests architectural patterns and design principles
- Verifies logging and error handling integration
"""