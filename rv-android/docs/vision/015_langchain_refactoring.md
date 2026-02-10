# 015 - LangChain/LangGraph Refactoring

**Date**: 2025-12-27
**Status**: COMPLETED
**Objective**: Refactor evaluator to use LangChain/LangGraph following RVAgent architecture

---

## Overview

The evaluation framework was refactored from a custom implementation to use LangChain/LangGraph, aligning with the RVAgent architecture for easier integration.

---

## Architecture

### Component Structure

```
src/
├── config/
│   └── evaluation_config.py     # Pydantic configuration
├── llm/
│   ├── client.py                # VisionLLMClient (LangChain wrapper)
│   ├── tools/
│   │   └── android_tools.py     # @tool definitions
│   └── graph/
│       ├── state.py             # TypedDict state
│       └── nodes.py             # LangGraph nodes
├── evaluator/
│   └── evaluator.py             # LLMEvaluator (LangGraph workflow)
├── parsers/
│   ├── uiautomator_parser.py    # UIElement extraction
│   └── tool_call_parser.py      # Multi-format tool call parsing
├── validation/
│   └── click_validator.py       # Hit validation
└── utils/
    └── coordinates.py           # Coordinate conversion
```

### LangGraph Workflow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   prepare   │────>│  inference  │────>│   extract   │────>│  validate   │
│  inference  │     │   (async)   │     │ coordinates │     │   result    │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

---

## Key Components

### 1. EvaluationConfig (Pydantic)

```python
class EvaluationConfig(BaseModel):
    model: str = "Qwen/Qwen3-VL-4B-Instruct"
    server_url: str = "http://localhost:30000"
    temperature: float = 0.01
    top_p: float = 0.6
    top_k: int = 50
    grounding_mode: GroundingMode = GroundingMode.VISUAL_ONLY
    max_screenshots: int = 150
    repetitions: int = 1
    hit_tolerance_px: int = 50

    @property
    def uses_normalized_coords(self) -> bool:
        """Check if model uses [0,1000) normalized coordinates."""
        return "qwen" in self.model.lower() or "minicpm" in self.model.lower()
```

### 2. VisionLLMClient (LangChain)

```python
class VisionLLMClient:
    def __init__(self, config: EvaluationConfig):
        self.llm = ChatOpenAI(
            base_url=f"{config.server_url}/v1",
            model=config.model,
            temperature=config.temperature,
        )
        self.tools = get_android_tools()
        self.llm_with_tools = self.llm.bind_tools(self.tools)

    async def invoke(self, messages: list) -> tuple[AIMessage, float]:
        response = await self.llm_with_tools.ainvoke(messages)
        return response, latency_ms

    def extract_tool_calls(self, response: AIMessage) -> list[dict]:
        # Native tool calls + fallback parser
        ...
```

### 3. EvaluatorState (TypedDict)

```python
class EvaluatorState(TypedDict):
    # Input
    screenshot_path: str
    element: dict
    grounding_mode: str
    target_x: int
    target_y: int

    # LLM Response
    messages: list
    response: Any
    tool_calls: list[dict]
    content: str

    # Extracted coordinates
    raw_x: int | None
    raw_y: int | None
    predicted_x: int | None
    predicted_y: int | None
    tool_name: str | None

    # Validation
    is_hit: bool
    distance_px: float

    # Injected dependencies
    _llm: Any
    _config: Any
```

### 4. LangGraph Nodes

```python
def prepare_inference(state: EvaluatorState) -> dict:
    """Create vision messages for LLM."""
    messages = llm.create_messages(screenshot_path, user_prompt, grounding_mode)
    return {"messages": messages, "image_width": w, "image_height": h}

async def run_inference(state: EvaluatorState) -> dict:
    """Run LLM inference with tools."""
    response, latency = await llm.invoke(messages)
    tool_calls = llm.extract_tool_calls(response)
    return {"response": response, "tool_calls": tool_calls, ...}

def extract_coordinates(state: EvaluatorState) -> dict:
    """Extract and denormalize coordinates."""
    # Handle multiple tool call formats
    # Apply coordinate denormalization for Qwen3-VL
    return {"predicted_x": x, "predicted_y": y, "tool_name": name}

def validate_result(state: EvaluatorState) -> dict:
    """Check if prediction is within tolerance."""
    distance = euclidean_distance(predicted, target)
    is_hit = distance <= tolerance
    return {"is_hit": is_hit, "distance_px": distance}
```

---

## Tool Call Parser Enhancements

### Supported Formats

1. **JSON Array**: `[{"name": "tool", "parameters": {...}}]`
2. **JSON Object**: `{"name": "tool", "parameters": {...}}`
3. **XML Tags**: `<tool_call>{"name": ...}</tool_call>`
4. **Markdown Code Blocks**: ` ```json {...} ``` `
5. **Pythonic Calls**: `android_click(x=540, y=1054)`
6. **Gemma Format**: `{"action": "android_click", "x": 480, "y": 1600}`

### Coordinate Normalization

```python
def normalize_tool_args(args: dict) -> dict:
    # Handle: {"x": [499, 510]} -> {"x": 499, "y": 510}
    # Handle: {"coordinate": [464, 487]} -> {"x": 464, "y": 487}
    # Handle: {"arguments": {"coordinate": [x, y]}} -> {"x": x, "y": y}
    ...

def denormalize_qwen_coords(x, y, width, height) -> tuple[int, int]:
    # Qwen3-VL [0, 1000) -> pixel coordinates
    pixel_x = int((x / 1000) * width)
    pixel_y = int((y / 1000) * height)
    return pixel_x, pixel_y
```

---

## Visual Element Filtering

Added `is_visually_identifiable` property to UIElement:

```python
@property
def is_visually_identifiable(self) -> bool:
    """Check if element can be identified visually in a screenshot."""
    # Always identifiable: Button, EditText, CheckBox, Switch, etc.
    # Require text/content-desc: TextView, ImageButton, ImageView
    # Never identifiable: LinearLayout, FrameLayout, etc.
```

This filters out container layouts and elements without visual identifiers from `visual_only` mode benchmarks.

---

## Integration with RVAgent

The refactored code follows the same patterns as RVAgent:

| RVAgent Component | Evaluator Equivalent |
|-------------------|---------------------|
| `AgentConfig` | `EvaluationConfig` |
| `LLMClient` | `VisionLLMClient` |
| `AgentState` | `EvaluatorState` |
| Graph nodes | `prepare_inference`, `run_inference`, etc. |
| `@tool` decorators | `android_tools.py` |

This alignment makes it easy to:
1. Port improvements back to RVAgent
2. Use the same tool definitions
3. Share parsing logic
4. Maintain consistent architecture

---

## Files Changed

| File | Change |
|------|--------|
| `src/config/evaluation_config.py` | NEW - Pydantic config |
| `src/llm/client.py` | NEW - LangChain wrapper |
| `src/llm/graph/state.py` | NEW - TypedDict state |
| `src/llm/graph/nodes.py` | NEW - LangGraph nodes |
| `src/llm/tools/android_tools.py` | NEW - @tool definitions |
| `src/evaluator/evaluator.py` | REWRITTEN - LangGraph workflow |
| `src/parsers/tool_call_parser.py` | ENHANCED - Multi-format support |
| `src/parsers/uiautomator_parser.py` | ENHANCED - Visual filtering |

---

## Testing

```bash
# Quick validation (2 screenshots)
poetry run python tests/test_evaluator.py --max-screenshots 2 --repetitions 1

# Full benchmark
poetry run python tests/test_evaluator.py --max-screenshots 150 --repetitions 1

# With specific model
poetry run python tests/test_evaluator.py --model microsoft/Fara-7B --url http://localhost:8000
```
