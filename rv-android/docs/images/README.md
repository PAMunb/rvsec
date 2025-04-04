# Test Framework Diagrams

This directory contains the architectural and process diagrams for the RV-Android Test Framework. The diagrams are available in two formats:

1. **PlantUML Files (.puml)** - Source files that can be edited and regenerated
2. **SVG Files (.svg)** - Vector graphics for use in documentation

## Diagram List

| Diagram | Description |
|---------|-------------|
| tf_architecture_overview | High-level overview of the Test Framework within the RV-Android ecosystem |
| tf_high_level_architecture | Main component architecture of the Test Framework |
| tf_configuration_flow | The configuration validation and processing workflow |
| tf_execution_process | Sequence diagram for test execution |
| tf_analysis_pipeline | Data flow for test result analysis |
| tf_advanced_analysis | Advanced analysis components and relationships |
| tf_data_flow | Comprehensive data flow through the framework |
| tf_test_suite_execution | Complete test suite execution process |
| tf_plateau_analysis | Plateau analysis process for optimal timeouts |
| tf_correlation_analysis | Correlation between app characteristics and configurations |
| tf_component_interactions | Component interaction flows |
| tf_extension_points | Extension points in the framework |
| tf_basic_testing | Basic testing user flow |
| tf_comparative_analysis | Comparative analysis process |
| tf_plateau_identification | Plateau identification process |
| tf_app_analysis | App characteristic analysis process |

## Usage

These diagrams are referenced in the Test Framework architecture documentation (`tf_design.md`). The SVG format allows for direct embedding in markdown documents.

## Updating Diagrams

1. Edit the PlantUML (.puml) files as needed
2. Run the `convert_to_svg.sh` script to regenerate the SVG files:

```bash
bash convert_to_svg.sh
```

For more detailed descriptions of each diagram, see `diagram_descriptions.md` in this directory.