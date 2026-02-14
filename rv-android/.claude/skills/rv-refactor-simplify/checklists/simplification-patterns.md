# Simplification Patterns

Catalog of common over-engineering patterns and their simpler replacements. Use to identify and fix unnecessary complexity.

## How to Use

1. During code review, check for each pattern below
2. For each match, verify it's not a false positive (see "When NOT to apply")
3. Apply the simplification, then verify tests still pass
4. Report: pattern name, location, before/after summary

---

## Pattern 1: Unnecessary Abstraction → Inline

**Symptom**: Class with one method, or interface with one implementor.

**Before**:
```python
class DataProcessor(ABC):
    @abstractmethod
    def process(self, data): ...

class JSONProcessor(DataProcessor):
    def process(self, data):
        return json.loads(data)

processor = JSONProcessor()
result = processor.process(raw_data)
```

**After**:
```python
result = json.loads(raw_data)
```

**When NOT to apply**: Multiple implementors exist, or the abstraction is a documented extension point.

## Pattern 2: Over-Parameterized → Hardcode

**Symptom**: Configuration option that is never changed from its default. Feature flag that is always on.

**Before**:
```python
def run_agent(mode="pure_algorithm", enable_logging=True, retry_count=3):
    if enable_logging:  # Always True in practice
        setup_logging()
```

**After**:
```python
def run_agent(mode="pure_algorithm", retry_count=3):
    setup_logging()  # Always needed
```

**When NOT to apply**: The parameter is documented as configurable and users may change it.

## Pattern 3: Premature Generalization → Specialize

**Symptom**: Generic framework built for one use case. Template method with one template.

**Before**:
```python
class BaseAnalyzer:
    def analyze(self, target):
        data = self.collect(target)
        result = self.process(data)
        return self.format(result)

    def collect(self, target): ...
    def process(self, data): ...
    def format(self, result): ...

class CoverageAnalyzer(BaseAnalyzer):  # Only subclass
    def collect(self, target): ...
    def process(self, data): ...
    def format(self, result): ...
```

**After**:
```python
class CoverageAnalyzer:
    def analyze(self, target):
        data = self._collect(target)
        result = self._process(data)
        return self._format(result)
```

**When NOT to apply**: Additional subclasses are planned for the current iteration (not "someday").

## Pattern 4: Deep Inheritance → Composition

**Symptom**: 3+ level inheritance hierarchy where subclasses override most parent methods.

**Before**: `Base → ToolBase → AndroidTool → MonkeyTool`

**After**: `MonkeyTool` with composed `AndroidToolHelper` for shared behavior.

**When NOT to apply**: The hierarchy is shallow (2 levels) and subclasses truly specialize.

## Pattern 5: Callback Hell → Direct Call

**Symptom**: Event bus, observer pattern, or callback chain with one subscriber.

**Before**:
```python
event_bus.subscribe("task_complete", handler)
# ... elsewhere ...
event_bus.publish("task_complete", result)
```

**After**:
```python
handler(result)  # Direct call, one subscriber
```

**P1 test**: Direct call > indirection with one subscriber.

**When NOT to apply**: Multiple subscribers exist, or decoupling is architecturally required.

## Pattern 6: Builder Overuse → Constructor

**Symptom**: Builder pattern for object with 2–3 fields.

**Before**:
```python
config = ConfigBuilder().set_timeout(60).set_mode("fast").set_retries(3).build()
```

**After**:
```python
config = Config(timeout=60, mode="fast", retries=3)
```

**When NOT to apply**: Object has 8+ fields with complex validation, or construction requires multiple steps.

## Pattern 7: Strategy Pattern Overuse → If/Else

**Symptom**: Strategy pattern with 2 strategies, selected once at startup.

**Before**:
```python
class Strategy(ABC): ...
class FastStrategy(Strategy): ...
class SafeStrategy(Strategy): ...
strategy = FastStrategy() if fast_mode else SafeStrategy()
```

**After**:
```python
if fast_mode:
    result = fast_process(data)
else:
    result = safe_process(data)
```

**When NOT to apply**: 4+ strategies, or strategies are selected dynamically at runtime.

## Pattern 8: Wrapper Over Nothing → Remove

**Symptom**: Adapter or wrapper that passes through without transformation.

**Before**:
```python
class DatabaseWrapper:
    def __init__(self, db):
        self.db = db
    def query(self, sql):
        return self.db.execute(sql)  # Just passes through
```

**After**: Use `db.execute(sql)` directly.

**When NOT to apply**: The wrapper adds logging, validation, or error handling.

## Pattern 9: Defensive Overvalidation → Trust Internal Code

**Symptom**: Validating parameters that were already validated upstream, or checking internal invariants that are guaranteed by construction.

**Before**:
```python
def _internal_process(self, config):
    if config is None:
        raise ValueError("config required")  # Already validated in public method
    if not isinstance(config, Config):
        raise TypeError("must be Config")  # Already type-checked
```

**After**:
```python
def _internal_process(self, config):
    # config guaranteed valid by process() public method
    result = config.compute()
```

**P1 rule**: Only validate at system boundaries (user input, external APIs). Trust internal code.

**When NOT to apply**: The function is public API, or called from multiple paths with different guarantees.

## Pattern 10: Unnecessary Indirection → Inline

**Symptom**: Method that just calls another method with the same arguments. Delegation with no added value.

**Before**:
```python
def get_results(self):
    return self._fetch_results()

def _fetch_results(self):
    return self.db.query("SELECT * FROM results")
```

**After**:
```python
def get_results(self):
    return self.db.query("SELECT * FROM results")
```

**When NOT to apply**: The indirection serves a purpose (testability, future extension documented in current sprint).

---

## P1 Simplicity Test

For any pattern match, ask: **"Do three similar lines of code serve better than this abstraction?"**

If the abstraction only has one use site, the answer is almost always yes. Inline it.
