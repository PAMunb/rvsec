# Settings Distribution Across RV-Android Modules

This document describes how the centralized `settings.py` configurations have been distributed across the specialized modules in the RV-Android platform, maintaining module independence while providing proper configuration management.

## Architectural Overview

The migration from a centralized `settings.py` to distributed, module-specific configurations follows these principles:

- **Module Independence**: Each module manages its own configuration requirements
- **Type Safety**: Modern configuration uses dataclasses with type hints and validation
- **Environment Integration**: Supports environment variables and flexible deployment scenarios
- **Validation**: Comprehensive validation at initialization time
- **Backward Compatibility**: Bridge patterns enable gradual migration

## Distribution Map

### rv-android-core (`modules/rv-android-core/src/rv_android_core/constants.py`)

**Purpose**: Core constants, environment variables, and shared definitions

**From settings.py**:
- All environment variable names (`ENV_*` constants)
- File extension constants
- Shared column names and metrics definitions
- Core experiment constants

**New Architecture**:
- Centralized constant definitions for cross-module consistency
- Environment variable naming conventions
- Shared data structure field names

---

### rv-monitor-generator (`modules/rv-monitor-generator/src/rv_monitor_generator/config.py`)

**Purpose**: Monitor generation tool configuration (JavaMOP, RV-Monitor)

**From settings.py**:
- `JAVAMOP_HOME`, `JAVAMOP_BIN` → `RVGeneratorConfig.javamop_bin`
- `RV_MONITOR_HOME`, `RV_MONITOR_BIN` → `RVGeneratorConfig.rvmonitor_bin`
- `MOP_BASE_DIR`, `MOP_JCA_DIR`, `MOP_GENERIC_DIR`, `MOP_DIR` → `RVGeneratorConfig.mop_specs_dir`
- `ASPECTS_DIR` → `RVGeneratorConfig.aspects_dir`
- `MOP_OUT_DIR` → Monitor output directory configuration
- `MOP_INCLUDE_DIR` → AspectJ include directory handling

**New Architecture**:
- `RVGeneratorConfig` class with priority-based path resolution
- Intelligent discovery from RVSEC_HOME environment variable
- Comprehensive validation of tool availability
- Support for multiple monitor specification types (JCA, Generic, Custom)

---

### rv-instrumentation (`modules/rv-instrumentation/src/rv_instrumentation/config.py`)

**Purpose**: APK instrumentation and Android SDK integration

**From settings.py**:
- `INSTRUMENTED_DIR` → `RVInstrumentationConfig.instrumented_dir`
- `TMP_DIR`, `LIB_TMP_DIR`, `RVM_TMP_DIR` → Temporary directory configuration
- `ANDROID_SDK_HOME`, `ANDROID_PLATFORMS_DIR` → `RVInstrumentationConfig.android_platforms_dir`
- `ANDROID_PLATFORM`, `ANDROID_JAR_PATH` → `RVInstrumentationConfig.android_jar_path`
- `KEYSTORE_FILE`, `KEYSTORE_PASSWORD` → Keystore configuration
- `D2J_HOME`, `D2J_DEX2JAR`, `D2J_ASM_VERIFY`, `D2J_APK_SIGN` → dex2jar tools configuration

**New Architecture**:
- `RVInstrumentationConfig` class with Android SDK integration
- Automatic Android platform discovery and validation
- Keystore management with security considerations
- dex2jar tool suite configuration and validation
- Monitor artifacts integration with rv-monitor-generator

---

### rv-static-analysis (`modules/rv-static-analysis/src/rv_static_analysis/config.py`)

**Purpose**: Static analysis tools configuration (GATOR, GESDA, REACH)

**From settings.py**:
- `RT_JAR` → `RVStaticAnalysisConfig.rt_jar`
- `LIB_DIR` + tool-specific paths → Static analysis tool JAR paths
- Android platform integration for analysis context

**New Architecture**:
- `RVStaticAnalysisConfig` class with multi-tool support
- Priority-based Android runtime JAR discovery
- Tool availability validation and command generation
- Integration with monitor specifications for REACH analysis

---

### rv-experiment (`modules/rv-experiment/src/rv_experiment/config.py`)

**Purpose**: Experiment orchestration and execution configuration

**From settings.py**:
- `RESULTS_DIR` → `ExperimentConfiguration.output_dir`
- `APKS_DIR` → `ApplicationConfiguration.directory`
- Experiment execution parameters (repetitions, timeouts, etc.)

**New Architecture**:
- `ExperimentConfiguration` class replacing legacy Configuration singleton
- Type-safe configuration with comprehensive validation
- Support for multiple experiment types (single-tool, comparative, batch)
- Integration with all specialized modules through configuration coordination

---

### Legacy Integration (`rv_experiment/bridge.py`)

**Purpose**: Bridge between legacy main.py and modern module architecture

**From settings.py**:
- Configuration translation between legacy and modern formats
- Backward compatibility for existing CLI interfaces
- Progressive migration support

**New Architecture**:
- `ExperimentBridge` class for seamless integration
- Configuration format translation
- Graceful fallback to legacy systems when needed

## Migration Benefits

### 1. **Module Independence**
- Each module can be developed, tested, and deployed independently
- Clear separation of concerns and responsibilities
- Reduced coupling between system components

### 2. **Type Safety and Validation**
- Dataclass-based configuration with type hints
- Comprehensive validation at initialization time
- Clear error messages for configuration issues

### 3. **Deployment Flexibility**
- Support for multiple deployment scenarios
- Environment-based configuration override
- Intelligent path discovery and fallback mechanisms

### 4. **Maintainability**
- Configuration logic co-located with module functionality
- Specialized validation for each module's requirements
- Clear documentation and examples for each configuration

### 5. **Extensibility**
- Easy addition of new configuration parameters
- Support for multiple configuration sources
- Plugin-like architecture for tool extensions

## Usage Examples

### Monitor Generation
```python
from rv_monitor_generator.config import RVGeneratorConfig

# Automatic discovery from environment
config = RVGeneratorConfig()

# Explicit configuration
config = RVGeneratorConfig(
    rvsec_root="/path/to/rvsec",
    mop_specs_dir="/path/to/jca/specs"
)
```

### Instrumentation
```python
from rv_instrumentation.config import RVInstrumentationConfig

# Android SDK integration
config = RVInstrumentationConfig(
    android_jar_path="/path/to/android.jar",
    keystore_file="/path/to/keystore.jks"
)
```

### Static Analysis
```python
from rv_static_analysis.config import RVStaticAnalysisConfig

# Multi-tool configuration
config = RVStaticAnalysisConfig(
    rt_jar="/path/to/android.jar",
    lib_dir="/path/to/tools"
)

# Generate command for GESDA analysis
cmd = config.get_tool_command("gesda", "app.apk", "output.gesda")
```

### Experiment Orchestration
```python
from rv_experiment.config import ExperimentConfiguration

# Modern experiment configuration
config = ExperimentConfiguration(
    name="comparative_study",
    tools=["monkey", "droidbot", "rvandroid"],
    execution=ExecutionConfiguration(
        repetitions=3,
        timeouts=[300, 600, 900]
    )
)
```

## Migration Status

✅ **Completed**:
- Core constants distributed to rv-android-core
- Monitor generation configuration in rv-monitor-generator
- Instrumentation configuration in rv-instrumentation  
- Static analysis configuration in rv-static-analysis
- Experiment configuration in rv-experiment
- Bridge pattern for legacy compatibility

✅ **Benefits Achieved**:
- Module independence maintained
- Type-safe configuration across all modules
- Comprehensive validation and error handling
- Flexible deployment support
- Backward compatibility preserved

## Future Enhancements

1. **Configuration Templates**: Pre-defined configuration templates for common scenarios
2. **Configuration Validation CLI**: Command-line tools for configuration validation
3. **Environment Detection**: Automatic environment detection and optimization
4. **Configuration Migration Tools**: Automated migration from legacy formats
5. **Configuration Documentation**: Auto-generated configuration documentation

---

This distribution maintains the flexibility and power of the original settings.py while providing modern, type-safe, and modular configuration management that respects module independence and enables scalable system architecture.