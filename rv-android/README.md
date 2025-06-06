# RV-Android: Runtime Verification for Android Applications

A modular framework for runtime verification of Android applications, supporting both JCA (Java Cryptographic Architecture) and generic monitored operations specifications through JavaMOP and RV-Monitor integration.

## 🏗️ Architecture Overview

### Modular Design
RV-Android follows a **Poetry workspace architecture** optimized for integrated development while maintaining logical separation:

```
rv-android/                           # 🏠 Main workspace
├── modules/                          # 📦 Independent modules
│   ├── rv-android-core/             # 🧠 Core utilities and commands
│   ├── rv-monitor-generator/        # 🔧 Monitor generation engine
│   └── rvandroid/                   # 🎯 Main application framework
├── pyproject.toml                   # 📋 Workspace configuration
└── README.md                        # 📖 This file
```

### Core Modules

#### 🧠 **rv-android-core**
- **Purpose**: Foundation utilities and command execution infrastructure
- **Key Components**: ErrorHandler, LoggingManager, Command execution, Android utilities
- **Dependencies**: None (base module)

#### 🔧 **rv-monitor-generator** 
- **Purpose**: JavaMOP and RV-Monitor integration for generating monitoring artifacts
- **Key Components**: RuntimeVerificationGenerator, RVGeneratorConfig, CLI interface
- **Dependencies**: rv-android-core
- **Supports**: JCA specifications, Generic operation monitoring

#### 🎯 **rvandroid**
- **Purpose**: Main application framework for Android testing and analysis
- **Key Components**: Experiment management, Tool integration, Analysis pipelines
- **Dependencies**: rv-android-core, rv-monitor-generator

## 🚀 Development Workflow

### Prerequisites
```bash
# Required tools
- Python >= 3.12
- Poetry >= 1.8.0
- Java 11+
- Android SDK
- JavaMOP and RV-Monitor tools (in RVSEC environment)

# Environment setup
export RVSEC_HOME="/path/to/rvsec"  # Optional: for auto-discovery
```

### Initial Setup
```bash
# Clone and install workspace
git clone <repository-url>
cd rv-android

# Install all modules and dependencies
poetry install

# Verify installation
poetry run python -c "import rv_android_core, rv_monitor_generator, rvandroid; print('✅ All modules loaded')"
```

### Development Commands

#### 🧪 **Testing**
```bash
# Run all tests across all modules
poetry run pytest

# Test specific module
poetry run pytest modules/rv-android-core/tests/
poetry run pytest modules/rv-monitor-generator/tests/
poetry run pytest modules/rvandroid/tests/

# Test with coverage
poetry run pytest --cov=modules --cov-report=html

# Test specific functionality
poetry run pytest -k "test_runtime_verification" -v

# Skip slow integration tests (for faster development)
poetry run pytest -m "not slow"

# Run only slow/integration tests
poetry run pytest -m "slow"
```

#### 🔧 **Monitor Generation**
```bash
# Using CLI (JCA specifications)
poetry run rv-monitor-generator generate \
  --specs-dir /rvsec/rvsec-mop/src/main/resources/jca \
  --output ./output/jca-monitors

# Using CLI (Generic specifications)  
poetry run rv-monitor-generator generate \
  --specs-dir /rvsec/rvsec-mop/src/main/resources/generic \
  --output ./output/generic-monitors

# Environment-based auto-discovery
poetry run rv-monitor-generator generate --output ./output/auto
```

#### 📊 **Analysis and Experiments**
```bash
# Run experiment framework
poetry run python run_test_framework.py

# Execute main RV-Android application
poetry run python main.py

# Run specific analysis
poetry run rvandroid --help
```

#### 🛠️ **Development Tools**
```bash
# Code formatting
poetry run black modules/

# Type checking  
poetry run mypy modules/

# Linting
poetry run flake8 modules/

# Dependency analysis
poetry show --tree

# Test markers and configuration
# Custom pytest markers are configured in each module's pyproject.toml:
# - slow: Integration tests that require external tools (RVSEC)
# - Use: pytest -m "not slow" for fast development cycles
```

### Module-Specific Development

#### Working on rv-android-core
```bash
# Navigate to module
cd modules/rv-android-core

# Run module tests
poetry run pytest tests/ -v

# Test in isolation (if needed)
poetry install --only-root
poetry run pytest tests/
```

#### Working on rv-monitor-generator
```bash
# Test monitor generation pipeline
poetry run pytest modules/rv-monitor-generator/tests/test_runtime_verification_generator_complete.py -v

# Test CLI functionality
poetry run rv-monitor-generator --help

# Test with real RVSEC environment
poetry run pytest modules/rv-monitor-generator/tests/ -k "Integration" -v
```

## 📦 Production Deployment Strategy

### Hybrid Approach: Development vs Production

#### Development Mode (Current)
- **Structure**: Integrated workspace with path dependencies
- **Benefits**: Full PyCharm integration, cross-module refactoring, unified debugging
- **Commands**: All development commands above

#### Production Mode (Future)
For independent module deployment, each module would have dual configuration:

**Development Configuration** (current):
```toml
# modules/rv-monitor-generator/pyproject.toml
[tool.poetry.dependencies]
rv-android-core = {path = "../rv-android-core", develop = true}
```

**Production Configuration** (future):
```toml
# modules/rv-monitor-generator/pyproject-prod.toml  
[tool.poetry.dependencies]
rv-android-core = "^0.1.0"  # Published PyPI package
```

**Build Pipeline** (future):
```bash
# Step 1: Build and publish core
cd modules/rv-android-core
poetry build
poetry publish

# Step 2: Update dependent modules
cd ../rv-monitor-generator
cp pyproject-prod.toml pyproject.toml
poetry update rv-android-core
poetry build
poetry publish

# Step 3: Build applications
cd ../rvandroid  
cp pyproject-prod.toml pyproject.toml
poetry update rv-android-core rv-monitor-generator
poetry build
```

## 🎯 Monitored Operations Support

### JCA Specifications
- **Purpose**: Monitor Java Cryptographic Architecture usage
- **Specifications**: MessageDigest, SecureRandom, Cipher operations
- **Location**: `/rvsec/rvsec-mop/src/main/resources/jca/`
- **Usage**: Cryptographic API compliance checking

### Generic Specifications  
- **Purpose**: Monitor general programming patterns
- **Specifications**: Iterator, Collection, Stream operations
- **Location**: `/rvsec/rvsec-mop/src/main/resources/generic/`
- **Usage**: General API contract enforcement

### Example: Experiment Separation
```bash
# Experiment 1: JCA Monitoring
poetry run rv-monitor-generator generate \
  --specs-dir /rvsec/rvsec-mop/src/main/resources/jca \
  --output ./experiments/crypto-monitoring

# Experiment 2: Generic Monitoring  
poetry run rv-monitor-generator generate \
  --specs-dir /rvsec/rvsec-mop/src/main/resources/generic \
  --output ./experiments/pattern-monitoring
```

## 🐛 Troubleshooting

### Common Issues

#### Import Errors
```bash
# If you see "No module named 'rv_android_core'"
# Make sure you're running from workspace root:
cd /path/to/rv-android  # Not modules/rv-monitor-generator!
poetry run pytest modules/rv-monitor-generator/tests/
```

#### RVSEC Environment Issues
```bash
# Set RVSEC_HOME if auto-discovery fails
export RVSEC_HOME="/path/to/rvsec"

# Verify RVSEC tools are accessible
ls $RVSEC_HOME/javamop/bin/javamop
ls $RVSEC_HOME/rv-monitor/bin/rv-monitor
```

#### Test Failures
```bash
# Run tests with more verbose output
poetry run pytest -vvv --tb=long

# Skip slow integration tests during development
poetry run pytest -m "not slow"

# Run tests with full debugging information
poetry run pytest --tb=long --capture=no -v
```

## 📚 Additional Resources

- **Architecture Documentation**: `docs/`
- **Configuration Examples**: `tf_configs/`, `plateau_config_example.json`
- **Tool Integration**: `rvandroid/tools/`
- **Analysis Framework**: `rvandroid/test_framework/`

## 🤝 Contributing

1. **Development**: Use workspace mode for all development
2. **Testing**: Always run tests from workspace root
3. **Modules**: Follow architectural patterns in existing modules
4. **Documentation**: Update relevant docs when adding features
5. **Dependencies**: Add new dependencies to appropriate module only

---

**Note**: This workspace is optimized for integrated development. For production deployments, consider the hybrid approach described above to maintain both development productivity and deployment flexibility.