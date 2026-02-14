# Audience Guidance

Guidance on writing for the LLM audience vs human audience. CLAUDE.md is primarily consumed by LLMs, which have different needs than human readers.

## How to Use

1. Before writing any CLAUDE.md section, consider who will read it (LLM vs human)
2. Apply the LLM-first conventions below for CLAUDE.md content
3. Use the comparison table to catch human-oriented writing habits
4. Review the final document against the checklist at the bottom

---

## Audience Comparison

| Aspect | LLM Reader (CLAUDE.md) | Human Reader (README, architecture.md) |
|--------|----------------------|---------------------------------------|
| Primary need | Precise paths and commands to take action | Conceptual understanding to make decisions |
| Path format | Absolute from module root: `src/rv_agent/agent/rv_agent.py` | Relative or abbreviated: `agent/rv_agent.py` |
| Command format | Copy-pasteable with full context | Conceptual with flags explained |
| Descriptions | What the code DOES, not why it exists | Why it was built, design rationale |
| Structure | Flat, scannable tables and lists | Narrative paragraphs with flow |
| Examples | Concrete values, real file names | Illustrative, may use placeholders |
| Length | Dense and compact | Can be verbose for clarity |

## LLM-First Writing Conventions

### File Paths

**Do**: Use paths relative to module root, always include the file extension.
```
src/rv_agent/agent/rv_agent.py
src/rv_agent/llm/llm_client.py
tests/unit/test_rv_agent.py
```

**Don't**: Use ambiguous references.
```
the agent module
the main file
the config
```

### Commands

**Do**: Include full command with working directory context.
```bash
# From project root
poetry run pytest modules/rv-agent/tests/unit/ -v
```

**Don't**: Assume context.
```bash
pytest tests/ -v  # Which module? From which directory?
```

### Descriptions

**Do**: Be specific about what code does.
```
RVAgent (agent/rv_agent.py:45): LangGraph workflow with 7 nodes (parse, decision, algorithm, llm, validation, execute, learn). Entry point: run() method.
```

**Don't**: Be vague or promotional.
```
The main agent class that handles the testing workflow in a sophisticated manner.
```

### Naming

**Do**: Use exact names as they appear in code.
```
TaskExecutor, ToolFactory, ErrorHandler
```

**Don't**: Use paraphrased or informal names.
```
the task runner, the tool maker, the error wrapper
```

### Type Annotations and Signatures

**Do**: Include key function signatures when they clarify the API.
```
def run(self, package: str, timeout: int = 300) -> ExecutionResult
```

**Don't**: Include every function signature (that's what the code is for).

## Common Mistakes

| Mistake | Example | Fix |
|---------|---------|-----|
| Ambiguous reference | "the config file" | "`modules/rv-agent/config.yaml`" |
| Missing default | "Set TIMEOUT env var" | "`TIMEOUT` (default: 300 seconds)" |
| Relative path | "./src/agent.py" | "`src/rv_agent/agent/rv_agent.py`" |
| Narrative where table works | "The module has three entry points..." | Table with columns: Entry Point, File, Usage |
| Outdated information | "Uses EventBus for events" | Verify against current code before writing |

## Document-Level Guidelines

### Length

Target: 200–500 lines per module CLAUDE.md. This is part of the LLM's context window — every line costs tokens. Dense and precise > verbose and explanatory.

### Section Order

Follow the standard order from `claude-md-sections.md`. LLMs benefit from consistent structure across modules — they learn where to find information.

### Updates

CLAUDE.md must reflect current code state (P4). When updating:
- Re-verify all file paths exist
- Re-test all commands
- Remove references to deleted code
- Add references to new code

## Final Review Checklist

Before submitting a CLAUDE.md:

- [ ] Every file path resolves to an existing file
- [ ] Every command runs successfully when copy-pasted
- [ ] No ambiguous references ("the module", "the config")
- [ ] No promotional language ("modern", "elegant", "sophisticated")
- [ ] No migration history ("was migrated from", "replaces old")
- [ ] All sections from the standard template are present
- [ ] Length is within 200–500 lines
