# State of the Art: LLM-Driven Android GUI Testing

**Date**: 2026-03-19
**Change**: gh43 — APE-RV LLM Coordinate Mapping Validation
**Type**: SOTA (State of the Art) analysis
**Author**: Claude (research analysis)

---

## 1. Executive Summary

This state-of-the-art survey covers 21 tools, models, and research systems (2023–2026) that use Large Language Models (LLMs) — including multimodal Vision-Language Models (VLMs) — for automated Android GUI testing and exploration. The survey was conducted through web research of academic papers and deep source code analysis of 10 open-source repositories, with the goal of understanding the current landscape and positioning APE-RV's LLM integration relative to established approaches.

The central finding relevant to APE-RV's gh43 investigation is that **no mature tool uses raw coordinate prediction as its primary action mechanism**. The two dominant patterns are: (a) **Set-of-Marks (SoM)**, where numbered labels are overlaid on interactive elements and the LLM selects an element by number (AppAgent, DroidAgent, AUITestAgent); and (b) **Action-list selection**, where the LLM chooses from a numbered list of possible actions described in text (DroidBot-GPT, GPTDroid, LLMDroid, LLM-Explorer). Both approaches eliminate the coordinate-to-widget mapping problem entirely — the 37.3% no_match rate that APE-RV experiences is a structural consequence of asking the LLM to predict raw coordinates and then mapping them to discrete widgets.

The most impactful architectural patterns for APE-RV are:
1. **Selective LLM invocation** (LLMDroid, VLM-Fuzz): call the LLM only when traditional exploration gets stuck, not for every action — reduces cost by 148x.
2. **Structured output templates** (AppAgent, DroidAgent): Observation/Thought/Action/Summary format with function-call actions.
3. **Two-phase knowledge building** (AppAgent, DroidAgent): exploration phase builds reusable documentation, deployment phase uses it.
4. **Code-level reasoning** (CovAgent): LLM analyzes decompiled Smali code to reason about unreachable activities.

---

## 2. Methodology

The survey combined three research methods:

1. **Web search**: 12 targeted searches across Google, arXiv, ACM DL, ResearchGate, and GitHub covering terms like "LLM Android testing", "multimodal VLM mobile GUI", "vision language model Android exploration", and specific tool names.

2. **Source code analysis**: 10 repositories were cloned to `/tmp/` and analyzed for prompt templates, LLM integration patterns, action spaces, and exploration strategies:
   - AppAgent (`/tmp/AppAgent`) — Tencent QQ GY Lab
   - DroidAgent (`/tmp/DroidAgent`) — COINSE Lab, KAIST
   - AutoDroid (`/tmp/AutoDroid`) — MobileLLM
   - DroidBot-GPT (`/tmp/DroidBot-GPT`) — MobileLLM
   - MobileAgent (`/tmp/MobileAgent`) — Alibaba X-PLUG
   - VisionDroid (`/tmp/VisionDroid`) — Anonymous
   - LLMDroid (`/tmp/LLMDroid`) — LLMDroid-2024
   - AUITestAgent (`/tmp/AUITestAgent`) — Meituan bz-lab
   - DigiRL (`/tmp/DigiRL`) — DigiRL-agent
   - GPTDroid — access denied (403), analyzed from paper

3. **Sequential thinking analysis**: structured reasoning about taxonomy, coordinate mapping approaches, prompt patterns, and implications for APE-RV.

---

## 3. Tool Catalog

### 3.1 Text-Only LLM with UI Hierarchy

| Tool | Year | Venue | Model | Open Source | Repository |
|------|------|-------|-------|-------------|------------|
| **GPTDroid** | 2023 | arXiv | GPT-3/3.5 | Partial | [testinging6/GPTDroid](https://github.com/testinging6/GPTDroid) |
| **DroidBot-GPT** | 2023 | arXiv | GPT-3.5 | Yes | [MobileLLM/DroidBot-GPT](https://github.com/MobileLLM/DroidBot-GPT) |
| **LLMDroid** | 2025 | FSE | GPT-4o | Yes | [LLMDroid-2024/LLMDroid](https://github.com/LLMDroid-2024/LLMDroid) |
| **LLM-Explorer** | 2025 | MobiCom | Various | Yes | [MobileLLM/LLM-Explorer](https://github.com/MobileLLM/LLM-Explorer) |

### 3.2 Multimodal LLM with Set-of-Marks (SoM)

| Tool | Year | Venue | Model | Open Source | Repository |
|------|------|-------|-------|-------------|------------|
| **AppAgent** | 2024 | arXiv | GPT-4V / Qwen-VL | Yes | [TencentQQGYLab/AppAgent](https://github.com/TencentQQGYLab/AppAgent) |
| **DroidAgent** | 2024 | ICSE | GPT-4 | Yes | [coinse/droidagent](https://github.com/coinse/droidagent) |
| **AUITestAgent** | 2024 | arXiv | Multimodal | Yes | [bz-lab/AUITestAgent](https://github.com/bz-lab/AUITestAgent) |

### 3.3 Multimodal LLM with Coordinate Prediction

| Tool | Year | Venue | Model | Open Source | Repository |
|------|------|-------|-------|-------------|------------|
| **VisionDroid** | 2024 | arXiv | GPT-4V | Partial | [testtestA6/VisionDroid](https://github.com/testtestA6/VisionDroid) |
| **CogAgent** | 2024 | CVPR | CogAgent-18B/9B | Yes | [THUDM/CogAgent](https://github.com/THUDM/CogAgent) |
| **SeeClick** | 2024 | ACL | Qwen-VL | Yes | [njucckevin/SeeClick](https://github.com/njucckevin/SeeClick) |
| **ShowUI** | 2025 | CVPR | ShowUI-2B | Yes | [showlab/ShowUI](https://github.com/showlab/ShowUI) |

### 3.4 RL-Trained Vision-Language Models

| Tool | Year | Venue | Model | Open Source | Repository |
|------|------|-------|-------|-------------|------------|
| **DigiRL** | 2024 | NeurIPS | 1.5B VLM + RL | Yes | [DigiRL-agent/digirl](https://github.com/DigiRL-agent/digirl) |
| **UINav** | 2024 | arXiv | Lightweight | No | — |

### 3.5 Hybrid and Agentic Approaches

| Tool | Year | Venue | Model | Open Source | Repository |
|------|------|-------|-------|-------------|------------|
| **AutoDroid** | 2024 | MobiCom | GPT-4 | Yes | [MobileLLM/AutoDroid](https://github.com/MobileLLM/AutoDroid) |
| **MobileAgent v1/v2/v3** | 2024 | NeurIPS | GPT-4V | Yes | [X-PLUG/MobileAgent](https://github.com/X-PLUG/MobileAgent) |
| **VLM-Fuzz** | 2025 | EMSE | VLM | No | — |
| **CovAgent** | 2026 | arXiv | Agentic AI | Yes | arXiv:2601.21253 |
| **LELANTE** | 2025 | EASE | LLM | No | — |
| **QTypist** | 2023 | ICSE | GPT-3 | Partial | — |
| **AdbGPT** | 2024 | ICSE | GPT-3.5 | Yes | [sidongfeng/AdbGPT](https://github.com/sidongfeng/AdbGPT) |
| **MobileFlow** | 2024 | NeurIPS WS | 21B (Qwen-VL-Chat) | No | — |

---

## 4. Taxonomy of Approaches

The 18 tools fall into five distinct architectural categories, each representing a fundamentally different philosophy about how LLMs should participate in the testing loop.

### 4.1 Text-Only LLM as Action Selector

The earliest and simplest approach treats the LLM as a text-based decision maker. The UI hierarchy (typically Android's accessibility tree or UIAutomator XML dump) is converted to a text representation, and the LLM selects the next action from a numbered list.

**GPTDroid** (Zheng et al., 2023) pioneered this approach by framing Android testing as a "conversation" between the LLM and the app. Each turn, the LLM receives a text description of the current GUI page and returns an action choice. The insight is that LLMs already have "commonsense knowledge" about how apps should be used — for example, that a login page typically requires username and password inputs followed by tapping a login button.

**DroidBot-GPT** (Wen et al., 2023) follows the same philosophy but builds on the established DroidBot framework. The implementation is remarkably simple — the entire LLM integration consists of two modified files (`input_policy.py` and `device_state.py`). The prompt is constructed by concatenating three elements:

```
Task: "I'm using a smartphone to {task}."
State: "The current state has the following UI elements: [numbered list]"
History: "I have already completed the following steps: [action list]"
Question: "Which action should I choose next? Just return the action id."
```

The LLM (GPT-3.5) returns a single integer corresponding to the chosen action. For text input fields, a follow-up prompt asks "What should I enter?". This approach achieves 100% match rate by construction — the LLM can only select from available actions.

**LLMDroid** (2025, FSE) introduced the most sophisticated text-only approach. Rather than calling the LLM for every action, LLMDroid uses a two-stage architecture:

1. **Autonomous Exploration**: A traditional testing tool (DroidBot, Humanoid, or Fastbot2) explores the app while the LLM periodically summarizes explored pages and identifies their functions.
2. **LLM Guidance**: When code coverage growth slows (plateau detection), the LLM is consulted to provide strategic guidance — recommending which page to visit and which function to test.

The LLMDroid prompts (analyzed from `/tmp/LLMDroid/LLMDroid-Droidbot/droidbot/policy/prompt.py`) reveal a sophisticated multi-phase prompt system:

- **Overview phase**: The LLM receives an HTML-like representation of a page (using `<button>`, `<checkbox>`, `<scroller>`, `<input>`, `<p>` tags with attributes like `id`, `class`, `resource-id`, `content-desc`, `text`) and produces: (1) a page summary, (2) a function list ranked by importance (prioritizing navigation functions), and (3) a page importance ranking relative to other explored pages.
- **Guidance phase**: Given the ranked list of pages and their unexplored functions, the LLM selects the next target state and function to test, following strategies like "prioritize navigation-related functions" and "choose functions that can trigger transitions to undiscovered pages."
- **Test execution phase**: The LLM selects specific element IDs and action types (click=0, long_press=1, swipe_down=2, etc.) from the HTML representation.

This design achieves 26.16% higher code coverage and 29.31% higher activity coverage over baselines, at a cost of $4.77/hr with GPT-4o (or $0.18/hr for the cost-effective variant that achieves 78% of optimal performance).

**LLM-Explorer** (Zhao et al., 2025, MobiCom) pushes the cost-efficiency argument further: it uses the LLM **only for maintaining knowledge** (app understanding, page summaries), not for generating individual actions. Standard heuristic exploration generates the actual actions, guided by the LLM-maintained knowledge. This achieves the fastest and highest coverage among all automated explorers while being **148x cheaper** than the state-of-the-art LLM-based approach.

### 4.2 Multimodal LLM with Set-of-Marks

This category represents the dominant approach in 2024: overlaying numbered visual markers on interactive UI elements in the screenshot, then asking the multimodal LLM to select an element by its number.

**AppAgent** (Yang et al., 2024, Tencent) is the most influential tool in this category. Its architecture, analyzed from the source code at `/tmp/AppAgent/`, consists of two distinct phases:

**Exploration phase** (`self_explorer.py`): The agent explores the app autonomously, building a documentation database of UI element functions. For each interaction, the LLM receives before/after screenshots and generates a concise description of the element's functionality. The `self_explore_reflect_template` prompt asks the LLM to evaluate each action's effectiveness with one of four decisions:
- `BACK`: The action navigated to an irrelevant page
- `INEFFECTIVE`: The action changed nothing
- `CONTINUE`: The action changed something but didn't advance the task
- `SUCCESS`: The action successfully moved the task forward

Each decision also generates documentation about the UI element's function, building a reusable knowledge base.

**Deployment phase** (`task_executor.py`): Given a user task, the agent uses the accumulated documentation to efficiently complete it. The main prompt (`task_template`) defines five functions:

```python
# From /tmp/AppAgent/scripts/prompts.py
1. tap(element: int)        # Tap a numbered UI element
2. text(text_input: str)    # Insert text in input field
3. long_press(element: int) # Long press a numbered element
4. swipe(element: int, direction: str, dist: str)  # Swipe with direction and distance
5. grid()                   # Fallback: overlay grid for precise interaction
```

The output format is structured as: `Observation → Thought → Action → Summary`. The `grid()` function is a clever fallback mechanism — when the target element is not labeled with a number, the agent can request a grid overlay that divides the screen into small areas, each labeled with an integer. This gives the LLM "more freedom to choose any part of the screen" for interaction.

The LLM integration (`model.py`) supports both OpenAI (GPT-4V) and Qwen-VL through a unified `BaseModel` interface. Screenshots are sent as base64-encoded images in the `image_url` content type of the chat API.

**DroidAgent** (Yoon et al., 2024, ICSE, KAIST) takes a fundamentally different approach within the SoM paradigm. Rather than task completion, it focuses on **intent-driven testing** — generating realistic test scenarios from a persona profile. The architecture (analyzed from `/tmp/DroidAgent/`) is modular, with separate LLM instances for planning, acting, critiquing, and reflecting:

- **Planner** (`prompts/plan.py`): Generates realistic test tasks based on a persona profile (e.g., "Alice, 28, software engineer who uses the app for..."). Tasks must satisfy four properties: realism, importance, diversity, and difficulty. The planner considers visited/unvisited pages and prior task history.
- **Actor** (`prompts/act.py`): Selects GUI actions using function calling. The prompt includes the full screen hierarchy as JSON with `num_prev_actions` and `widget_role_inference` properties for each widget, enabling the LLM to reason about exploration progress.
- **Critic** (`prompts/critique_during_task.py`): Evaluates whether actions are effective and on-track.
- **Reflector** (`prompts/reflect_task.py`): After each task, generates reusable knowledge about app behavior.

DroidAgent uses OpenAI function calling (not text parsing) for action selection, with retry logic that sends error messages back through the function call mechanism. The UI state is represented as a hierarchical JSON structure (not raw XML), with semantic annotations from the memory system. DroidAgent achieves 61% activity coverage compared to 51% for prior state-of-the-art.

**AUITestAgent** (2024, Meituan) is unique in being requirements-driven: it takes natural language test requirements as input and automatically generates test interactions and verifications. It uses dynamically organized agents (not a fixed pipeline) and a multi-dimensional data extraction strategy to verify test outcomes.

### 4.3 Coordinate Prediction

This category is most directly relevant to APE-RV because it shares the fundamental challenge of mapping predicted coordinates to UI elements.

**VisionDroid** (2024) uses a multimodal LLM for both exploration and bug detection. Analysis of the source code at `/tmp/VisionDroid/VisionDroid Code/prompt.py` reveals a simpler approach than expected: the LLM receives a text list of clickable widgets (extracted from the accessibility tree) and selects one by name, not by coordinates. The "vision" aspect comes from the bug detection phase, where the LLM analyzes screenshot sequences to identify non-crash functional bugs by checking whether GUI transitions align with expected logic.

The exploration prompt is straightforward:
```python
# From /tmp/VisionDroid/VisionDroid Code/prompt.py
"We want to test the {app_name} App, which has {N} main function pages..."
"Do not select the same choice as before. Now we can do these:
 1. click "widget_name"
 2. click "widget_name"
 ..."
"Give a number of a choice above only"
```

This means VisionDroid, despite its name, uses **text-based action selection** for exploration (similar to Category 4.1) and reserves multimodal capabilities for the bug detection phase. The action matching problem is avoided entirely.

**CogAgent** (Hong et al., 2024, CVPR Highlight) is a purpose-built 18B parameter VLM for GUI understanding. Unlike general-purpose VLMs, CogAgent uses dual encoders (low-resolution + high-resolution at 1120×1120) specifically designed to recognize small GUI elements and text. It can output coordinates and bounding boxes for GUI elements, achieving state-of-the-art performance on both text-rich VQA benchmarks and GUI navigation tasks. The December 2024 update (CogAgent-9B) further improved GUI perception and action space completeness.

**SeeClick** (Cheng et al., 2024, ACL) is a Qwen-VL-based model fine-tuned specifically for GUI grounding — mapping natural language instructions to screen locations. It outputs normalized coordinates in [0,1]² format via `click(x, y)` actions. SeeClick created **ScreenSpot**, the first realistic GUI grounding benchmark across mobile, desktop, and web environments. This is the model closest to APE-RV's Qwen3-VL approach, but with dedicated grounding fine-tuning that APE-RV lacks.

**ShowUI** (2025, CVPR) introduces iterative coordinate refinement: the model predicts coordinates, then progressively narrows the region of focus through multiple passes. This addresses the precision problem inherent in single-pass coordinate prediction.

### 4.4 RL-Trained VLMs

**DigiRL** (Zhou et al., 2024, NeurIPS) represents a completely different paradigm: instead of prompt engineering a general-purpose VLM, it **fine-tunes** a 1.5B VLM using reinforcement learning. The training process has two stages:

1. **Offline RL**: Initialize the model on the Android-in-the-Wild (AitW) dataset of human demonstrations.
2. **Online RL**: Continue training with autonomous interaction in a scalable Android emulator environment, using advantage-weighted RL with enhanced advantage estimators.

The results are dramatic: DigiRL achieves 67.2% success rate, a 49.5% absolute improvement over supervised fine-tuning (17.7%). This vastly outperforms AppAgent with GPT-4V (8.3%) and CogAgent (14.4%) on the AitW benchmark. The key insight is that **RL-trained small models can dramatically outperform larger prompted models** when sufficient training infrastructure exists.

**UINav** (Google, 2024) takes a demonstration-based approach: given ~10 task demonstrations, it trains a lightweight agent that can run directly on mobile devices. It includes a "referee model" trained to predict task completion, enabling autonomous execution without constant LLM queries.

### 4.5 Hybrid and Agentic Approaches

**AutoDroid** (Wen et al., 2024, MobiCom) combines LLM commonsense knowledge with app-specific knowledge through automated dynamic analysis. Source code analysis (`/tmp/AutoDroid/`) reveals that AutoDroid is built on DroidBot's UTG (UI Transition Graph) infrastructure and uses **GPT-3.5-turbo** (text-only, not multimodal). The UI is represented as HTML-like tags (`<button id=3 class='More options'>`, `<input class='search'>placeholder</input>`). A distinctive feature is the **pre-computed embedding memory**: AutoDroid uses INSTRUCTOR-XL embeddings to find UI elements semantically similar to the task description, injecting `onclick` hints into the UI state. The prompt asks for structured JSON output with Steps, Analyses, Finished (Yes/No), Next step, id, action (tap/input), input_text. Before querying the LLM, AutoDroid physically scrolls through all scrollable views to collect ALL visible elements, giving the LLM complete page information. It achieves 71.3% task completion rate and 90.9% per-action accuracy.

**MobileAgent** (Alibaba X-PLUG, 2024) evolved through three versions, each adding architectural sophistication:
- **v1**: Single multimodal agent for mobile operation (ICLR 2024 Workshop)
- **v2**: Multi-agent collaboration with planning, decision, and reflection agents (NeurIPS 2024). The planning agent condenses lengthy operation histories into pure-text task progress, which is passed to the decision agent — solving the context window explosion problem.
- **v3**: Multi-modal and multi-platform support

**VLM-Fuzz** (Demissie et al., 2025, EMSE) is architecturally closest to APE-RV's approach. It combines heuristic-based recursive DFS with targeted VLM analysis for visually complex screens. The key design choice is that the VLM is **not called for every action** — it is only invoked for screens where the heuristic DFS cannot determine the appropriate interaction. This selective approach outperforms the best baseline by 9.0% class coverage, 3.7% method coverage, and 2.1% line coverage, while detecting 208 unique crashes across 24 apps.

**CovAgent** (2026, arXiv) represents the state-of-the-art. Rather than using the LLM to select GUI actions, it uses an AI agent to **analyze the app's decompiled Smali code** and component transition graph. When standard GUI fuzzing (APE, Fastbot) fails to reach certain activities, the agent reasons about unsatisfied activation conditions — such as required intents, permissions, or data prerequisites — and generates targeted actions to satisfy them. Combined with Frida dynamic instrumentation, CovAgent achieves 101.1% higher activity coverage than LLMDroid and 179.7% higher than APE.

**LELANTE** (Fatin et al., 2025, EASE) interprets natural language test case descriptions and executes them on real Android devices. It refines the verbose XML screen representation by extracting only essential interactive components (buttons, text fields, descriptions), achieving a 73% test execution success rate across 390 test cases on 10 apps.

**AndroidWorld M3A** (Google DeepMind, 2024) deserves special attention as a well-engineered multimodal agent. Source code analysis reveals it uses **SoM + Reflexion**: each step, the agent receives (1) a raw screenshot, (2) a SoM-annotated screenshot with bounding boxes and numeric indices, and (3) a textual list of UI element properties from the accessibility tree. The output format is `Reason: ... Action: {"action_type": "click", "idx": N}`. After each action, a summary step compares before/after screenshots (Reflexion-style). This combination — visual context + element indices + structured reasoning — represents the current best practice for multimodal agent design.

**AdbGPT** (Feng & Chen, 2024, ICSE) takes a different angle: automated bug reproduction from bug reports. It uses chain-of-thought prompting with few-shot examples to extract S2R (Steps to Reproduce) entities from natural language, then matches them to UI elements via an HTML encoding of the accessibility tree. The LLM (GPT-3.5, text-only) maps extracted entities to HTML element IDs using 2-shot CoT examples that demonstrate both exact and semantic matching (e.g., "Sign in" maps to "Log in" button). This demonstrates that even text-only LLMs with good prompt engineering can achieve reliable UI element matching.

---

## 5. Deep Analysis Dimensions

### 5.1 UI Representation

How tools represent the UI state to the LLM is the single most consequential design decision, because it determines the action space and directly affects match rates.

| Approach | Tools | Representation | Match Rate |
|----------|-------|---------------|------------|
| **Numbered action list** | DroidBot-GPT, GPTDroid | Text list of available actions with IDs | 100% by construction |
| **HTML-like hierarchy** | LLMDroid, LELANTE | `<button>`, `<input>` etc. with attributes | 100% (element ID selection) |
| **Hierarchical JSON** | DroidAgent, AutoDroid | JSON tree with widget properties | 100% (widget ID selection) |
| **Screenshot + SoM** | AppAgent | Screenshot with numbered labels | ~95% (fallback to grid) |
| **Screenshot + text list** | APE-RV, VisionDroid | Screenshot + widget descriptions | ~63% (APE-RV) |
| **Screenshot only** | CogAgent, SeeClick, DigiRL | Raw screenshot, coordinates output | Varies (grounding accuracy) |

The pattern is clear: **tools that constrain the LLM's output to a discrete set of valid actions achieve near-perfect match rates**, while tools that ask for free-form coordinate prediction face grounding accuracy challenges. APE-RV's 62.7% match rate (100% - 37.3% no_match) is consistent with the general-purpose VLM coordinate prediction accuracy reported by other tools — SeeClick reports similar grounding accuracy ranges on its ScreenSpot benchmark before fine-tuning.

### 5.2 Action Spaces and Coordinate Systems

| Tool | Action Format | Coordinates | Notes |
|------|--------------|-------------|-------|
| DroidBot-GPT | `action_id: int` | None | Selects from numbered list |
| GPTDroid | `action_id: int` | None | Selects from numbered list |
| LLMDroid | `{"Element Id": int, "Action Type": int}` | None | JSON with element ID + action code |
| AppAgent | `tap(element)`, `swipe(element, dir, dist)` | SoM labels | Function call with element number |
| AppAgent (grid) | `tap(area, subarea)` | Grid cells + subarea | 9 subareas per grid cell |
| DroidAgent | `touch(target_widget_ID)` | None | OpenAI function calling |
| VisionDroid | `click "widget_name"` | None | Text selection by widget name |
| CogAgent | `CLICK(box=[[x1,y1,x2,y2]])` | **Normalized [0, 1000)** | Purpose-built grounding model, same coord system as Qwen3-VL |
| MobileAgent v3 | `{"action": "click", "coordinate": [x, y]}` | **Normalized [0, 1000)** or absolute | Configurable, same convention |
| SeeClick | `click(x, y)` | Normalized [0, 1]² | Fine-tuned for grounding |
| AndroidWorld M3A | `{"action_type": "click", "idx": N}` | SoM element index | ReAct + Reflexion loop |
| DigiRL | `DUAL_POINT touch=[y,x] lift=[y,x]` | Normalized [0, 1]² | RL-trained, BLIP-2 features |
| **APE-RV** | Coordinate → ModelAction | Normalized [0, 1000) | 5-step mapping algorithm |

APE-RV's coordinate system — Qwen3-VL's [0, 1000) normalization mapped to device pixels and then to ModelActions — adds two conversion steps where errors can accumulate. Notably, **CogAgent and MobileAgent v3 use the exact same [0, 1000) normalization convention**, but CogAgent is a purpose-built 9B grounding model fine-tuned on GUI datasets, while MobileAgent v3 relies on GPT-4V/similar large models. DigiRL uses [0, 1]² normalization but with RL fine-tuning that optimizes for action accuracy. Every tool that uses raw coordinate prediction either (a) is purpose-built for grounding (CogAgent, SeeClick), (b) uses RL fine-tuning (DigiRL), or (c) is a very large model (GPT-4V in MobileAgent). APE-RV's use of a general-purpose 4B model without grounding fine-tuning is unique and explains the high no_match rate.

### 5.3 Prompt Engineering Patterns

Analysis of actual prompt templates from the cloned repositories reveals several recurring patterns:

**Pattern 1: Structured Output Templates**

The most successful tools enforce a rigid output structure. AppAgent uses:
```
Observation: <what you see>
Thought: <reasoning>
Action: <function call>
Summary: <action summary for history>
```

DroidAgent uses a similar template with numbered sections:
```
1. Summary of previous interactions: <...>
2. Description of current app state: <...>
3. Inference on remaining steps: <...>
4. Reasoning for next action: <...>
```

This structured format serves two purposes: it forces the LLM to reason before acting (chain-of-thought), and it makes parsing reliable.

**Pattern 2: Role-Based System Prompts**

DroidAgent assigns the LLM a specific persona and goal:
```
"You are a helpful assistant to guide {persona_name} to select an appropriate GUI action
to accomplish a task on an Android application named {app_name}."
```

LLMDroid frames the LLM as a testing strategist:
```
"Based on the information above, please decide: Which State should we go next,
and what function would be most appropriate to test?"
```

**Pattern 3: History Management**

Every tool includes action history, but with different granularities:
- **DroidBot-GPT**: Simple list of completed steps (text)
- **AppAgent**: Running summary updated each step (prevents context explosion)
- **DroidAgent**: Working memory with virtual conversation, spatial memory with widget knowledge, task memory with reflections
- **LLMDroid**: Page summaries + function lists (structural, not per-action)

**Pattern 4: Negative Constraints**

Effective prompts tell the LLM what NOT to do:
- LLMDroid: "Do not choose functions related to login or registration"
- DroidAgent: "I don't want to do the same actions repeatedly"
- LLMDroid: "Do not select function that has been chosen before: [list]"

**Pattern 5: JSON/Function-Call Output**

More recent tools prefer structured JSON or native function calling over text parsing:
- LLMDroid: `{"Element Id": 2, "Action Type": 4}` — pure JSON
- DroidAgent: OpenAI function calling with retry on parse failure
- AppAgent: Still uses text parsing with regex (older approach)

### 5.4 Exploration Strategy

| Tool | Strategy | LLM Role | When LLM is Called |
|------|----------|----------|-------------------|
| GPTDroid | Chat-based sequential | Action selector | Every action |
| DroidBot-GPT | Task-driven | Action selector | Every action |
| AppAgent | Two-phase (explore + deploy) | Explorer + executor | Every action |
| DroidAgent | Intent-driven + persona | Planner + actor + critic | Every action |
| LLMDroid | Traditional + LLM guidance | Strategic advisor | On coverage plateau |
| LLM-Explorer | Heuristic + knowledge | Knowledge maintainer | Periodically |
| VLM-Fuzz | DFS + VLM on complex screens | Visual analyst | On complex screens only |
| CovAgent | Fuzzer + code analysis | Code analyst | For unreachable activities |
| **APE-RV** | DFS + LLM coordinate mapping | Action enhancer | Configurable frequency |

The clear trend from 2023 to 2026 is toward **more selective LLM invocation**. Early tools (GPTDroid, DroidBot-GPT) called the LLM for every single action. The 2025-2026 tools (LLMDroid, VLM-Fuzz, CovAgent, LLM-Explorer) reserve LLM calls for situations where traditional approaches are insufficient, dramatically reducing cost while maintaining or improving effectiveness.

### 5.5 Cost and Efficiency

| Tool | Model | Cost | Strategy |
|------|-------|------|----------|
| DroidBot-GPT | GPT-3.5 | Low per-call, but every action | Every action |
| AppAgent | GPT-4V | High per-call, every action | Build docs once, use many times |
| LLMDroid (optimal) | GPT-4o | $4.77/hr | Only on coverage plateau |
| LLMDroid (cheap) | GPT-4o | $0.18/hr | Less frequent guidance |
| LLM-Explorer | Various | **148x cheaper** than SOTA | Knowledge only, not actions |
| DigiRL | 1.5B VLM | Training cost, then free | Fine-tuned, runs locally |
| **APE-RV** | Qwen3-VL-4B | Free (local SGLang) | Configurable frequency |

APE-RV's use of a local Qwen3-VL-4B model via SGLang eliminates API costs, which is a significant advantage. However, the 37.3% no_match rate means that roughly one-third of LLM inference time is wasted. The latency overhead per LLM call (1-3s) multiplied by the no_match rate translates to measurable performance degradation compared to the non-LLM baseline.

### 5.6 Reported Performance

| Tool | Metric | Result | Baseline Comparison |
|------|--------|--------|-------------------|
| GPTDroid | Activity coverage | Not reported | — |
| DroidBot-GPT | Task completion | Not reported | — |
| AppAgent | Task success rate | Varies by task | — |
| DroidAgent | Activity coverage | 61% | vs 51% SOTA |
| LLMDroid | Code coverage | +26.16% | vs DroidBot/Humanoid/Fastbot |
| LLMDroid | Activity coverage | +29.31% | vs DroidBot/Humanoid/Fastbot |
| LLM-Explorer | Coverage | Fastest + highest | 148x cheaper than SOTA |
| VLM-Fuzz | Method coverage | +3.7% | vs best baseline |
| CovAgent | Activity coverage | +101.1% | vs LLMDroid |
| DigiRL | AitW success rate | 67.2% | vs 17.7% SFT, 8.3% AppAgent |
| AUITestAgent | Bug recall | 90% at 4.5% FPR | vs manual testing |
| VisionDroid | New bugs found | 29 (19 confirmed) | On Google Play apps |
| **APE-RV** | Method coverage | 27.60% (LLM) vs 28.35% (no LLM) | LLM variant **worse** |

APE-RV's current result — where the LLM variant performs worse than the non-LLM baseline — is unique among the surveyed tools. Every other tool reports improvement from LLM integration. This strongly suggests that the problem is not with using an LLM per se, but with the specific integration approach (coordinate prediction + mapping).

---

## 6. Source Code Analysis: Prompt Excerpts

### 6.1 AppAgent — Deployment Prompt (task_template)

```
You are an agent trained to perform basic tasks on a smartphone.
The interactive UI elements on the screenshot are labeled with numeric tags starting from 1.

You can call the following functions:
1. tap(element: int)
2. text(text_input: str)
3. long_press(element: int)
4. swipe(element: int, direction: str, dist: str)
5. grid()

The task you need to complete is to <task_description>.
Your past actions: <last_act>

Output format:
Observation: <what you see>
Thought: <next step reasoning>
Action: <function call or FINISH>
Summary: <summarize past + latest action>
```

Source: `/tmp/AppAgent/scripts/prompts.py:43-91`

### 6.2 DroidAgent — Action Selection Prompt

```
System: You are a helpful assistant to guide {persona_name} to select an appropriate
GUI action on {app_name}.

User: [Current page as hierarchical JSON with widget properties including
num_prev_actions and widget_role_inference]

Guidelines:
- Note that num_prev_actions means times the widget was interacted with
- When stuck, explore a new widget that hasn't been used
- Don't repeat same actions unless clearly needed

Template:
1. Summary of previous interactions: <1-2 sentences>
2. Description of current app state: <1-2 sentences>
3. Inference on remaining steps: <1-2 sentences>
4. Reasoning for next action: <1 sentence>

[Then: "Select the next action by calling one of the given functions"]
```

Source: `/tmp/DroidAgent/droidagent/prompts/act.py:14-59`

### 6.3 DroidBot-GPT — Minimal Prompt

```python
task_prompt = f"I'm using a smartphone to {self.task}."
history_prompt = f"I have already completed the following steps: {action_history}"
state_prompt, candidate_actions = current_state.get_described_actions()
question = "Which action should I choose next? Just return the action id."
prompt = f"{task_prompt}\n{state_prompt}\n{history_prompt}\n{question}"
```

For text input: `"What should I enter to the {view_text}? Just return the text."`

Source: `/tmp/DroidBot-GPT/droidbot/input_policy.py:672-695`

### 6.4 LLMDroid — Page Overview Prompt

```
I will provide an HTML description of an app's page.
Tags: <button>, <checkbox>, <scroller>, <input>, <p>
Attributes: id, class, resource-id, content-desc, text, direction, value

Tasks:
1. Page Overview: Summarize what the page presents and what it's used for
2. Function Analysis: Identify functions with element IDs, ranked by importance
   - Navigation functions are crucial (menus, tabs, drawers)
   - Core functions central to page's purpose
   - Functions that could trigger new pages
3. Page Importance Ranking: Compare with 5 other pages

Output: JSON with "Overview", "Function List", "Top5"
```

Source: `/tmp/LLMDroid/LLMDroid-Droidbot/droidbot/policy/prompt.py:1-95`

### 6.5 LLMDroid — Guidance Prompt

```
After testing, we identified pages (States) and ranked them by importance.
Below are States from highest to lowest importance, each with Overview and
top-5 untested functions.

Decide: Which State should we go next? What function to test?

Strategies:
1. Do not select functions chosen before: [list]
2. Do not choose login/registration functions
3. Prioritize navigation-related functions
4. Choose functions that trigger transitions to undiscovered pages
5. If no navigation functions, choose core functions from higher-ranked pages

Output: {"Target State": "State2", "Target Function": "navigate to 'News'"}
```

Source: `/tmp/LLMDroid/LLMDroid-Droidbot/droidbot/policy/prompt.py:100-131`

### 6.6 VisionDroid — Exploration Prompt

```python
few_shot = """Now that you are an automated testing program for Android software,
what you have to do is test the functionality of the software as completely as possible.
I will tell you the information of the current program interface.
When you encounter components with similar names, look at them as the same category.
When you encounter many options, click from smallest to largest,
and tend to click on the component with "menu button" in its name."""

# Per-page prompt:
"The function UI page we are currently testing is {activity_name}."
"The number of exploration recorded on the current page is {visit_times}."
"Do not select the same choice as before. Now we can do these:
 1. click 'widget_name'
 2. click 'widget_name'
 ..."
"Give a number of a choice above only."
```

Source: `/tmp/VisionDroid/VisionDroid Code/prompt.py:1-57`

---

## 7. Comparative Table

| Dimension | GPTDroid | DroidBot-GPT | LLMDroid | AppAgent | DroidAgent | VisionDroid | CogAgent | SeeClick | DigiRL | VLM-Fuzz | CovAgent | **APE-RV** |
|-----------|---------|-------------|---------|---------|-----------|------------|---------|---------|-------|---------|---------|-----------|
| **Year** | 2023 | 2023 | 2025 | 2024 | 2024 | 2024 | 2024 | 2024 | 2024 | 2025 | 2026 | 2024-26 |
| **Multimodal** | No | No | No | Yes | No* | Partial | Yes | Yes | Yes | Yes | No | Yes |
| **UI repr.** | Text list | Text list | HTML | Screenshot+SoM | JSON tree | Text list | Screenshot | Screenshot | Screenshot | Screenshot+XML | Smali code | Screenshot+list |
| **Action space** | ID selection | ID selection | ID+type | Function call | Function call | ID selection | Coordinates | Coordinates | Coordinates | Heuristic+VLM | Frida inject | Coordinates |
| **Coord system** | — | — | — | Element # | Widget ID | — | Absolute | [0,1]² | — | — | — | [0,1000) |
| **Match rate** | 100% | 100% | 100% | ~95% | 100% | 100% | Varies | Varies | N/A | N/A | N/A | **62.7%** |
| **LLM frequency** | Every action | Every action | On plateau | Every action | Every action | Every action | Every action | Every action | N/A (trained) | Complex screens | Unreachable only | Configurable |
| **Exploration** | Chat-based | Task-driven | Traditional+guidance | Two-phase | Intent+persona | Function-aware | — | — | RL-trained | DFS+VLM | Fuzzer+code | DFS+LLM |
| **Memory** | History list | History list | Page summaries | UI docs | Spatial+task memory | Visit counts | — | — | RL weights | — | — | WTG+scores |
| **Model** | GPT-3 | GPT-3.5 | GPT-4o | GPT-4V | GPT-4 | GPT-4V | CogAgent-18B | Qwen-VL | 1.5B VLM | VLM | Agentic | Qwen3-VL-4B |

*DroidAgent uses GPT-4 text API with function calling, not vision capabilities.

---

## 8. Technical Implications for APE-RV gh43

### 8.1 The Core Problem: Coordinate Prediction Without Grounding

APE-RV's 37.3% no_match rate is not a bug — it is a predictable consequence of using a general-purpose VLM (Qwen3-VL-4B) for coordinate prediction without grounding fine-tuning. The survey reveals that:

1. **No other testing tool** uses raw coordinate prediction from a general-purpose VLM as its primary action mechanism.
2. Tools that use coordinates (CogAgent, SeeClick, ShowUI) are **purpose-built grounding models** fine-tuned specifically for GUI element localization.
3. The most successful tools **eliminate the coordinate mapping problem entirely** by constraining LLM output to discrete action choices.

### 8.2 Recommended Approaches (Ranked by Impact)

**Approach A: Action-List Selection (highest impact, lowest risk)**

Convert APE-RV's LLM integration to provide the list of available ModelActions as numbered choices alongside the screenshot. The LLM selects an action by number, not by coordinate. This eliminates no_match by construction.

This is exactly what DroidBot-GPT, LLMDroid, and VisionDroid do — and all three report significant improvements over their baselines. The prompt would look like:

```
You are exploring an Android app to maximize code coverage.
Current screenshot is attached. Available actions:
1. Click "Login" button (center: 540, 1200)
2. Click "Settings" icon (center: 980, 120)
3. Type in "Username" field (center: 540, 800)
4. Scroll down on main content area
5. Press Back

Which action should I choose? Return the number only.
```

**Approach B: Set-of-Marks Overlay (high impact, moderate effort)**

Overlay numbered labels on the screenshot at each ModelAction's coordinates before sending to the LLM. This is AppAgent's approach and preserves the visual context that coordinate prediction was meant to provide, while eliminating ambiguity.

This requires a preprocessing step (drawing numbers on the screenshot) but no changes to the coordinate mapping algorithm — the mapping simply becomes a dictionary lookup by label number.

**Approach C: Selective LLM Invocation (medium impact, complementary)**

Adopt LLMDroid/VLM-Fuzz's approach: use the LLM only when the traditional exploration algorithm gets stuck (detected by coverage plateau or repeated state visits). This reduces wasted LLM calls and focuses the LLM's contribution on situations where it can actually help — breaking out of exploration dead-ends.

This is complementary to Approaches A or B and could be combined with either.

**Approach D: Grounding Model Replacement (high impact, high effort)**

Replace Qwen3-VL-4B with a purpose-built grounding model (SeeClick or ShowUI) that has been fine-tuned for GUI element localization. This preserves the coordinate prediction paradigm but with much higher accuracy.

SeeClick is based on Qwen-VL (same family as APE-RV's Qwen3-VL) and could potentially be served via SGLang with minimal infrastructure changes. However, it would require evaluating whether the grounding model's accuracy justifies the switch.

**Approach E: Two-Phase Knowledge Building (long-term)**

Adopt AppAgent/DroidAgent's approach of building reusable app knowledge during an exploration phase, then using that knowledge to guide more efficient testing. In APE-RV's context, this could mean: (1) run a short LLM-guided exploration to map out the app's structure and widget functions, (2) use this knowledge map to prioritize actions during the main DFS exploration.

### 8.3 Validation Framework Implications

For the gh43 offline validation module, the survey suggests these specific prompt variants to test:

1. **Baseline**: Current APE-RV prompt (screenshot + widget list → coordinates)
2. **Action-list**: Screenshot + numbered ModelAction list → action ID
3. **SoM**: Annotated screenshot with numbered labels → element number
4. **Structured**: Action-list + Observation/Thought/Action/Summary template
5. **Guidance-only**: Traditional exploration + LLM guidance on plateau (simulate LLMDroid approach)
6. **Hybrid**: Screenshot + action list + "If none of these actions seem useful, predict coordinates for the most promising element"

Variants 2-4 should achieve near-100% match rate while maintaining the visual context that motivated multimodal LLM integration in the first place.

---

## 9. References

### Papers

1. Zheng et al. "Chatting with GPT-3 for Zero-Shot Human-Like Mobile Automated GUI Testing" (GPTDroid), arXiv:2305.09434, 2023.
2. Wen et al. "DroidBot-GPT: GPT-powered UI Automation for Android", arXiv, 2023. [GitHub](https://github.com/MobileLLM/DroidBot-GPT)
3. Yang et al. "AppAgent: Multimodal Agents as Smartphone Users", arXiv:2312.13771, 2024. [GitHub](https://github.com/TencentQQGYLab/AppAgent)
4. Yoon et al. "Intent-Driven Mobile GUI Testing with Autonomous Large Language Model Agents" (DroidAgent), ICSE 2024. [GitHub](https://github.com/coinse/droidagent)
5. Wen et al. "AutoDroid: LLM-powered Task Automation in Android", MobiCom 2024. [GitHub](https://github.com/MobileLLM/AutoDroid)
6. Liu et al. "VisionDroid: Vision-driven Automated Mobile GUI Testing via Multimodal Large Language Model", arXiv:2407.03037, 2024. [GitHub](https://github.com/testtestA6/VisionDroid)
7. Wang et al. "Mobile-Agent: Autonomous Multi-Modal Mobile Device Agent with Visual Perception", ICLR 2024 Workshop. [GitHub](https://github.com/X-PLUG/MobileAgent)
8. Wang et al. "Mobile-Agent-v2: Mobile Device Operation Assistant with Effective Navigation via Multi-Agent Collaboration", NeurIPS 2024.
9. Hong et al. "CogAgent: A Visual Language Model for GUI Agents", CVPR 2024 (Highlight). [GitHub](https://github.com/THUDM/CogAgent)
10. Cheng et al. "SeeClick: Harnessing GUI Grounding for Advanced Visual GUI Agents", ACL 2024. [GitHub](https://github.com/njucckevin/SeeClick)
11. Lin et al. "ShowUI: One Vision-Language-Action Model for GUI Visual Agent", CVPR 2025. [GitHub](https://github.com/showlab/ShowUI)
12. Zhou et al. "DigiRL: Training In-The-Wild Device-Control Agents with Autonomous Reinforcement Learning", NeurIPS 2024. [GitHub](https://github.com/DigiRL-agent/digirl)
13. "UINav: A Maker of UI Automation Agents", arXiv:2312.10170, 2024.
14. "LLMDroid: Enhancing Automated Mobile App GUI Testing Coverage with Large Language Model Guidance", FSE 2025. [GitHub](https://github.com/LLMDroid-2024/LLMDroid)
15. Zhao et al. "LLM-Explorer: Towards Efficient and Affordable LLM-based Exploration for Mobile Apps", MobiCom 2025. [GitHub](https://github.com/MobileLLM/LLM-Explorer)
16. Demissie et al. "VLM-Fuzz: Vision Language Model Assisted Recursive Depth-first Search Exploration for Effective UI Testing of Android Apps", EMSE 2025. [arXiv](https://arxiv.org/abs/2504.11675)
17. "CovAgent: Overcoming the 30% Curse of Mobile Application Coverage with Agentic AI and Dynamic Instrumentation", arXiv:2601.21253, 2026.
18. Fatin et al. "LELANTE: LEveraging LLM for Automated ANdroid TEsting", EASE 2025. [arXiv](https://arxiv.org/abs/2504.20896)
19. "AUITestAgent: Automatic Requirements Oriented GUI Function Testing", arXiv:2407.09018, 2024. [GitHub](https://github.com/bz-lab/AUITestAgent)
20. Feng et al. "Prompting Is All You Need: Automated Android Bug Replay with Large Language Models" (AdbGPT), ICSE 2024.

### Surveys and Benchmarks

21. "GUI-Agents-Paper-List", OSU-NLP-Group. [GitHub](https://github.com/OSU-NLP-Group/GUI-Agents-Paper-List)
22. "Awesome-GUI-Agent", showlab. [GitHub](https://github.com/showlab/Awesome-GUI-Agent)
23. "AndroidWorld: A Dynamic Benchmarking Environment for Autonomous Agents", Google DeepMind, 2024. [arXiv](https://arxiv.org/abs/2405.14573)
24. "A Survey on Benchmarks of LLM-based GUI Agents", TechRxiv, 2024.
25. "Vision-Based Mobile App GUI Testing: A Survey", 2024.

### Related Grounding Models

26. "UGround: Universal Visual Grounding for GUI Agents", ICLR 2025 (Oral). [GitHub](https://github.com/OSU-NLP-Group/UGround)
27. "Ferret-UI: Grounded Mobile UI Understanding with Multimodal LLMs", Apple, 2024.
28. "ARIA-UI: Visual Grounding for GUI Instructions", 2024.

---

## 10. APE-RV Positioning in the State of the Art

This section summarizes where APE-RV stands relative to the surveyed tools, identifying both its unique contributions and the gaps revealed by this SOTA analysis.

### 10.1 What APE-RV Does Differently

APE-RV occupies a unique niche that no other surveyed tool fills:

1. **Runtime verification integration**: APE-RV is the only tool that combines LLM-driven GUI exploration with runtime verification (MOP monitoring). Every other tool focuses exclusively on coverage, bug detection, or task completion — none monitors API misuse specifications during exploration.
2. **Hybrid algorithmic/LLM exploration**: APE-RV's DFS-based strategy with configurable LLM routing (algorithm vs LLM decisions) is architecturally distinct. VLM-Fuzz comes closest (DFS + VLM on complex screens), but lacks the scorer-based prioritization, successor tracking, and plateau detection that APE-RV implements.
3. **Local small model**: APE-RV runs Qwen3-VL-4B locally via SGLang, eliminating API costs entirely. Most other tools depend on GPT-4V/GPT-4o API calls ($4–20/hr). Only DigiRL (1.5B fine-tuned VLM) and CogAgent (9B fine-tuned VLM) also use local models, but both require expensive fine-tuning.

### 10.2 Gaps Revealed by This Survey

1. **Action mapping approach**: APE-RV's coordinate prediction → widget mapping is the weakest link. The SOTA has converged on two proven alternatives: (a) action-list selection (100% match by construction) and (b) Set-of-Marks (near-100% match with visual context). The 37.3% no_match rate is not competitive with any surveyed tool.
2. **LLM invocation frequency**: APE-RV calls the LLM on a configurable fraction of actions, but the 2025-2026 SOTA (LLMDroid, LLM-Explorer, VLM-Fuzz, CovAgent) demonstrates that selective invocation — only when the exploration is stuck — is far more cost-effective and often more performant.
3. **Prompt engineering**: APE-RV's prompts lack the structured output templates (Observation/Thought/Action/Summary), negative constraints ("do not repeat actions"), and history management that are standard across AppAgent, DroidAgent, and LLMDroid.
4. **Reflection/validation**: AppAgent, DroidAgent, MobileAgent v2/v3, and AndroidWorld M3A all include post-action reflection (comparing before/after screenshots to validate effectiveness). APE-RV does not validate whether the LLM-selected action produced the expected effect.

### 10.3 Recommended SOTA-Informed Changes for gh43

| Priority | Change | SOTA Basis | Expected Impact |
|----------|--------|-----------|-----------------|
| **P0** | Switch from coordinate prediction to action-list selection | DroidBot-GPT, LLMDroid, VisionDroid | Eliminates 37.3% no_match |
| **P1** | Add structured output template (Observation/Thought/Action) | AppAgent, DroidAgent | Improves action quality and parseability |
| **P1** | Include exploration history in prompt | All surveyed tools | Avoids repetitive actions |
| **P2** | Selective LLM invocation (on coverage plateau only) | LLMDroid, VLM-Fuzz, LLM-Explorer | Reduces wasted LLM overhead |
| **P3** | Post-action reflection (before/after comparison) | AppAgent, MobileAgent, M3A | Detects ineffective actions early |
| **P3** | Two-phase knowledge building | AppAgent, DroidAgent | Amortizes LLM cost across exploration |

### 10.4 Open Research Opportunities

The survey also reveals areas where APE-RV could contribute novel research beyond what exists in the SOTA:

- **MOP-aware exploration guidance**: No tool uses runtime verification feedback to guide exploration. APE-RV could use MOP coverage data to direct the LLM toward UI paths likely to trigger monitored operations — a form of specification-driven testing that is absent from the literature.
- **Static analysis + LLM synergy**: CovAgent uses Smali code analysis, but APE-RV already has GATOR-based static analysis (reachability, WTG, transitions). Combining WTG data with LLM guidance — "navigate to Activity X because it contains reachable methods Y, Z" — would be a novel contribution.
- **Local small model optimization**: The SOTA uses either large cloud models (GPT-4V) or fine-tuned small models (DigiRL, CogAgent). APE-RV's approach of prompting a general-purpose 4B local model is under-explored. Optimizing prompts specifically for Qwen3-VL-4B's strengths (coordinate normalization, tool calling) could establish a cost-effective baseline for the community.

---

## 11. Deep Source Code Analysis

This section documents detailed findings from reading the source code of the 10 cloned repositories (Section 2). While the preceding sections summarize tool architectures and strategies at a conceptual level, this section examines six specific dimensions (D1–D6) at the code level, with comparative tables and concrete excerpts that inform APE-RV's gh43 design decisions.

### 11.1 Image Pipeline (D1)

How tools preprocess screenshots before sending them to the LLM is a critical and under-discussed design choice. The pipeline affects token count, spatial reasoning accuracy, and coordinate grounding precision.

| Tool | Resize | Format | Encoding | Multiple Images | Annotations |
|------|--------|--------|----------|-----------------|-------------|
| AppAgent | None (raw device resolution) | PNG | base64 (MIME says jpeg) | Yes (before/after) | SoM: pyshine+OpenCV, alpha=0.5, numbers at center+10px |
| MobileAgent v3 | smart_resize(factor=28) | PNG | base64 with data URI | Yes (before/after reflection) | None |
| DroidBot-GPT | N/A (text-only) | N/A | N/A | N/A | N/A |
| LLMDroid | N/A (text-only) | N/A | N/A | N/A | N/A |
| DroidAgent | N/A (text-only) | N/A | N/A | N/A | N/A |
| AutoDroid | N/A (text-only) | N/A | N/A | N/A | N/A |
| VisionDroid | None (text for exploration, raw PNG for bugs) | JPG | base64 | Yes (sequence for bug detection) | Red bboxes + numbers for bug detection |
| AUITestAgent | Unknown | PNG | Unknown | Unknown | SoM: blue filled rectangles + white number labels |
| DigiRL | BLIP-2 AutoProcessor (224x224) | N/A (features) | 1408-dim pooler output | 2-frame stacking for critic | None |
| **APE-RV** | max-edge 1000px, JPEG q80 | JPEG | base64 (no data URI) | No | None |

MobileAgent v3 uses `factor=28` because it targets Qwen2.5-VL, where the vision encoder uses patch_size=14 and merge_size=2 (14 x 2 = 28). For Qwen3-VL — APE-RV's model — the correct factor is 32 (patch_size=16 x merge_size=2).

**Key finding: APE-RV's max-edge 1000px resize is not optimized for Qwen3-VL.** The `smart_resize` function ensures image dimensions are divisible by the vision encoder's patch alignment factor, avoiding padding or truncation in the ViT encoder. APE-RV's current resize of a 1080x1920 device screenshot to 562x1000 produces dimensions not divisible by 32, which can degrade spatial reasoning and coordinate grounding accuracy.

AppAgent's SoM implementation (from `scripts/utils.py`) uses `draw_bbox_multi()` with pyshine for text labels and OpenCV for I/O. Labels are sequential integers placed at element centers with +10px offset. The style uses font_scale=1, thickness=2, alpha=0.5 blending, dark background (10,10,10) with light text (255,250,250). A MIN_DIST=30px threshold prevents label overlap. When the UI is too dense for individual labels, a grid fallback (`draw_grid()`) divides the screenshot into 120-180px cells with coral-colored (255,116,113) numbered cells.

### 11.2 Coordinate Systems and Conversion (D2)

This is the most critical dimension for APE-RV. The analysis reveals that APE-RV is the **only** tool in the SOTA with three coordinate spaces in its pipeline.

| Tool | # Spaces | Spaces | Conversion |
|------|----------|--------|------------|
| DroidBot-GPT | 1 | Element ID to bounds center | `(bounds[0]+bounds[1])//2` |
| LLMDroid | 1 | Element ID to bounds center | Same |
| DroidAgent | 1 | Widget ID to bounds center | Same via function calling enum |
| AutoDroid | 1 | Element ID to bounds center | Same |
| VisionDroid | 1 | Widget name to bounds center | `(x1+x2)//2, (y1+y2)//2` |
| AppAgent | 1 | SoM label to bounds center | `(tl+br)//2` |
| MobileAgent v3 | 2 | [0,999] to device pixels | `int(normalized / 1000 * device_size)` |
| CogAgent | 2 | [0,1000) to device pixels | `x/1000, y/1000` then scale |
| DigiRL | 2 | [0,1] to device pixels | `normalized * screen_size` |
| **APE-RV** | **3** | resized image to [0,1000) to device pixels | 2-step conversion with error accumulation |

Six of the ten surveyed tools have only one coordinate space because the LLM selects an element by ID or label rather than predicting coordinates. The three VLM-based tools that do predict coordinates (MobileAgent v3, CogAgent, DigiRL) all use two spaces: a model-native normalized space and device pixels. APE-RV alone has three spaces: the resized image (562x1000), Qwen-VL's normalized [0,1000) range, and device pixels (1080x1920). Each conversion step introduces rounding error.

MobileAgent v3's denormalization (from `run_mobileagentv3.py`):

```python
if coor_type != "abs":
    action_object['coordinate'] = [
        int(action_object['coordinate'][0] / 1000 * width),
        int(action_object['coordinate'][1] / 1000 * height)
    ]
```

However, the reverse direction in `coordinate_resize.py` uses 999, not 1000:

```python
elif tgt_format == "qwen-vl":
    new_bbox = [
        int(x1 / image_ele["width"] * 999),
        int(y1 / image_ele["height"] * 999),
        ...
    ]
```

This 999 vs 1000 asymmetry may be significant. If the model's internal range is [0, 999] (inclusive), then denormalizing with `/1000` introduces a systematic off-by-one at the boundaries. DigiRL takes a different approach, using [0,1] normalized coordinates in (y,x) order — reversed from the standard (x,y) convention — which has its own error risk.

**Key finding**: APE-RV's 3-space pipeline accumulates conversion error at two stages. Eliminating the resized-image space (by using `smart_resize(factor=32)` which aligns to the model's native patch grid) would reduce this to a 2-space pipeline matching the SOTA pattern.

### 11.3 Prompt Architecture Deep Dive (D3)

Beyond the high-level prompt strategies described in Sections 6-9, the source code reveals specific patterns in prompt structure, constraint framing, and history management.

**Structured output templates.** DroidAgent enforces a 4-step Chain-of-Thought in every response (from `prompts/act.py`):

```
1. Summary of previous interactions: <1-2 sentences>
2. Description of current app state: <1-2 sentences>
3. Inference on remaining steps: <1-2 sentences>
4. Reasoning for next action: <1 sentence>
```

This structured decomposition forces the model to reason about state and progress before selecting an action. DroidAgent further constrains actions via function calling with dynamic enum — the `target_widget_ID` parameter only accepts IDs present in the current screen, making invalid selections impossible at the schema level.

**UI encoding strategies.** LLMDroid and AutoDroid both encode the UI hierarchy as HTML, but with notable differences. LLMDroid (from `desc/widget.py`) maps Android widget types to 5 HTML classes: `<button>`, `<checkbox>`, `<input>`, `<scroller>`, and `<p>`. Non-interactive elements use `<p>` tags without an `id` attribute, implicitly preventing the LLM from selecting them. A hard cap of max depth 25 and max 100 tags prevents token overflow. Nested single-child nodes are collapsed during widget merging. AutoDroid takes a similar approach but adds a key optimization: it pre-scrolls all scrollable views to collect every element before querying the LLM, ensuring the action list is complete.

**Multi-agent decomposition.** MobileAgent v3 splits the workflow across four prompt personas: a Manager for high-level planning, an Executor for action selection (outputting JSON like `{"action": "click", "coordinate": [x, y]}`), an ActionReflector that compares before/after screenshots with three possible outcomes (A=success, B=wrong page triggering auto-back, C=no change), and a Notetaker that persists important information across steps.

**Negative constraints.** A universal pattern across the SOTA is explicit negative instructions. Examples from the source code:

- LLMDroid: *"Do not select function that has been chosen before: [list]"*
- LLMDroid: *"Do not choose functions related to login or registration"*
- DroidAgent: *"I don't want to do the same actions repeatedly"*
- MobileAgent v3: *"Do NOT repeat previously failed actions multiple times"*
- MobileAgent v3: *"Please make sure the start and end points of your swipe are within the swipeable area and away from the keyboard (y1 < 1400)"*

APE-RV's prompts currently lack any negative constraints.

**History management** varies significantly in approach and window size:

| Tool | Approach | Window |
|------|----------|--------|
| DroidBot-GPT | Simple list of completed steps | Full history |
| AppAgent | Running summary (overwritten each step) | 1 summary |
| DroidAgent | Virtual conversation + spatial memory (ChromaDB) | Recent + retrieved |
| LLMDroid | Page summaries + function lists | Per-cluster |
| MobileAgent v3 | Last N actions (sliding window) | 5 actions |
| DigiRL | Last action (online) or 8 (client) | 1-8 actions |

AppAgent's approach is particularly efficient: instead of growing the context window, it maintains a single running summary that is overwritten each step. DroidAgent's ChromaDB-backed spatial memory is the most sophisticated — it stores per-widget knowledge including `num_prev_actions` and inferred widget roles, retrieving relevant context by similarity rather than recency.

### 11.4 Action Space Design (D4)

The action space — what actions the LLM can select and how they are encoded — determines both the expressiveness and the error rate of the LLM integration.

| Tool | Actions | Encoding | Scroll | Text Input |
|------|---------|----------|--------|------------|
| DroidBot-GPT | click, edit, scroll, back | Integer ID | scroll up/down (action IDs) | Follow-up prompt |
| LLMDroid | click, long_press, 4 swipes, input | JSON `{"Element Id": N, "Action Type": N}` | 4 directional (types 2-5) | Type 6 |
| DroidAgent | touch, long_touch, scroll, set_text, go_back, wait, end_task | Function calling with dynamic enum | 4 directions + widget ID | 3rd LLM call |
| AutoDroid | tap, input | JSON `{"id": N, "action": "tap/input"}` | Pre-scrolling (external) | Same call |
| AppAgent | tap, text, long_press, swipe, grid, FINISH | Text calls `tap(5)` | `swipe(elem, dir, dist)` | `text("content")` |
| MobileAgent v3 | click, long_press, type, system_button, swipe, answer | JSON `{"action": "click", "coordinate": [x,y]}` | `swipe` with 2 coords | `type` action |
| VisionDroid | click, back | Integer selection | None | None |
| DigiRL | DualPoint, Type, GoBack, GoHome, Enter, TaskComplete | Text string | DualPoint with dist > sqrt(10) | Type action |

Two patterns emerge. **ID-based tools** (DroidBot-GPT, LLMDroid, AutoDroid, VisionDroid) have the narrowest action spaces and rely on the UI dump for all targeting — the LLM never predicts coordinates. **Coordinate-based tools** (MobileAgent v3, DigiRL) have richer action spaces but require the LLM to accurately predict touch locations. AppAgent bridges both: SoM labels for identified elements, with a grid fallback for when the LLM needs to interact with something not in the element list.

DroidAgent's function calling with dynamic enum is notable: the `target_widget_ID` parameter's allowed values change every step to reflect only the widgets present on the current screen. This makes invalid element selection impossible at the API schema level — a stronger guarantee than post-hoc parsing and validation.

### 11.5 Output Parsing and Matching (D5)

How tools parse LLM output and handle malformed responses directly affects robustness.

| Tool | Parsing Method | Error Handling | Retry |
|------|---------------|----------------|-------|
| AppAgent | Regex on `Action:` line | `["ERROR"]` breaks loop | None |
| DroidAgent | Function calling + JSON parse | 3-retry with error feedback | Yes (3 attempts) |
| AutoDroid | `ast.literal_eval()` | Falls back to id=-1 (task finished) | None |
| DroidBot-GPT | `re.search(r'\d+', response)` | Returns None, falls back to random action | None |
| LLMDroid | Extract first `{` to last `}`, `json.loads()` | Infinite recursive retry | Unlimited |
| MobileAgent v3 | Section splitting + `json.loads()` | Sets action to "invalid", continues | 10 retries on LLM call |
| VisionDroid | `int(output.split(".")[0]) - 1` | Uncaught exception | 5 retries if no newline |
| DigiRL | Custom text parser for DUAL_POINT format | 3 retries with 60s timeout | Yes |

The most robust approaches are DroidAgent (function calling eliminates most parse errors; 3-retry with error feedback for the remainder) and MobileAgent v3 (10 retries with graceful degradation to "invalid" action). The least robust are VisionDroid (uncaught exceptions on parse failure) and LLMDroid (infinite recursive retry on malformed JSON — a potential infinite loop).

DroidBot-GPT's fallback to random action on parse failure is pragmatic for exploration: a random action is better than crashing, and the next LLM call gets a fresh opportunity to guide exploration.

### 11.6 Novel Techniques (D6)

The source code reveals techniques not apparent from reading papers alone. These are grouped by their applicability to APE-RV's gh43 scope.

**Directly applicable (gh43 scope):**

1. **smart_resize(factor=32)**: MobileAgent v3's Qwen-optimized image preprocessing ensures dimensions are divisible by the vision encoder's patch alignment factor. For Qwen3-VL, the correct factor is 32 (patch_size=16 x merge_size=2), not 28 as in MobileAgent v3 which targets Qwen2.5-VL. This is a low-effort, high-impact change.

2. **Before/after reflection**: Both AppAgent (4-outcome: BACK/INEFFECTIVE/CONTINUE/SUCCESS) and MobileAgent v3 (3-outcome: A=success, B=wrong page triggering auto-back, C=no change) compare screenshots before and after action execution to validate effectiveness. This pattern could detect and recover from APE-RV's no_match actions.

3. **Negative constraints in prompts**: Every surveyed tool includes explicit negative instructions (avoid repeated actions, avoid login screens, stay within swipeable areas). APE-RV's prompts lack any such constraints. Adding them is zero-cost.

**Future applicability (beyond gh43):**

4. **Grid fallback** (AppAgent): When the LLM encounters elements visible on screen but absent from the UI dump, it calls `grid()` to receive a grid-annotated screenshot and selects a cell+subarea. This elegantly handles stale XML — a known problem in Android testing.

5. **Plateau-based selective invocation** (LLMDroid): An adaptive threshold on the coverage growth rate sliding window triggers LLM invocation only when exploration stalls. This reduces LLM cost by 148x compared to per-action invocation.

6. **Pre-scrolling** (AutoDroid): Before querying the LLM, all scrollable views are scrolled to collect every element, ensuring the action list is complete. This prevents the LLM from being unaware of off-screen elements.

7. **Widget cropping** (AUITestAgent): Individual widgets are cropped from the screenshot for detailed VLM analysis, with a fallback dual-mode detection when `uiautomator dump` fails.

8. **Spatial memory** (DroidAgent): ChromaDB-backed per-widget knowledge stores `num_prev_actions` and inferred widget roles, retrieved by similarity rather than recency. This allows the LLM to recall what happened with a specific widget even hundreds of steps ago.

9. **RL fine-tuning** (DigiRL): Advantage-weighted regression on filtered trajectories using binary advantage scoring (gamma=0.5) with Gemini-judged rewards. This is the only tool that fine-tunes the VLM on exploration experience rather than relying solely on prompting.

### 11.7 Implications for APE-RV gh43

The deep source code analysis crystallizes five actionable implications for the gh43 validation experiment.

**Image processing.** APE-RV's max-edge 1000px resize is suboptimal for Qwen3-VL. The `smart_resize(factor=32)` approach from MobileAgent v3 ensures image dimensions align with the vision encoder's patch grid, avoiding padding artifacts that degrade spatial reasoning. This should be tested as an orthogonal variable — the improvement may be significant enough to affect coordinate grounding accuracy independently of prompt changes.

**Coordinate pipeline.** APE-RV's unique 3-space pipeline (resized image to [0,1000) to device pixels) introduces error accumulation at two conversion stages. No other surveyed tool has more than two coordinate spaces. The 999 vs 1000 asymmetry discovered in MobileAgent v3's normalization code warrants investigation — if Qwen3-VL's internal coordinate range is [0, 999] inclusive, APE-RV's denormalization with `/1000` introduces a systematic boundary error.

**Prompt engineering.** APE-RV lacks three patterns that are standard across the SOTA: negative constraints (preventing repeated/invalid actions), structured Chain-of-Thought output templates (forcing reasoning before action selection), and reflection patterns (validating action effectiveness). These should be incorporated as prompt variant dimensions in the gh43 experiment.

**SoM as fallback variant.** AppAgent-style Set-of-Marks overlay — where numbered labels replace coordinate prediction for identified elements — is a viable fallback variant that preserves APE-RV's agentic tool-calling design. The LLM would receive tool parameters with id/label instead of coordinates, eliminating coordinate prediction for labeled elements. However, the primary focus should remain on improving coordinate grounding quality, since APE-RV specifically targets dynamic elements not captured by the UIAutomator dump.

**Pre-validation via grounding test.** A quick grounding-only test — per-widget "click on X" prompts comparing max-edge resize vs smart_resize, without full exploration — can establish the VLM's baseline grounding capability and validate the image processing improvement before investing compute in full prompt variant evaluation.

---

*This SOTA survey was generated through 12 web searches, source code analysis of 10 cloned repositories, and structured reasoning via sequential thinking. Source code excerpts are from repositories as of 2026-03-19. Curated paper lists for ongoing tracking: [GUI-Agents-Paper-List](https://github.com/OSU-NLP-Group/GUI-Agents-Paper-List), [Awesome-GUI-Agent](https://github.com/showlab/Awesome-GUI-Agent).*
