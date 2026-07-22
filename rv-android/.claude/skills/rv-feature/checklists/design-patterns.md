# Design Patterns Reference

A catalog of common design patterns with guidance on when and how to apply them.

---

## What is a Design Pattern?

A design pattern is a reusable solution to a commonly occurring problem in software design. Each pattern has four essential elements:

| Element | Description |
|---------|-------------|
| **Name** | Identifier for the pattern |
| **Problem** | When to apply the pattern |
| **Solution** | How to structure the design |
| **Consequences** | Trade-offs and results |

---

## Pattern Selection Guide

Use this decision tree to identify applicable patterns:

```
START: What problem are you solving?
│
├─► Need to notify multiple objects of state changes?
│   └─► Observer Pattern
│
├─► Need to simplify a complex subsystem?
│   └─► Façade Pattern
│
├─► Need to traverse a collection without exposing internals?
│   └─► Iterator Pattern
│
├─► Need to add responsibilities dynamically?
│   └─► Decorator Pattern
│
├─► Need to create objects without specifying concrete class?
│   └─► Factory Pattern
│
├─► Need to ensure only one instance exists?
│   └─► Singleton Pattern
│
├─► Need to define a family of algorithms?
│   └─► Strategy Pattern
│
├─► Need to represent hierarchies of objects uniformly?
│   └─► Composite Pattern
│
└─► Need to adapt one interface to another?
    └─► Adapter Pattern
```

---

## Creational Patterns

### Factory Pattern

```markdown
## Factory Pattern

### Name
Factory Method / Abstract Factory

### Problem
- Need to create objects without specifying the exact class
- Object creation logic should be centralized
- Different configurations require different object types

### Solution
```
┌─────────────────┐
│ Creator         │
├─────────────────┤
│ +create()       │◄──────── Abstract creator
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌───▼───┐
│Creator│ │Creator│
│   A   │ │   B   │     Concrete creators
└───┬───┘ └───┬───┘
    │         │
    ▼         ▼
┌───────┐ ┌───────┐
│Product│ │Product│     Concrete products
│   A   │ │   B   │
└───────┘ └───────┘
```

**Python Example**:
```python
class ToolFactory:
    @staticmethod
    def create(tool_type: str, config: Config) -> Tool:
        if tool_type == "monkey":
            return MonkeyTool(config)
        elif tool_type == "droidbot":
            return DroidbotTool(config)
        else:
            raise ValueError(f"Unknown tool: {tool_type}")
```

### Consequences
| Pros | Cons |
|------|------|
| Loose coupling between creator and products | Can lead to many subclasses |
| Single Responsibility (creation in one place) | Requires parallel class hierarchies |
| Open/Closed (new products without changing client) | |
```

### Singleton Pattern

```markdown
## Singleton Pattern

### Name
Singleton

### Problem
- Need exactly one instance of a class
- Global point of access required
- Lazy initialization preferred

### Solution
```
┌─────────────────────────┐
│ Singleton               │
├─────────────────────────┤
│ - _instance: Singleton  │
├─────────────────────────┤
│ + get_instance(): Self  │
│ - __init__()            │
└─────────────────────────┘
```

**Python Example**:
```python
class EventBus:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._handlers = {}
        self._initialized = True
```

### Consequences
| Pros | Cons |
|------|------|
| Controlled access to sole instance | Global state (testing difficulties) |
| Reduced namespace pollution | Violates Single Responsibility |
| Lazy initialization | Hidden dependencies |
```

---

## Structural Patterns

### Façade Pattern

```markdown
## Façade Pattern

### Name
Façade

### Problem
- Complex subsystem with many classes
- Clients need simplified interface
- Want to reduce coupling between subsystem and clients

### Solution
```
Client
   │
   ▼
┌──────────────────────────────────────┐
│            Façade                    │
│  ┌─────────────────────────────────┐ │
│  │ + simple_operation()            │ │
│  │ + another_operation()           │ │
│  └─────────────────────────────────┘ │
└──────────────────┬───────────────────┘
                   │ delegates to
        ┌──────────┼──────────┐
        ▼          ▼          ▼
   ┌────────┐ ┌────────┐ ┌────────┐
   │ ClassA │ │ ClassB │ │ ClassC │
   │        │ │        │ │        │
   └────────┘ └────────┘ └────────┘
         Complex Subsystem
```

**Python Example**:
```python
class PlatformFacade:
    """Simplified interface to the rv-platform subsystem."""

    def __init__(self):
        self._task_generator = TaskGenerator()
        self._executor = TaskExecutor()
        self._result_processor = ResultProcessor()

    def run_experiment(self, config: Config) -> Results:
        """Single method hides complex subsystem."""
        tasks = self._task_generator.generate(config)
        raw_results = self._executor.execute_all(tasks)
        return self._result_processor.process(raw_results)
```

### Consequences
| Pros | Cons |
|------|------|
| Simplified interface for clients | Can become a god object |
| Decouples subsystem from clients | Additional layer of indirection |
| Can be entry point for subsystem | |
```

### Decorator Pattern

```markdown
## Decorator Pattern

### Name
Decorator / Wrapper

### Problem
- Need to add responsibilities to objects dynamically
- Subclassing would lead to explosion of classes
- Want to add/remove features at runtime

### Solution
```
┌──────────────────────┐
│ <<interface>>        │
│ Component            │
├──────────────────────┤
│ + operation()        │
└──────────┬───────────┘
           │
     ┌─────┴─────┐
     │           │
┌────▼────┐ ┌────▼────────────┐
│Concrete │ │ Decorator       │
│Component│ ├─────────────────┤
└─────────┘ │ - wrapped       │
            ├─────────────────┤
            │ + operation()   │
            └────────┬────────┘
                     │
          ┌──────────┼──────────┐
          │          │          │
     ┌────▼────┐┌────▼────┐┌────▼────┐
     │Decorator││Decorator││Decorator│
     │    A    ││    B    ││    C    │
     └─────────┘└─────────┘└─────────┘
```

**Python Example**:
```python
class LoggingDecorator(Tool):
    """Adds logging to any Tool."""

    def __init__(self, wrapped: Tool):
        self._wrapped = wrapped

    def execute(self, task: Task) -> Result:
        logger.info(f"Starting: {task.name}")
        result = self._wrapped.execute(task)
        logger.info(f"Completed: {task.name}")
        return result

# Usage: tool = LoggingDecorator(MonkeyTool(config))
```

### Consequences
| Pros | Cons |
|------|------|
| More flexible than inheritance | Many small objects |
| Add/remove features at runtime | Decorator and component not identical |
| Single Responsibility (features in decorators) | Configuration can be complex |
```

### Adapter Pattern

```markdown
## Adapter Pattern

### Name
Adapter / Wrapper

### Problem
- Need to use a class with an incompatible interface
- Want to reuse existing class without modification
- Need to work with multiple unrelated classes

### Solution
```
Client ───► ┌──────────────────┐
            │ <<interface>>    │
            │ Target           │
            ├──────────────────┤
            │ + request()      │
            └────────┬─────────┘
                     │
                     │ implements
                     │
            ┌────────▼─────────┐      ┌─────────────────┐
            │ Adapter          │─────►│ Adaptee         │
            ├──────────────────┤      ├─────────────────┤
            │ - adaptee        │      │ + specific_     │
            ├──────────────────┤      │   request()     │
            │ + request()      │      └─────────────────┘
            │   calls adaptee. │
            │   specific_      │
            │   request()      │
            └──────────────────┘
```

**Python Example**:
```python
class LegacyAnalyzer:
    def analyze_file(self, path: str) -> dict:
        # Old interface returns dict
        return {"result": "..."}

class AnalyzerAdapter(Analyzer):
    """Adapts LegacyAnalyzer to new Analyzer interface."""

    def __init__(self, legacy: LegacyAnalyzer):
        self._legacy = legacy

    def analyze(self, target: Path) -> AnalysisResult:
        # Convert between interfaces
        raw = self._legacy.analyze_file(str(target))
        return AnalysisResult.from_dict(raw)
```

### Consequences
| Pros | Cons |
|------|------|
| Reuse existing code | Additional complexity |
| Single Responsibility | Can be confusing with many adapters |
| Open/Closed | |
```

---

## Behavioral Patterns

### Observer Pattern

```markdown
## Observer Pattern

### Name
Observer / Publish-Subscribe / Event Listener

### Problem
- One object's state change should notify many others
- Don't want tight coupling between notifier and notified
- Number of observers can vary at runtime

### Solution
```
┌──────────────────────┐       ┌──────────────────────┐
│ Subject              │       │ <<interface>>        │
├──────────────────────┤       │ Observer             │
│ - observers: List    │       ├──────────────────────┤
├──────────────────────┤       │ + update(state)      │
│ + attach(observer)   │──────►└──────────┬───────────┘
│ + detach(observer)   │                  │
│ + notify()           │         ┌────────┼────────┐
└──────────────────────┘         │        │        │
                            ┌────▼───┐┌───▼────┐┌──▼─────┐
                            │Observer││Observer││Observer│
                            │   A    ││   B    ││   C    │
                            └────────┘└────────┘└────────┘
```

**Python Example**:
```python
class EventBus:
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, handler: Callable):
        self._handlers.setdefault(event_type, []).append(handler)

    def publish(self, event_type: str, data: Any):
        for handler in self._handlers.get(event_type, []):
            handler(data)

# Usage
bus = EventBus()
bus.subscribe("task.completed", lambda e: logger.info(e))
bus.publish("task.completed", {"task_id": "123"})
```

### Consequences
| Pros | Cons |
|------|------|
| Loose coupling (subject knows only Observer interface) | Unexpected updates |
| Open/Closed (new observers without changing subject) | No guarantee of order |
| Supports broadcast | Memory leaks if not detached |
```

### Strategy Pattern

```markdown
## Strategy Pattern

### Name
Strategy / Policy

### Problem
- Multiple algorithms for the same task
- Algorithm should be selected at runtime
- Want to avoid conditional logic for algorithm selection

### Solution
```
┌─────────────────────┐
│ Context             │      ┌──────────────────────┐
├─────────────────────┤      │ <<interface>>        │
│ - strategy          │─────►│ Strategy             │
├─────────────────────┤      ├──────────────────────┤
│ + execute()         │      │ + algorithm()        │
│   uses strategy.    │      └──────────┬───────────┘
│   algorithm()       │                 │
└─────────────────────┘       ┌─────────┼─────────┐
                              │         │         │
                         ┌────▼───┐┌────▼───┐┌────▼───┐
                         │Strategy││Strategy││Strategy│
                         │   A    ││   B    ││   C    │
                         └────────┘└────────┘└────────┘
```

**Python Example**:
```python
class ExplorationStrategy(Protocol):
    def select_action(self, state: AppState) -> Action: ...

class RandomStrategy:
    def select_action(self, state: AppState) -> Action:
        return random.choice(state.available_actions)

class DFSStrategy:
    def select_action(self, state: AppState) -> Action:
        return self._get_unvisited_or_backtrack(state)

class Agent:
    def __init__(self, strategy: ExplorationStrategy):
        self._strategy = strategy

    def step(self, state: AppState):
        action = self._strategy.select_action(state)
        return self.execute(action)
```

### Consequences
| Pros | Cons |
|------|------|
| Family of algorithms interchangeable | Clients must be aware of strategies |
| Eliminates conditional statements | Increased number of objects |
| Easy to add new strategies | Strategy and Context communicate overhead |
```

### Iterator Pattern

```markdown
## Iterator Pattern

### Name
Iterator / Cursor

### Problem
- Need to traverse a collection without exposing its structure
- Want multiple simultaneous traversals
- Want uniform interface for different collections

### Solution
```
┌──────────────────────┐      ┌──────────────────────┐
│ <<interface>>        │      │ <<interface>>        │
│ Iterable             │─────►│ Iterator             │
├──────────────────────┤      ├──────────────────────┤
│ + __iter__()         │      │ + __next__()         │
└──────────────────────┘      │ + __iter__()         │
                              └──────────────────────┘
```

**Python Example**:
```python
class TaskIterator:
    """Iterates through tasks in execution order."""

    def __init__(self, tasks: List[Task]):
        self._tasks = sorted(tasks, key=lambda t: t.priority)
        self._index = 0

    def __iter__(self):
        return self

    def __next__(self) -> Task:
        if self._index >= len(self._tasks):
            raise StopIteration
        task = self._tasks[self._index]
        self._index += 1
        return task

# Usage
for task in TaskIterator(tasks):
    executor.run(task)
```

### Consequences
| Pros | Cons |
|------|------|
| Single Responsibility (iteration vs storage) | Overkill for simple collections |
| Multiple iterators simultaneously | Additional classes |
| Uniform interface | |
```

---

## Composite Pattern

```markdown
## Composite Pattern

### Name
Composite / Object Tree

### Problem
- Represent part-whole hierarchies
- Treat individual objects and compositions uniformly
- Tree-like structure of objects

### Solution
```
┌──────────────────────┐
│ <<interface>>        │
│ Component            │◄──────────────────────┐
├──────────────────────┤                       │
│ + operation()        │                       │
└──────────┬───────────┘                       │
           │                                   │
     ┌─────┴─────┐                             │
     │           │                             │
┌────▼────┐ ┌────▼────────────┐                │
│ Leaf    │ │ Composite       │                │
├─────────┤ ├─────────────────┤                │
│+operation││ - children      │───────────────►│
└─────────┘ ├─────────────────┤
            │ + operation()   │  (for each child:
            │ + add(child)    │   child.operation())
            │ + remove(child) │
            └─────────────────┘
```

**Python Example**:
```python
class TestSuite:
    """Composite that can contain tests or other suites."""

    def __init__(self, name: str):
        self.name = name
        self._children: List[Union[Test, TestSuite]] = []

    def add(self, child: Union[Test, TestSuite]):
        self._children.append(child)

    def run(self) -> TestResult:
        results = []
        for child in self._children:
            results.append(child.run())
        return TestResult.merge(results)
```

### Consequences
| Pros | Cons |
|------|------|
| Uniform treatment of composites and leaves | Can make design overly general |
| Easy to add new component types | Hard to restrict composite contents |
| Simplifies client code | |
```

---

## Pattern Application Checklist

Before applying a pattern:

- [ ] **Problem Match**: Does the pattern solve my actual problem?
- [ ] **Simplicity**: Is the pattern simpler than alternatives?
- [ ] **Future Needs**: Does anticipated change justify the pattern?
- [ ] **Team Familiarity**: Will the team understand this pattern?
- [ ] **Documentation**: Have I documented why this pattern was chosen?

After applying a pattern:

- [ ] **Testability**: Is the code still easy to test?
- [ ] **Readability**: Is the code clear to others?
- [ ] **Performance**: Does the pattern introduce unacceptable overhead?
- [ ] **Maintainability**: Will future developers understand this?

---

## Anti-Patterns to Avoid

| Anti-Pattern | Description | Better Alternative |
|--------------|-------------|-------------------|
| **Patternitis** | Using patterns unnecessarily | Simple solution first |
| **Golden Hammer** | Using one pattern for everything | Match pattern to problem |
| **Copy-Paste Pattern** | Implementing without understanding | Study pattern first |
| **Speculative Generality** | Patterns for hypothetical future | YAGNI - add when needed |

---

## Pattern Selection Matrix

| Situation | Recommended Pattern |
|-----------|---------------------|
| Multiple algorithms, runtime selection | Strategy |
| Notify observers of state changes | Observer |
| Simplify complex subsystem | Façade |
| Add features without inheritance | Decorator |
| Create objects without concrete class | Factory |
| Part-whole hierarchies | Composite |
| Traverse collection uniformly | Iterator |
| Incompatible interfaces | Adapter |
| Single instance needed | Singleton (use sparingly) |
