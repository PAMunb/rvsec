# RV-Android Modularization Plan - Gradual Migration Strategy

**Version**: 1.0  
**Date**: December 2024  
**Status**: Implementation Ready  

## 1. Executive Summary

This document presents the modularization strategy for the RV-Android system, transforming it from a monolithic architecture into independent modules using Poetry for packaging and dependency management. The plan emphasizes **gradual migration** starting with core modules while preserving existing functionality throughout the process.

### Key Strategic Decisions
- **Gradual Migration**: Start with core modules, migrate incrementally
- **Poetry Workspace**: Centralized dependency management with path dependencies
- **Functional Modules**: Group by functionality rather than fine-grained separation
- **File-Based Dependencies**: Inter-module communication via files (current approach)
- **Plugin System**: Dynamic tool loading for testing tools
- **Maven Integration**: Automatic JAR copying from RVSec build process

## 2. Module Architecture Overview

### 2.1 Workspace Structure

```
rv-android-workspace/
├── pyproject.toml                 # Workspace root with shared dependencies
├── modules/
│   ├── rv-android-core/          # Core utilities, domain models
│   ├── rv-monitor-generator/     # JavaMOP → RV-Monitor integration  
│   ├── rv-instrumentation/       # APK instrumentation
│   ├── rv-static-analysis/       # GATOR, GESDA, REACH + parsers
│   ├── rv-screen-parser/         # Screen parsing (DroidBot/UIAutomator)
│   ├── rv-log-parser/           # Logcat parsing and analysis
│   ├── rv-llm/                  # LLM adapters and prompt framework
│   ├── rv-testing-tools/        # Standard tools + plugin system
│   ├── rvandroid-tool/          # RVAndroid (DroidBot + LLM)
│   ├── rvdroid-tool/            # RVDroid (UIAutomator + LLM)
│   ├── rvandroid/               # Current project (Phase 1)
│   └── rv-experiment/           # Experiment orchestration
└── lib/                         # Shared JARs from RVSec build
```

### 2.2 Dependency Management Strategy

**Workspace Root** (`pyproject.toml`):
- Defines **specific versions** for all common dependencies
- Manages path dependencies to all modules
- Provides development tools and testing framework

**Module Dependencies**:
- Use `"*"` for dependencies managed by workspace root
- Specify versions only for module-specific dependencies
- Inherit common tools (pytest, black, mypy) from workspace

### 2.3 Module Structure Standard

Each module follows Poetry's standard structure:

```
module-name/
├── pyproject.toml
├── README.md
├── src/
│   └── module_package/
│       ├── __init__.py
│       ├── __main__.py          # CLI entry point (if applicable)
│       └── (module code)
├── lib/                         # Module-specific JARs (if needed)
├── tests/
└── docs/
```

## 3. Phase-Based Migration Plan

### Phase 1: Foundation Setup (Current Focus)

**Initial Workspace with 3 Modules:**

1. **rv-android-core** - Extract core utilities from current project
2. **rv-monitor-generator** - Extract monitor generation logic (`rvsec.py`)
3. **rvandroid** - Current project as Poetry module (minimal changes)

**Phase 1 Goals:**
- Establish Poetry workspace
- Move core utilities to rv-android-core
- Move monitor generation to rv-monitor-generator
- Maintain full functionality with existing experiment system
- Test complete workflow after each move

### Phase 2: Analysis and Instrumentation

**Add Modules:**
4. **rv-static-analysis** - Extract static analysis (`static_analysis.py` + parsers)
5. **rv-instrumentation** - Extract APK instrumentation (`rvandroid.py`)

### Phase 3: Parsing and Services  

**Add Modules:**
6. **rv-screen-parser** - Extract screen parsing logic
7. **rv-log-parser** - Extract logcat parsing
8. **rv-llm** - Extract LLM infrastructure (not services)

### Phase 4: Testing Tools

**Add Modules:**
9. **rv-testing-tools** - Standard tools integration + plugin system
10. **rvandroid-tool** - RVAndroid tool (DroidBot + LLM)
11. **rvdroid-tool** - RVDroid tool (UIAutomator + LLM)

### Phase 5: Orchestration

**Add Module:**
12. **rv-experiment** - Experiment coordination and management

## 4. Module Specifications

### 4.1 rv-android-core

**Purpose**: Core utilities, domain models, and shared components

**Contents to migrate from current project:**
- `app.py` - App class and related utilities
- `domain/` - Domain models (static analysis, coverage, etc.)
- `util/` - Utility functions and helpers
- `commands/` - Command execution framework
- `constants.py` - System constants

**Dependencies**: None (foundation module)

### 4.2 rv-monitor-generator

**Purpose**: JavaMOP and RV-Monitor integration for generating runtime verification monitors

**Contents to migrate:**
- `rvsec.py` → `generator.py` (main logic)
- Monitor generation workflow
- JavaMOP execution logic
- RV-Monitor execution logic

**Dependencies**: `rv-android-core`

**CLI**: `python -m rv_monitor_generator --specs specs/ --output monitors/`

**JAR Dependencies**: 
- `javamop.jar`
- `rv-monitor.jar`
- Custom AspectJ files

### 4.3 rv-instrumentation

**Purpose**: APK instrumentation with runtime verification monitors

**Contents to migrate:**
- `rvandroid.py` → `instrumenter.py` (main logic)
- APK decompilation/recompilation logic
- Monitor weaving logic
- APK signing and verification

**Dependencies**: `rv-android-core`, `rv-monitor-generator`

**CLI**: `python -m rv_instrumentation --apk app.apk --monitors monitors/ --output instrumented.apk`

**JAR Dependencies**:
- `dex2jar.jar`
- Various build tools

### 4.4 rv-static-analysis

**Purpose**: Static analysis tools integration and result parsing

**Contents to migrate:**
- `static_analysis.py` → `analysis.py` (main logic)
- GATOR, GESDA, REACH integration
- Result parsers for each tool
- Analysis coordination logic

**Dependencies**: `rv-android-core`

**CLI Options:**
```bash
# Run all tools
python -m rv_static_analysis --apk app.apk --output results/

# Specific tools
python -m rv_static_analysis --apk app.apk --tools gator,gesda --output results/

# Single tool
python -m rv_static_analysis --apk app.apk --tool reach --output results/
```

**JAR Dependencies**:
- `gator.jar`
- `gesda.jar` 
- `reach.jar`

### 4.5 rv-screen-parser

**Purpose**: Android screen parsing for DroidBot and UIAutomator

**Contents to migrate:**
- Screen parsing logic
- Visitor pattern implementation
- ScreenDescription generation
- Parser factory

**Dependencies**: `rv-android-core`, `rv-static-analysis`

**No CLI initially** (programmatic use only)

### 4.6 rv-log-parser

**Purpose**: Android logcat parsing and analysis

**Contents to migrate:**
- Logcat parsing logic
- Coverage analysis
- Error detection
- Log filtering and processing

**Dependencies**: `rv-android-core`

**No CLI** (programmatic use only)

### 4.7 rv-llm

**Purpose**: LLM integration infrastructure and prompt framework

**Contents to migrate:**
- LLM adapters (Ollama, HuggingFace, Frontier)
- Prompt framework and templates
- Response parsing utilities
- LLM configuration management

**Note**: LLM *services* (action_service.py, etc.) remain in tool-specific modules

**Dependencies**: `rv-android-core`

### 4.8 rv-testing-tools

**Purpose**: Standard testing tools integration with plugin system

**Plugin System for Tools:**
- monkey, droidbot, ape, fastbot, etc. (external tools)
- rvandroid-tool, rvdroid-tool (internal tools)

**Plugin Discovery:**
- Entry points in `pyproject.toml`
- Automatic tool registration
- Runtime tool loading

**Dependencies**: `rv-android-core`, `rv-screen-parser`

### 4.9 rvandroid-tool

**Purpose**: DroidBot + LLM integration tool

**Contents to migrate:**
- RVAndroid-specific LLM services
- DroidBot policy integration
- REST API server
- RVAndroid templates

**Dependencies**: `rv-android-core`, `rv-screen-parser`, `rv-llm`

**Registration**: Plugin in rv-testing-tools

### 4.10 rvdroid-tool

**Purpose**: UIAutomator + LLM integration tool

**Contents to migrate:**
- RVDroid core system
- Advanced memory management
- Strategy framework
- Analysis components

**Dependencies**: `rv-android-core`, `rv-screen-parser`, `rv-static-analysis`, `rv-llm`

**Registration**: Plugin in rv-testing-tools

### 4.11 rv-experiment

**Purpose**: Experiment orchestration and coordination

**Contents to migrate:**
- Experiment controller
- Task execution management
- Result processing
- Workflow coordination

**Dependencies**: All other modules

## 5. Configuration Examples

### 5.1 Workspace Root Configuration

```toml
# rv-android-workspace/pyproject.toml
[tool.poetry]
name = "rv-android-workspace"
version = "0.1.0"
description = "RV-Android Modular Platform Workspace"
authors = ["RV-Android Team"]

[tool.poetry.dependencies]
python = "^3.8"
# Common dependencies with specific versions
requests = "^2.28.0"
pyyaml = "^6.0"
click = "^8.0"
jinja2 = "^3.1.0"
numpy = "^1.24.0"

# Path dependencies for all modules
rv-android-core = {path = "modules/rv-android-core", develop = true}
rv-monitor-generator = {path = "modules/rv-monitor-generator", develop = true}
rvandroid = {path = "modules/rvandroid", develop = true}

[tool.poetry.group.dev.dependencies]
pytest = "^7.0"
pytest-cov = "^4.0"
black = "^23.0"
mypy = "^1.0"
flake8 = "^6.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

### 5.2 Module Configuration Example

```toml
# modules/rv-monitor-generator/pyproject.toml
[tool.poetry]
name = "rv-monitor-generator"
version = "0.1.0"
description = "JavaMOP and RV-Monitor integration for runtime verification"
authors = ["RV-Android Team"]

[tool.poetry.dependencies]
python = "^3.8"
# Inherit from workspace
requests = "*"
pyyaml = "*"
click = "*"
# Local dependency
rv-android-core = {path = "../rv-android-core", develop = true}

[tool.poetry.scripts]
rv-monitor-generator = "rv_monitor_generator.__main__:main"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

## 6. Maven Integration

### 6.1 JAR Distribution Strategy

**Current Build Process:**
1. `mvn clean install` in RVSec repository
2. JARs automatically copied to appropriate module lib/ folders
3. Modules use relative paths to their lib/ directories

**Maven Configuration Updates:**
```xml
<!-- In RVSec pom.xml -->
<plugin>
    <artifactId>maven-resources-plugin</artifactId>
    <executions>
        <execution>
            <id>copy-gator-jar</id>
            <phase>package</phase>
            <goals><goal>copy-resources</goal></goals>
            <configuration>
                <outputDirectory>rv-android/modules/rv-static-analysis/lib</outputDirectory>
                <resources>
                    <resource>
                        <directory>gator/target</directory>
                        <includes><include>gator.jar</include></includes>
                    </resource>
                </resources>
            </configuration>
        </execution>
        <!-- Similar executions for other JARs -->
    </executions>
</plugin>
```

## 7. Implementation Timeline

### Week 1: Foundation Setup

**Day 1-2: Workspace Creation**
- Create Poetry workspace structure
- Setup initial pyproject.toml files
- Create rv-android-core and rv-monitor-generator modules

**Day 3-4: Core Migration**
- Move core utilities to rv-android-core
- Update imports in current project
- Test functionality

**Day 5: Monitor Migration**
- Move rvsec.py logic to rv-monitor-generator
- Test monitor generation workflow
- Run complete experiment to validate

### Week 2: Analysis and Instrumentation

**Day 1-3: Static Analysis Module**
- Create rv-static-analysis module
- Move static_analysis.py and parsers
- Test static analysis workflow

**Day 4-5: Instrumentation Module**
- Create rv-instrumentation module
- Move rvandroid.py logic
- Test instrumentation workflow

### Subsequent Weeks

Continue with remaining phases based on testing and validation of each module.

## 8. Testing Strategy

### 8.1 Module Testing

Each module includes:
- Unit tests for core functionality
- Integration tests with dependencies
- CLI testing (where applicable)

### 8.2 System Testing

After each migration phase:
- Complete experiment execution
- All tools functionality verification
- Result validation against baseline

### 8.3 Regression Testing

- Maintain test APK set for validation
- Compare results before/after migration
- Performance benchmarking

## 9. Migration Guidelines

### 9.1 Code Movement Process

1. **Create target module structure**
2. **Move files with git mv** (preserve history)
3. **Update import statements** in moved files
4. **Update import statements** in dependent files
5. **Update module __init__.py** files
6. **Test functionality** after each move
7. **Run complete experiment** validation

### 9.2 Import Statement Updates

**Before Migration:**
```python
from rvandroid.app import App
from rvandroid.domain.static import StaticAnalysisData
```

**After Migration:**
```python
from rv_android_core.app import App
from rv_android_core.domain.static import StaticAnalysisData
```

### 9.3 Configuration Migration

Settings and constants:
- Move shared constants to rv-android-core
- Module-specific settings in respective modules
- Environment variable handling in each module

## 10. Risk Mitigation

### 10.1 Gradual Migration Benefits

- **Reduced Risk**: Each phase is small and testable
- **Continuous Functionality**: System works throughout migration
- **Easy Rollback**: Can revert individual phases if needed
- **Learning Curve**: Team learns Poetry/module structure gradually

### 10.2 Contingency Plans

- **Module Integration Issues**: Keep old imports as fallback
- **Dependency Conflicts**: Use workspace-level version pinning
- **Build Integration**: Maintain Maven build compatibility
- **Testing Failures**: Thorough validation at each phase

## 11. Success Criteria

### 11.1 Phase 1 Success Metrics

- [ ] Poetry workspace successfully created
- [ ] rv-android-core module functional with moved code
- [ ] rv-monitor-generator module functional with monitor generation
- [ ] Complete experiment runs successfully
- [ ] All tests pass
- [ ] No functionality regression

### 11.2 Overall Project Success

- [ ] All modules independently functional
- [ ] Plugin system working for testing tools
- [ ] Complete workflow preserved
- [ ] Performance maintained
- [ ] Code maintainability improved
- [ ] Team can develop modules independently

---

**Document Status**: Ready for Implementation - Phase 1  
**Next Steps**: Create workspace structure and begin core module migration