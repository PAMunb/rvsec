# Module Analysis Reference

Consolidated reference for comprehensive module analysis. Contains the 4 modeling perspectives and analysis checklists.

---

## 4 Modeling Perspectives

| Perspective | What it Shows | Key Questions |
|-------------|---------------|---------------|
| **Context** | Module boundaries and environment | What is inside/outside? What triggers execution? |
| **Interaction** | Communication with actors and systems | Who initiates? What use cases? What message sequences? |
| **Structural** | Static organization and relationships | What classes? What patterns? What hierarchies? |
| **Behavioral** | Dynamic behavior during execution | Data-driven or event-driven? What states/flows? |

---

## Context Modeling Checklist

Analyze the module's context and boundaries:

1. **System Boundaries**: What functionality is inside this module? What is delegated to other modules?
2. **Adjacent Modules**: For each rv-android dependency:
   - What data flows between them?
   - What is the direction (depends-on, depended-by, bidirectional)?
3. **External Systems**: What external APIs, services, or hardware does it interact with?
   - Android device, LLM server, file system, network
4. **Process Triggers**: What initiates module execution?
   - CLI command, parent module call, event/callback, scheduler

---

## Interaction Modeling Checklist

Identify how the module interacts with actors and systems:

1. **Actors**: Who/what initiates interactions?
   - Human: CLI user, API consumer
   - System: parent module, scheduler, event bus
   - External: Android device, LLM server
2. **Use Cases**: For each discrete task the module supports, document:
   - Actor(s), stimulus, response, error handling
3. **Key Sequences** (for complex interactions only):
   - Trace message flow between components
   - Document alternative paths (error, timeout, retry)

---

## Structural Modeling Checklist

Analyze the static structure:

1. **Key Classes**: Main domain entities and services — name, responsibility, line count
2. **Associations**: Relationships between classes:
   - Dependency (uses), Association (has-a), Aggregation (contains), Composition (owns)
3. **Hierarchies**: Inheritance structures — ABC/Protocol → concrete implementations
4. **Design Patterns**: Recognize and document patterns used:
   - Factory, Strategy, Observer, Decorator, Facade, Registry, Builder, Template Method
5. **Coupling Assessment**: Are there classes that know too much about other classes' internals?

---

## Behavioral Modeling Checklist

Analyze dynamic behavior:

1. **Behavior Type**: Is the module primarily data-driven (pipeline/ETL) or event-driven (state machine)?
2. **For Data-Driven Modules**:
   - Input → Processing steps → Output
   - Data transformations at each stage
   - Error/retry handling in the pipeline
3. **For Event-Driven Modules**:
   - What states can the module be in?
   - What stimuli trigger state transitions?
   - What actions occur on entry/exit/during each state?
4. **Key Scenarios**: Document happy path and top 2-3 error scenarios
5. **Common Patterns**: Pipeline, Request-Response, State Machine, Workflow orchestration

---

## rv-android Module Directory

| Module | Layer | Package | Primary Role |
|--------|-------|---------|-------------|
| rv-android-core | 1 | rv_android_core | Foundation: domain models, error handling, logging |
| rv-tools | 2 | rv_tools | Tool plugin system: registry, factory |
| rv-uiautomator | 2 | rv_uiautomator | UIAutomator components for device interaction |
| rv-screen-parser | 2 | rv_screen_parser | Android UI parsing with visitor patterns |
| rv-static-analysis | 3 | rv_static_analysis | GATOR/GESDA/REACH for Android apps |
| rv-coverage | 3 | rv_coverage | Coverage analysis and tracking |
| rv-monitor-generator | 3 | rv_monitor_generator | JavaMOP/RV-Monitor integration |
| rv-instrumentation | 4 | rv_instrumentation | APK instrumentation with monitor weaving |
| rv-agent | 4 | rv_agent | LLM-driven testing with LangGraph |
| rv-platform | 4 | rv_platform | Central execution platform |
| rv-experiment | 5 | rv_experiment | Experiment orchestration |
| rvagent-tool | 5 | rvagent_tool | rv-agent as rv-platform tool |
| aperv-tool | 5 | aperv_tool | APE-RV as rv-platform tool |
