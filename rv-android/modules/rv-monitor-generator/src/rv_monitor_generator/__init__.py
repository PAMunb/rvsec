"""
RV-Monitor Generator Module

A sophisticated runtime verification monitor generation system for Android application instrumentation,
supporting both JCA (Java Cryptographic Architecture) and generic monitored operations specifications.

### Architectural Decisions:
- Implements a modular configuration system with intelligent path resolution and environment discovery
- Integrates seamlessly with existing rv-android-core error handling and logging infrastructure  
- Supports flexible specification sets for different experimental scenarios and research contexts
- Provides both programmatic API and CLI interfaces for diverse integration requirements
- Maintains clear separation between JCA cryptographic and generic operation monitoring capabilities

### Role in the System:
- Acts as the central orchestration component for transforming MOP specifications into executable monitoring artifacts
- Coordinates JavaMOP and RV-Monitor tools execution with comprehensive error handling and recovery strategies
- Generates AspectJ weaving files and Java monitor classes required for runtime verification instrumentation
- Supports independent operation for standalone monitor generation or integration within larger experimental frameworks
- Facilitates experimental reproducibility through consistent monitor generation across different research scenarios

### Key Considerations:
- Handles dual specification ecosystems: JCA cryptographic API monitoring and generic operation pattern detection
- Supports dynamic environment-based configuration discovery through RVSEC_HOME and explicit path resolution
- Provides comprehensive validation of tool availability, functionality, and specification accessibility
- Maintains experimental independence allowing separate specification sets for different research objectives
- Ensures robust error propagation and detailed logging for debugging complex monitor generation scenarios

### Monitored Operations Support:

**JCA Specifications (Cryptographic API Monitoring):**
- MessageDigest algorithm validation and usage pattern detection
- SecureRandom entropy source verification and randomization tracking  
- Cipher operation sequence monitoring and algorithm compliance checking
- Key generation and management operation validation

**Generic Specifications (General Operation Pattern Monitoring):**
- Iterator usage pattern validation (hasNext() before next() enforcement)
- Collection modification during iteration detection
- Stream operation lifecycle monitoring and resource management
- Generic API contract enforcement and violation detection

### Configuration Flexibility:
- **Environment Discovery**: Automatic RVSEC_HOME detection for seamless integration
- **Explicit Configuration**: Direct path specification for controlled experimental setups
- **Specification Directory Support**: Custom paths for both JCA and generic specification collections
- **Tool Path Validation**: Comprehensive verification of JavaMOP and RV-Monitor availability
- **Experiment Independence**: Each specification set operates independently for research isolation

### Integration Examples:

```python
# JCA Cryptographic Monitoring Setup
from rv_monitor_generator import RuntimeVerificationGenerator, RVGeneratorConfig

# Environment-based configuration for JCA specifications
jca_generator = RuntimeVerificationGenerator()
jca_success = jca_generator.generate_monitors('/output/jca-monitors')

# Explicit JCA configuration
jca_config = RVGeneratorConfig(
    rvsec_root='/path/to/rvsec',
    mop_specs_dir='/path/to/rvsec/rvsec-mop/src/main/resources/jca'
)
jca_generator = RuntimeVerificationGenerator(jca_config)
jca_result = jca_generator.generate_monitors('/output/jca-monitors')

# Generic Operations Monitoring Setup  
generic_config = RVGeneratorConfig(
    rvsec_root='/path/to/rvsec',
    mop_specs_dir='/path/to/rvsec/rvsec-mop/src/main/resources/generic'
)
generic_generator = RuntimeVerificationGenerator(generic_config)
generic_result = generic_generator.generate_monitors('/output/generic-monitors')
```

```bash
# CLI usage for different specification types
# JCA cryptographic specifications
rv-monitor-generator generate --specs-dir /rvsec/rvsec-mop/src/main/resources/jca --output /output/jca

# Generic operation specifications  
rv-monitor-generator generate --specs-dir /rvsec/rvsec-mop/src/main/resources/generic --output /output/generic

# Environment-based automatic detection
rv-monitor-generator generate --output /output/auto-detected
```
"""

__version__ = "0.1.0"
__author__ = "RV-Android Team"

# Public API exports
from .runtime_verification_generator import RuntimeVerificationGenerator
from .config import RVGeneratorConfig, ConfigurationError

__all__ = [
    'RuntimeVerificationGenerator',
    'RVGeneratorConfig', 
    'ConfigurationError'
]