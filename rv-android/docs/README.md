# RV-Android Documentation

This directory contains the technical documentation for the RV-Android system, including its components and tools.

## Structure

- `images/` - Diagrams in both PlantUML and image formats
- `tf_*.md` - Test Framework documentation
- `rvdroid/` - RVDroid documentation
- `examples/` - Example configuration files and scripts
- `rv_android_usage.md` - Comprehensive usage guide for the rv-android platform

## Key Documentation

### Platform Documentation

- [RV-Android Usage Guide](rv_android_usage.md) - Complete guide for running experiments with the platform
- [Example Configuration File](examples/example_config.json) - Example JSON configuration for complex experiments

### Test Framework Documentation

- [Test Framework Architecture](tf_design.md) - Design and architecture of the test framework
- [Test Framework Usage Guide](tf_usage.md) - How to use the test framework for systematic tool evaluation
- [Example Test Suite](tf_example_suite.json) - Example configuration for comprehensive testing
- [Example Plateau Analysis](tf_example_plateau.json) - Example configuration for timeout plateau analysis

### RVDroid Documentation

- [RVDroid Architecture](rvdroid/rvdroid_architecture.md) - Overview of the RVDroid system architecture
- [RVDroid Diagrams](images/rvdroid_diagrams.md) - Index of all RVDroid architecture diagrams

## Generating Documentation

The repository includes a script to convert PlantUML diagrams to images and update the references in markdown files.

### Requirements

```bash
pip install plantuml markdown
```

### Usage

To convert PlantUML diagrams to SVG and update references:

```bash
./generate_documentation.py
```

Options:

- `--format svg|png` - Output format (default: svg)
- `--embed` - Embed images directly in markdown files instead of linking
- `--dir PATH` - Root directory to process (default: current docs directory)

Examples:

```bash
# Convert to PNG instead of SVG
./generate_documentation.py --format png

# Embed images directly in the markdown files
./generate_documentation.py --embed

# Process a specific directory
./generate_documentation.py --dir /path/to/docs
```

## Editing Diagrams

1. Edit the PlantUML files (`.puml`) in the `images/` directory
2. Run the `generate_documentation.py` script to update the images and references
3. If needed, manually adjust the references in the markdown files

## Viewing Documentation

The markdown files can be viewed with any markdown viewer. For the best experience with diagrams:

- Use a viewer that supports SVG images for regular references
- Use a viewer that supports HTML for embedded diagrams (when using the `--embed` option)

## Adding New Documentation

1. Create a new markdown file with the appropriate prefix (e.g., `tf_` for Test Framework, `rvdroid_` for RVDroid)
2. Create any needed diagrams as PlantUML files in the `images/` directory
3. Reference the diagrams in your markdown file using the format: `![Description](../images/diagram_name.puml)`
4. Run the `generate_documentation.py` script to generate images and update references