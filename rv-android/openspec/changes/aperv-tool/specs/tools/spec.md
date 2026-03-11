## ADDED Requirements

### Requirement: ApeRVTool External Registration (FR18, FR19, NFR02)

`_register_external_tools()` in `rv_platform/__init__.py` SHALL include an idempotent registration block for `ApeRVTool`, placed after the `RVSmartTool` registration block. The structure MUST follow the same pattern as the existing `RVSmartTool` block: check `is_tool_registered("aperv")`, attempt `from aperv_tool.tools.aperv.tool import ApeRVTool`, catch `ImportError` as warning and any other exception as error. This registration makes `aperv` available to `ToolFactory` and `ToolRegistry` whenever `rv_platform` is imported and `aperv-tool` is installed.

#### Scenario: aperv registered alongside rvsmart
- **WHEN** `import rv_platform` is executed and both `rvsmart-tool` and `aperv-tool` are installed
- **THEN** both `"rvsmart"` and `"aperv"` SHALL be registered in `ToolRegistry`
- **AND** `ToolRegistry.get_instance().list_tools()` SHALL contain both `"rvsmart"` and `"aperv"`

#### Scenario: aperv registration isolated from rvsmart registration
- **WHEN** `aperv-tool` raises `ImportError` during registration
- **THEN** `"rvsmart"` SHALL still be registered and functional
- **AND** `"aperv"` SHALL NOT appear in `ToolRegistry`
