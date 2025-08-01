# RV-Android: Runtime Verification for Android Applications

A modular framework for runtime verification of Android applications, supporting monitored operations through JavaMOP and RV-Monitor integration. Enables monitoring of both JCA (Java Cryptographic Architecture) and generic programming patterns.

## 🏗️ Architecture Overview

RV-Android uses a modular Poetry workspace architecture optimized for development productivity while maintaining clear separation of concerns:

```
rv-android/
├── modules/                          # 📦 Independent modules
│   ├── rv-android-core/             # 🧠 Core infrastructure
│   ├── rv-monitor-generator/        # 🔧 Monitor generation
│   ├── rv-instrumentation/          # 📱 APK instrumentation
│   ├── rv-static-analysis/          # 🔍 Static analysis tools
│   ├── rv-coverage/                 # 📊 Coverage analysis
│   ├── rv-screen-parser/            # 📱 UI parsing framework
│   ├── rv-llm/                      # 🤖 LLM integration
│   ├── rv-tools/                    # 🛠️ Testing tools registry
│   ├── rv-experiment/               # 🧪 Experiment framework
│   ├── rvandroid-tool/              # 🎯 AI-driven testing server
│   └── rvandroid/                   # 📦 Tool registry and patterns
├── pyproject.toml                   # 📋 Workspace configuration
└── modules/install.sh               # 🚀 Module installer
```

### Modules Overview

| Module | Purpose | README |
|--------|---------|--------|
| **rv-android-core** | Foundation infrastructure (ErrorHandler, EventBus, domain models) | [📖](modules/rv-android-core/README.md) |
| **rv-monitor-generator** | JavaMOP/RV-Monitor integration for generating monitors | [📖](modules/rv-monitor-generator/README.md) |
| **rv-instrumentation** | APK instrumentation with monitor weaving | [📖](modules/rv-instrumentation/README.md) |
| **rv-static-analysis** | Static analysis tools (GATOR, GESDA, REACH) | [📖](modules/rv-static-analysis/README.md) |
| **rv-coverage** | Coverage analysis and tracking | [📖](modules/rv-coverage/README.md) |
| **rv-screen-parser** | Android UI parsing with visitor patterns | [📖](modules/rv-screen-parser/README.md) |
| **rv-llm** | Language model integration framework | [📖](modules/rv-llm/README.md) |
| **rv-tools** | Testing tool plugin system | [📖](modules/rv-tools/README.md) |
| **rv-experiment** | Experiment orchestration and coordination | [📖](modules/rv-experiment/README.md) |
| **rvandroid-tool** | AI-driven testing server with LLM integration | [📖](modules/rvandroid-tool/README.md) |
| **rvandroid** | Tool registry and UI pattern detection | [📖](modules/rvandroid/README.md) |

## 🚀 Quick Start Guide

### 1. First-Time Setup (New Project)

**Prerequisites:**
- Python 3.12+
- Java 21+
- Aspectj 1.9.24
- Android SDK
- RVSEC environment


**Complete setup sequence:**

```bash
# 1. Install RVSEC (required for monitor generation)
cd /path/to/rvsec
./configure.sh
mvn clean install -DskipTests -DskipMopAgent

# 2. Set environment variables
export RVSEC_HOME="/path/to/rvsec"
export ANDROID_HOME="/path/to/android-sdk"
export RV_PYDANTIC=true  # Enable validation in development

# 3. Setup RV-Android
cd rv-android

# 4. Install all modules in dependency order
cd modules
./install.sh

# 5. Verify installation
cd ..
poetry run python -c "import rv_android_core, rv_monitor_generator; print('✅ Setup complete')"
```

### 2. Development Update (Existing Project)

```bash
# 1. Pull latest changes
git pull

# 2. Update dependencies across all modules
cd modules
./install.sh --verbose

# 3. Run tests to verify update
cd ..
poetry run pytest modules/*/tests/ -v
```

### 3. Creating a New Module

```bash
# 1. Create module structure
cd modules
mkdir rv-new-module
cd rv-new-module

# 2. Initialize Poetry project
poetry init --name rv-new-module --dependency rv-android-core
mkdir -p src/rv_new_module tests

# 3. Create basic structure
cat > src/rv_new_module/__init__.py << 'EOF'
"""RV New Module - Description of functionality."""
__version__ = "0.1.0"
EOF

# 4. Add to install script
# Edit modules/install.sh and add "rv-new-module" to MODULES array

# 5. Install and test
cd ..
./install.sh rv-new-module
poetry run pytest rv-new-module/tests/
```

## 💻 Development Workflows

### Environment Configuration

RV-Android supports environment-controlled data validation:

```bash
# Development mode - full validation enabled
export RV_PYDANTIC=true

# Production mode - validation disabled for performance
export RV_PYDANTIC=false
# or leave unset (default)
```

**When to use:**
- **Development**: Set `RV_PYDANTIC=true` for full type safety and error detection
- **Production**: Leave unset or `false` for optimal performance
- **Testing**: Automatically enabled during test execution

### Daily Development Commands

```bash
# Navigate to project root
cd /path/to/rv-android

# Set development environment
export RV_PYDANTIC=true

# Run all tests
poetry run pytest

# Test specific module
poetry run pytest modules/rv-monitor-generator/tests/ -v

# Install single module (after changes)
cd modules
./install.sh rv-android-core --verbose

# Run with coverage
poetry run pytest --cov=modules --cov-report=html
```

### Monitor Generation Workflow

```bash
# Generate JCA cryptography monitors
poetry run rv-monitor-generator generate \
  --specs-dir $RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca \
  --output ./output/jca-monitors

# Generate generic pattern monitors
poetry run rv-monitor-generator generate \
  --specs-dir $RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/generic \
  --output ./output/generic-monitors

# Auto-discover specifications (requires RVSEC_HOME)
poetry run rv-monitor-generator generate --output ./output/auto-monitors
```

### Static Analysis Workflow

```bash
# Analyze single APK
poetry run rv-static-analysis analyze \
  --apk /path/to/app.apk \
  --output /analysis/results

# Batch analysis
poetry run rv-static-analysis batch \
  --apks-dir /path/to/apks \
  --output /analysis/batch-results
```

### Experiment Execution

```bash
# Run complete experiment
poetry run python run_test_framework.py

# Execute main application
poetry run python main.py

# Run specific experiment configuration
poetry run python -m rv_experiment \
  --config ./tf_configs/basic_config.json
```

## 🔧 PyCharm Development Setup

### Project Configuration

1. **Open Project**: Open the `rv-android` directory (workspace root) in PyCharm
2. **Python Interpreter**: Configure Poetry environment
   - File → Settings → Project → Python Interpreter
   - Add → Poetry Environment → Existing environment
   - Select the Poetry virtual environment for rv-android

3. **Source Roots**: Mark module source directories
   - Right-click `modules/rv-android-core/src` → Mark Directory as → Sources Root
   - Repeat for all modules: `modules/*/src`

4. **Test Configuration**: 
   - Run/Debug Configurations → Templates → Python tests → pytest
   - Working directory: `$PROJECT_DIR$`
   - Additional arguments: `-v`

### Debugging Workflow

```bash
# Set up debugging in PyCharm
# 1. Create Python configuration
# 2. Script path: modules/rv-monitor-generator/src/rv_monitor_generator/__main__.py
# 3. Parameters: generate --specs-dir /path/to/specs --output /tmp/debug
# 4. Working directory: /path/to/rv-android
# 5. Environment variables: RVSEC_HOME=/path/to/rvsec
```

## 🧪 Testing Strategy

### Test Organization

```bash
# Fast unit tests (no external dependencies)
poetry run pytest -m "not slow" -v

# Integration tests (requires RVSEC)
poetry run pytest -m "slow" -v

# Module-specific tests
poetry run pytest modules/rv-android-core/tests/ -v
poetry run pytest modules/rv-monitor-generator/tests/test_runtime_verification_generator_complete.py -v

# Test with debugging
poetry run pytest --tb=long --capture=no -vvv
```

### Continuous Testing

```bash
# Watch mode for development
poetry run pytest-watch modules/rv-android-core/tests/

# Coverage report
poetry run pytest --cov=modules --cov-report=html
# View: open htmlcov/index.html
```

## 🏗️ Module Development Patterns

### Working on rv-android-core

```bash
cd modules/rv-android-core

# Run module tests
poetry run pytest tests/ -v

# Test domain models
poetry run pytest tests/domain/ -v

# Test error handling
poetry run pytest tests/util/error/ -v
```

### Working on rv-monitor-generator

```bash
# Test monitor generation
poetry run pytest modules/rv-monitor-generator/tests/ -k "test_generate" -v

# Test CLI interface
poetry run rv-monitor-generator --help

# Debug with real RVSEC
poetry run rv-monitor-generator generate \
  --specs-dir $RVSEC_HOME/examples/MOPSyntax \
  --output /tmp/debug-monitors \
  --verbose
```

### Working on rv-experiment

```bash
# Test experiment framework
poetry run pytest modules/rv-experiment/tests/ -v

# Run basic experiment
poetry run python -c "
from rv_experiment.experiment.experiment_controller import ExperimentController
controller = ExperimentController()
print('Experiment framework ready')
"
```

## 🛠️ Troubleshooting

### Common Issues

#### Module Import Errors
```bash
# Error: "No module named 'rv_android_core'"
# Solution: Ensure you're in workspace root
cd /path/to/rv-android  # NOT modules/rv-*/
poetry run pytest modules/rv-monitor-generator/tests/

# Verify Poetry environment
poetry env info
poetry show --tree
```

#### RVSEC Environment Issues
```bash
# Set RVSEC_HOME if auto-discovery fails
export RVSEC_HOME="/path/to/rvsec"

# Verify RVSEC installation
ls $RVSEC_HOME/javamop/bin/javamop
ls $RVSEC_HOME/rv-monitor/bin/rv-monitor

# Test RVSEC integration
poetry run rv-monitor-generator generate --dry-run
```

#### Poetry Installation Issues
```bash
# Clean and reinstall
cd modules
for module in */; do
  cd "$module"
  poetry env remove --all
  poetry install
  cd ..
done

# Verify installation
./install.sh --dry-run --verbose
```

#### Test Failures
```bash
# Debug test failures
poetry run pytest --tb=long --capture=no -vvv

# Skip slow tests during development
poetry run pytest -m "not slow"

# Run single test with full output
poetry run pytest modules/rv-android-core/tests/test_app.py::test_app_creation -vvv
```

### Environment Validation

```bash
# Quick environment check
cd modules
./install.sh --dry-run

# Comprehensive validation
poetry run python -c "
import sys
print(f'Python: {sys.version}')

try:
    import rv_android_core
    print('✅ rv-android-core')
except ImportError as e:
    print(f'❌ rv-android-core: {e}')

try:
    import rv_monitor_generator
    print('✅ rv-monitor-generator')
except ImportError as e:
    print(f'❌ rv-monitor-generator: {e}')

import os
rvsec_home = os.environ.get('RVSEC_HOME')
print(f'RVSEC_HOME: {rvsec_home or \"Not set\"}')
"
```

## 📚 Additional Resources

- **Configuration Examples**: `tf_configs/`, `plateau_config_example.json`
- **Architecture Documentation**: `docs/`
- **Module Documentation**: Each module's `README.md`
- **Test Data**: `modules/*/tests/resources/`

## 🤝 Contributing

1. **Development Environment**: Always use workspace mode for development
2. **Testing**: Run tests from workspace root, not individual modules
3. **New Modules**: Follow the module creation pattern above
4. **Documentation**: Update relevant READMEs when adding features
5. **Dependencies**: Add new dependencies to appropriate module only

---

**Development Note**: This workspace is optimized for integrated development with Poetry path dependencies. All development should be done from the workspace root to ensure proper module resolution and dependency management.