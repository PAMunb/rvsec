# RVSmart Prompt Refactoring Plan

## Context and Motivation

RVSmart is a testing tool developed as an adaptation of RVAndroid, replacing DroidBot with UIAutomator for Android application testing. The primary objective is to discover monitored operations violations and increase test coverage. Currently, prompts are too large, impacting inference speed and potentially reducing effectiveness in finding errors.

### Hardware Considerations
- **GPU Resources**: 16GB VRAM available
- **Model Selection**: User responsibility to configure experiments within hardware limits
- **Optimization Focus**: Token reduction and inference efficiency rather than hardware constraints

## Current System Analysis

### RVSmart Architecture
- **Modular architecture** based on fragments
- **Structured XML templates** with system/user roles
- **Specialized strategies**: single, batch, vision (mop_vision will be merged)
- **Framework based on rv-llm** focused on monitored operations discovery and coverage increase

## Data Architecture Hierarchy

### State Dictionary - The Foundational Container

The RVSmart prompt system is built on a **State Dictionary** (`OrderedDict`) that serves as the central data container orchestrating all information flow. This state uses `StateEntry` constants as type-safe keys and contains all data consumed by fragments:

**State Architecture**:
- **Central Container**: All prompt data flows through the state dictionary
- **Type Safety**: Uses `StateEntry` constants (25+ defined keys) to prevent string mismatches
- **Data Orchestration**: Coordinates between StateEnricher, fragments, and template system
- **Complete Context**: Contains application context, UI state, coverage metrics, history, and analysis results

**Key StateEntry Categories**:
- **Application Context**: `PACKAGE_NAME`, `ACTIVITY`, `PREVIOUS_ACTIVITY`
- **UI Structure**: `STRUCTURED_SCREEN`, `SCREEN_DESCRIPTION`, `AVAILABLE_ACTIONS`
- **Coverage Metrics**: `COVERAGE_METRICS`, `METHOD_COVERAGE`, `ACTIVITY_COVERAGE`, `MOP_COVERAGE_*`
- **Visual Data**: `SCREENSHOT_PATH`, `SCREENSHOT_INFO`, `VIEW_TREE`
- **Analysis Results**: `MONITORED_OPERATIONS`, `STATIC_DATA`, `DETECTED_PATTERN`
- **Memory & History**: `ACTION_HISTORY`, `MEMORY_INSIGHTS`, `NAVIGATION_PATH`

### Four-Pillar Data System (Priority Order)

Built on top of the state dictionary foundation, the RVSmart prompt system organizes information into four critical data pillars, ordered by importance:

#### 1. **ScreenDescription** (HIGHEST PRIORITY)
- **Role**: Primary UI structure representation and main prompt component
- **Sources**: 
  - Static analysis (layout structure, widget definitions)
  - Screenshot analysis (visual elements, dynamic content)
  - Enriched visitor data (coordinate information, interaction capabilities)
- **StateEnricher Integration**: Complex 4-phase enrichment process via `state_enricher.py`:
  - **Phase 1**: Screen description generation using configurable visitor patterns (DefaultTextVisitor, Enhanced, etc.)
  - **Phase 2**: Screenshot processing with LLMImageContent creation for multimodal models
  - **Phase 3**: ScreenDescription text update incorporating visual enhancements and annotations
  - **Phase 4**: Monitored operations integration from static analysis data
- **Template-Visitor Alignment**: Dynamic visitor selection based on configuration (`visitor_type`)
- **Multimodal Enhancement**: Screenshot complementor adds visual mapping and enhanced screen analysis
- **State Storage**: 
  - `STRUCTURED_SCREEN`: Complete ScreenDescription object for programmatic access
  - `SCREEN_DESCRIPTION`: String representation for prompt consumption
  - `AVAILABLE_ACTIONS`: Action ID mapping for execution
- **Critical**: This is the foundation - all other data enhances or guides the interpretation of ScreenDescription

#### 2. **UI Coverage Tracker** (SECOND PRIORITY) 
- **Role**: UI element-level visit metrics and interaction history (distinct from system coverage)
- **Features**: [UNTESTED]/[TESTED-Nx] annotations, coverage statistics, action distribution
- **UI vs System Coverage Distinction**:
  - **UI Coverage**: Element-level interaction tracking, visit counts, action success rates
  - **System Coverage**: Method/activity/class coverage from system execution
  - **Different Purpose**: UI coverage guides immediate LLM decisions, system coverage provides strategic context
- **Importance**: Provides crucial guidance for systematic exploration and prevents interaction loops
- **Location**: `modules/rvsmart-tool/src/rvsmart_tool/core/memory/ui_coverage_tracker.py`
- **Note**: Must NOT be over-compressed as these metrics directly guide LLM decisions

#### 3. **Transition Manager** (THIRD PRIORITY)
- **Role**: Activity transition data and navigation patterns
- **Features**: Inter-activity navigation tracking, transition recommendations
- **Data Format**: "Click button X may transition to activity Y" information
- **Standardized Format**: Well-defined structure via `get_transition_guidance()` method:
  - **Static Transitions**: From static analysis WTG (Window Transition Graph)
  - **Dynamic Transitions**: Runtime-observed transitions with success tracking
  - **Visit Statistics**: Activity visit counts and transition frequencies  
  - **Unexplored Actions**: Actions that may lead to new activities
  - **Data Grouping**: Multiple actions leading to same activity are properly aggregated
- **State Storage**: `TRANSITION_GUIDANCE` key contains structured dictionary
- **Integration**: Via TransitionManager service providing navigation context

#### 4. **System Coverage** (FOURTH PRIORITY)
- **Role**: Overall system coverage metrics (activities, classes, methods)
- **Features**: High-level coverage statistics and exploration completeness
- **Usage**: Strategic guidance for overall exploration effectiveness

### Implementation Status from Previous Plan (24/08/2024)

#### ✅ Already Implemented in RVSmart:

1. **UICoverageTracker System** - **CRITICAL IMPORTANCE**
   - Contains comprehensive UI element visit metrics (distinct from system coverage)
   - Features: [UNTESTED]/[TESTED-Nx] annotations, coverage statistics
   - Integration: ActionService recording, fragment system

2. **MOPVisionStrategy** - **TO BE ELIMINATED**
   - Current location: Will be moved to backup folder
   - Action: Merge all functionality into VisionStrategy, eliminate separate strategy

3. **Fragment System**
   - Coverage guidance fragment implemented
   - Template structure with 19 fragments (requires consolidation)

4. **Template Architecture**
   - Current: Independent vision.xml (incorrect)
   - Required: vision.xml must inherit from system_base.xml

#### ❌ Consolidation Required:

1. **Complete MOP_VISION Elimination**: Remove all mop_vision files, merge functionality into vision with conditional logic
2. **Template Hierarchy Fix**: Correct vision.xml inheritance structure  
3. **Legacy Cleanup**: Move all obsolete files to backup folder

## Identified Problems

### Problem 1: Large Prompts Impact
- Current prompts estimated at ~2000-2500 tokens
- Inference latency affecting testing efficiency
- Potential reduction of 30-40% needed

### Problem 2: Coordinate Precision (Critical Discovery)
- LLMs have only **30% success rate** generating coordinates without explicit information
- Systematic bias toward upper-left center (X < 200, Y < 300)
- **0% success** on non-DOM elements (games, canvas rendered)
- **100% success** when explicit coordinates provided in prompt

**Solution**: Implement coordinate enhancement at multiple levels
- **Visitor Level**: Add `_with_position()`, `_with_bounds()` methods to abstract_visitor.py following existing patterns
  - **Critical**: Not just add methods, but ensure consistent usage across ALL visitors
  - **Current Status**: Basic coordinate extraction exists in abstract_visitor.py (lines extracting from `node.center_coordinates`)
- **Fragment Level**: Create `coordinate_precision.xml` fragment for visual elements outside ScreenDescription  
- **Format Standardization Research**: Current implementation shows mixed formats:
  - **ScreenshotActionComplementor**: Uses `visual_bounds[0][0], visual_bounds[0][1], visual_bounds[1][0], visual_bounds[1][1]`
  - **Coordinate format**: Position tuples `(x, y)` in abstract_visitor.py
  - **Need**: Establish consistent format across all coordinate usage
- **Proposed Format**: `"button 'OK' at position (540, 1306) - bounds[[200, 1270], [880, 1342]]"`
  - **Arrays**: `[]` for bounds arrays
  - **Objects**: `{}` for structured data  
  - **Coordinates**: `()` for position tuples
- **Implementation Priority**: Verify existing coordinate standardization before expanding

**RVSmart Advantage**: UIAutomator provides precise coordinates natively

### Problem 3: Template Structure Issues
- **Redundancies**: vision_system_consolidated duplicates system_intro + system_guidelines
- **Inconsistent hierarchy**: vision.xml doesn't inherit from system_base.xml
- **Fragment duplications**: Multiple guidelines fragments with overlapping content

## Development Philosophy

### Guiding Principles
- **Simplicity and elegance**: System as simple as possible without unnecessary complexity
- **Functionality preservation**: All current capabilities must be maintained
- **Complete legacy removal**: No adapters or compatibility layers
- **Backup old files**: Move obsolete code to backup folder
- **Conservative approach**: Prioritize natural and systematic exploration in prompt instructions

### Implementation Standards
- **Language**: English code and comments throughout
- **Documentation**: Detailed architectural comments at critical points following templates from EventBus, ExecutionManager, TaskExecutor classes
- **Comments**: Reflect current state only, no migration history, no promotional language
- **Error Handling**: Use rv-android-core ErrorHandler decorators and exceptions
- **Logging**: Integrate with LoggingManager infrastructure
- **Constants**: Use existing constants files across modules
- **Terminology**: "monitored operations" (not "security") for specification-agnostic context

## Detailed Refactoring Plan

### Phase 1: Consolidation of Previous Plan

#### 1.1 MOP_VISION Strategy Consolidation
**Objective**: Complete planned merge of mop_vision functionality into vision strategy

**Actions**:
- Merge `MOPVisionStrategy` functionality into `VisionStrategy`
- Add conditional `mop_focus` flag to vision.xml template
- Update `rvsmart_framework.py` to remove MOPVisionStrategy registration
- Move obsolete files to backup:
  - `modules/rvsmart-tool/src/rvsmart_tool/llm/prompt/strategies/mop_vision_strategy.py`
  - `modules/rvsmart-tool/src/rvsmart_tool/templates/templates/mop_vision.xml`
  - `modules/rvsmart-tool/src/rvsmart_tool/templates/fragments/mop_vision_instructions.xml`

**Implementation**:
```xml
<!-- vision.xml -->
<template name="vision" version="3.0" extends="system_base">
  <variables>
    <required>ui_elements</required>
    <optional>mop_focus</optional>
    <!-- other variables -->
  </variables>
  <roles>
    <system><![CDATA[
{% include "vision_system_consolidated" %}

{% if mop_focus %}
MONITORED OPERATIONS PRIORITY:
- [DM] elements have highest priority for violation detection
- [M] elements are secondary priority for coverage
- Follow natural UI flow while prioritizing monitored operations
{% endif %}

{% if additional_guidelines %}
ADDITIONAL GUIDANCE: {{ additional_guidelines }}
{% endif %}]]>
    </system>
  </roles>
</template>
```

#### 1.2 Template Hierarchy Correction
**Objective**: Fix vision.xml inheritance structure

**Current Issue**: vision.xml is independent, doesn't inherit from system_base.xml
**Solution**: Add `extends="system_base"` to vision.xml template
**Benefit**: Eliminates duplication and ensures consistent base structure

#### 1.3 Fragment Naming Standardization
**Objective**: Complete naming standardization established in previous implementation

**Analysis of Current Naming Issues**:
- Some fragments use `standard_*` naming instead of `single_*` 
- `single` refers to single-action generation strategy (one action per LLM inference)
- Naming must be consistent across all fragments for each strategy

**Actions**:
- Rename `standard_format.xml` → `single_format.xml`
- Rename `standard_guidelines.xml` → `single_guidelines.xml`  
- Verify all strategy fragments follow consistent naming patterns
- Document final naming convention for future development

### Phase 2: Fragment System Optimization

#### 2.1 Core Fragment Consolidation with UICoverageTracker Enhancement
**Target fragments for optimization**:

**CRITICAL: UICoverageTracker Strategic Enhancement**
- **Enhanced annotation system**: Beyond [UNTESTED]/[TESTED-Nx], implement contextual annotations:
  - `[NAVIGATION-TARGET]` for transition-critical elements  
  - `[MOP-PRIORITY]` for monitored operations focus
- **Note**: Form-specific annotations like `[FORM-INCOMPLETE]` are not feasible due to lack of UI pattern detection (UIPatternDetector deprecated)
- **Coverage heuristics**: Smart prioritization based on exploration efficiency patterns
- **UI vs System Coverage distinction**: UI tracker focuses on element-level interactions vs system-level method/activity coverage
- **Balance**: Strategic enhancement while preserving critical guidance data for LLM decisions

1. **vision_system_consolidated.xml** (98 lines → target 60-70 lines)
   - **Issues**: Duplicates content from system_intro and system_guidelines
   - **Solution**: Leverage system_base inheritance, compress examples
   - **Action**: Refactor to use inherited content, focus on vision-specific instructions

2. **context_status.xml** (49 lines → target 35-40 lines)
   - **Issues**: Complex RICH vs STATELESS mode logic, nested conditionals
   - **Critical Balance**: UI tracker metrics are ESSENTIAL for LLM guidance - cannot over-compress
   - **Solution**: Simplify structure while preserving UI visit data, action distribution statistics
   - **Approach**: Strategic balance between compression and data preservation
   - **Integration**: Coordinate with coverage_guidance to distribute UI tracker information effectively

3. **Guidelines consolidation**
   - **Issue**: `single_guidelines`, `batch_guidelines`, `vision_guidelines`, `system_guidelines` overlap
   - **Solution**: Create `core_guidelines.xml` with common content, strategy-specific extensions

#### 2.2 New Specialized Fragments

**coordinate_precision.xml** - For visual elements outside ScreenDescription:
```xml
<fragment name="coordinate_precision">
  <![CDATA[COORDINATE GUIDANCE:
  
  - ScreenDescription elements: Use provided action_id
  - Visual elements (games, canvas, dynamic): Use coordinate analysis
  - Format: {"action_id": "coord", "params": {"coordinates": [x,y]}}
  
  PRECISION: Use exact coordinates when provided vs visual estimation]]>
</fragment>
```

**strategic_guidance.xml** - Consolidated priority instructions:
```xml
<fragment name="strategic_guidance">
  <![CDATA[TESTING STRATEGY:
  
  1. SYSTEMATIC EXPLORATION: Cover untested elements systematically
  2. MONITORED OPERATIONS: Prioritize [DM] → [M] → Others when available
  3. NATURAL FLOW: Complete forms before submission, logical sequences
  4. ACTION VARIETY: Balance clicks, text input, coordinate actions
  
  Current focus: {{ coverage_guidance }}]]>
</fragment>
```

### Phase 3: Template Architecture Enhancement

#### 3.1 Multi-Provider Template Variants with Dynamic Pillar Inclusion

**Template-Visitor Alignment System**:
Templates must align with visitor capabilities and data output structure. Critical importance for maintaining data consistency and quality across different visitor implementations.

**Progressive Template Portfolio with Four-Pillar Integration**:
Templates are structured with dynamic pillar inclusion, allowing progressive complexity:

### Strategy vs Model Capability Matrix:

**IMPORTANT ARCHITECTURAL DISTINCTION**:
- **Strategies** (what to do): SINGLE (1 action), BATCH (1-5 actions), VISION (multimodal-specific)  
- **Model Capabilities** (how to do): Text-only vs Multimodal (screenshot analysis)
- **Context Modes**: STATELESS (inline context) vs RICH (sliding window with compression)

**Single Strategy Templates (Text + Multimodal Compatible):**
- `single_compact.xml` (~800 tokens) - **Pillar 1**: Basic ScreenDescription only
- `single_standard.xml` (~1200 tokens) - **Pillars 1+2**: + UI Coverage Tracker + optional multimodal support
- `single_premium.xml` (~1800 tokens) - **Pillars 1+2+3+4**: Full integration + optional multimodal support

**Batch Strategy Templates (Text + Multimodal Compatible):**
- `batch_compact.xml` (~1000 tokens) - **Pillar 1**: Multi-action planning with basic ScreenDescription
- `batch_standard.xml` (~1500 tokens) - **Pillars 1+2**: + UI tracker guidance + optional multimodal support
- `batch_premium.xml` (~2000 tokens) - **Pillars 1+2+3+4**: Complete sequences + optional multimodal support

**Vision Strategy Templates (Multimodal Only):**
- `vision_compact.xml` (~1200 tokens) - **Pillar 1**: ScreenDescription + mandatory coordinate precision
- `vision_standard.xml` (~1800 tokens) - **Pillars 1+2+3**: Multimodal with UI tracker and transitions
- `vision_premium.xml` (~2200 tokens) - **Pillars 1+2+3+4**: Complete integration with system coverage

**Multimodal Support Implementation**:
All Single and Batch templates support optional multimodal capabilities through:
- `screenshot_available` variable triggers coordinate precision fragments
- Visual analysis instructions when screenshot is present
- Coordinate action generation for elements not in UI dump
- Vision strategy remains dedicated to multimodal-specific scenarios

**Dynamic Pillar Selection Logic:**
```xml
<!-- Template structure supporting progressive pillar inclusion -->
<template name="single_standard" extends="system_base">
  <variables>
    <required>ui_elements</required> <!-- Pillar 1: ScreenDescription -->
    <conditional>ui_coverage_data</conditional> <!-- Pillar 2: UI Tracker -->
    <optional>transition_data</optional> <!-- Pillar 3: Transitions -->
    <optional>system_coverage</optional> <!-- Pillar 4: System Coverage -->
  </variables>
</template>
```

**Template Selection Architecture - IMPLEMENTED**:
New PromptConfig-based template selection system:
1. **Context override**: `context[ContextEntry.TEMPLATE]` (runtime flexibility - highest priority)
2. **PromptConfig template_name**: `config.template_name` from variant configuration (primary method)
3. **Dictionary config**: Backward compatibility for dict-based configs
4. **Strategy fallback**: Deprecated DEFAULT_TEMPLATE constants (warning issued)
5. **Final fallback**: Uses strategy name as template name

**Implementation Details**:
- **PromptConfig**: Added `template_name: str` field for progressive template selection
- **RvSmartToolConfig**: Updated to pass `template_name` from variant configs to PromptConfig
- **Tool Variants**: All variants now specify `template_name` (e.g., "vision_premium", "single_compact", "batch_standard")
- **Base Strategy**: Updated `get_template_name()` method to prioritize PromptConfig over deprecated defaults
- **Strategy Classes**: Removed hardcoded `DEFAULT_TEMPLATE` constants from single_strategy, batch_strategy, vision_strategy

#### 3.2 Coordinate Validation Implementation

**Critical for RVSmart**: UIAutomator provides precise coordinates natively

**Implementation Strategy**:
1. **Visitor Level Enhancement**: 
   - Add `_with_position()` and `_with_bounds()` methods to abstract_visitor.py
   - Follow existing pattern of `_with_description()` and similar methods
   - Implement across all visitors for consistency
2. **Fragment Integration**: Create coordinate_precision.xml for vision-specific guidance
3. **Format standardization**: `"element 'text' at position (x, y) - bounds[[x1,y1],[x2,y2]]"`
4. **Standardization Compliance**: Use `[]` for arrays, `{}` for objects, `()` for coordinates

**Expected Impact**: Coordinate precision improvement from 30% to 95-100%

**IMPORTANT CLARIFICATION ON COORDINATE PRECISION**:
The vision model's primary value is enabling interaction with dynamically rendered elements that are NOT present in UIAutomator dumps (games, canvas-rendered content, dynamic graphics). The coordinate precision implementation focuses on this specific use case - not replacing UIAutomator data, but complementing it for non-DOM elements that only vision models can detect and interact with.

### Phase 4: Advanced Prompt Engineering

#### 4.1 Chain-of-Thought Implementation
**Usage**: Complex decisions affecting coverage and monitored operations discovery
**Strategic Enhancement**: Explicit reasoning for complex scenarios involving form completion, MOP priorities, and systematic exploration decisions

**Format** (Simplified - No Form Detection Available):
```xml
<thinking>
State Analysis:
1. UI exploration status → 5 [UNTESTED] elements, 12 [TESTED-1x] elements
2. Available monitored operations → 2 [DM] elements, 3 [M] elements  
3. Transition opportunities → 3 unexplored actions may lead to new activities
4. Coverage decision → Prioritize untested elements with MOP annotations
</thinking>
```

**Chain-of-Thought Triggers**:
- Multiple viable actions with different strategic implications
- MOP prioritization vs systematic coverage decisions
- Navigation choices affecting coverage efficiency
- Complex UI states with transition opportunities

#### 4.2 Few-Shot Examples Optimization
**ExamplesFragment**: 2-3 concise examples focused on:
- **Multi-action capabilities**: Clear demonstration of selecting multiple actions per inference
- **Mixed action types**: Combination of action_id and coordinate-based actions
- **Systematic exploration**: Effective coverage and navigation patterns
- **Coordinate precision**: When and how to use coordinate actions
- **Natural flow completion**: Form completion before submission

**Structure**: `<state>` + `<action>` + `<rationale>` (eliminate verbose thinking)
**Emphasis**: Balanced exploration strategy rather than aggressive MOP prioritization

#### 4.3 Token Optimization Techniques
- **Semantic compression**: Remove redundant explanations
- **Imperative format**: Direct instructions vs explanatory text
- **Conditional inclusion**: Context-aware fragment selection
- **Structured XML**: Maintain clear organization while reducing verbosity

## Implementation Standards and Quality Requirements

**CRITICAL**: These standards must be applied throughout ALL phases from project start, not as a final step. Following these requirements is essential for successful implementation.

### Code Standards
- **Language**: English throughout codebase
- **Documentation**: Follow EventBus/ExecutionManager/TaskExecutor comment templates
- **Error Handling**: Use ErrorHandler decorators, proper exception hierarchy
- **Logging**: LoggingManager integration with structured context
- **Constants**: Utilize existing constants across rv-android-core, rv-llm, rv-experiment modules

### Architectural Integration with Template-Visitor Alignment
- **Component Reuse**: Maximum utilization of rv-android-core infrastructure
- **Clean Implementation**: No legacy compatibility layers
- **Universal Application**: Features work across all strategies
- **Task Isolation**: No state persistence between executions
- **Template-Visitor Alignment Optimization**: CRITICAL IMPORTANCE
  - **Data Quality Metrics**: Implement measurement and optimization of visitor output quality
  - **Context-Aware Visitor Selection**: Dynamic visitor method selection based on data requirements
  - **Consistency Validation**: Ensure template expectations align with visitor capabilities
  - **Performance Monitoring**: Track visitor execution time vs data quality trade-offs

### Terminology and Priority Standardization
- **"Monitored Operations"**: For specification-neutral context (not "security")  
- **ScreenDescription**: PRIMARY focus and foundation of all prompts (especially critical for non-vision models)
- **[M]/[DM] annotations**: Maintained for EXTREME IMPORTANCE - not compatibility but research objectives
  - Essential for increasing monitored operations error detection
  - Based on static analysis reachability data to MOP methods
  - Enables systematic coverage increase of monitored operation methods
- **Systematic Exploration Emphasis**: Primary strategy for achieving research objectives
- **Template variables**: Consistent naming across strategies
- **Fragment naming**: Clear, descriptive identifiers

## Expected Results

### Performance Metrics
- **Token reduction**: 30-40% decrease in average prompt size
- **Inference latency**: 25-35% reduction based on token optimization
- **Coordinate precision**: 30% → 95-100% for visual elements
- **Monitored operations discovery**: 15-25% improvement
- **Coverage increase**: 10-20% improvement in method/activity coverage

### Quality Improvements
- **Systematic testing**: Enhanced through UICoverageTracker annotations
- **Natural exploration**: Balanced prioritization vs forced MOP focus
- **Multi-provider support**: Optimized templates for different model capabilities
- **Maintainability**: Clean architecture with eliminated redundancies

## Risk Mitigation

### Technical Risks
1. **Compatibility break**: Mitigated by thorough testing and gradual rollout
2. **Data balance issues**: Risk of over-compressing critical UI tracker information
   - Mitigation: Careful balance in context_status.xml optimization
3. **Coordinate implementation complexity**: Multiple levels of implementation required
   - Mitigation: Phased approach starting with visitor methods then fragment integration

### Implementation Risks
1. **Legacy dependencies**: Mitigated by complete removal strategy
2. **Fragment integration**: Mitigated by existing framework compatibility
3. **Multi-provider testing**: Mitigated by comprehensive validation matrix

## Validation Strategy

### Testing Approach
- **A/B comparison**: Original vs optimized prompts
- **Multi-provider validation**: Ollama, HuggingFace, Frontier models
- **Performance benchmarks**: Latency, accuracy, coverage metrics
- **Integration testing**: Full workflow validation

### Success Criteria
- Token reduction achieved (30-40%)
- Coordinate precision improvement validated
- No functionality regression
- Enhanced monitored operations discovery
- Improved test coverage metrics

## Template Compatibility Matrix

### Strategy vs Model Compatibility:

| Strategy | Text Models | Multimodal Models | Context Modes | Notes |
|----------|------------|-------------------|---------------|--------|
| SINGLE   | ✅         | ✅                | STATELESS/RICH | Optional multimodal via screenshot_available |
| BATCH    | ✅         | ✅                | STATELESS/RICH | Optional multimodal via screenshot_available |
| VISION   | ❌         | ✅                | STATELESS/RICH | Mandatory multimodal, coordinate-focused |

### Context Mode Implementation:
- **STATELESS**: Uses `history_section.xml` and inline context in templates
- **RICH**: Uses `recent_iterations` with sliding window and compression
- **Both modes**: Supported by all template variants through conditional logic

### Template Selection Strategy - IMPLEMENTED:

**Configuration Flow**:
1. **CLI Command**: `rv-experiment run --tools rvandroid:qwen_7b_vision@temperature=0.3`
2. **Variant Resolution**: `RVSmartTool.get_variants()["qwen_7b_vision"]` provides base configuration
3. **PromptConfig Creation**: `RvSmartToolConfig.create_from_variant()` extracts `template_name` from variant
4. **Strategy Initialization**: Strategy receives PromptConfig with specific template_name
5. **Runtime Template Selection**: `base_strategy.get_template_name()` prioritizes PromptConfig over defaults

**New Variant Examples**:
```python
# Compact tokens for fast inference
"default": {
    "prompt_strategy": PromptStrategyType.SINGLE,
    "template_name": "single_compact",
    ...
}

# Premium features for thorough testing
"qwen_7b_vision": {
    "prompt_strategy": PromptStrategyType.VISION,
    "template_name": "vision_premium",
    ...
}

# Batch processing with multimodal support
"qwen_7b_batch_compact": {
    "prompt_strategy": PromptStrategyType.BATCH,
    "template_name": "batch_compact",
    "vision": True,  # enables screenshot_available variable
    ...
}
```

**Selection Criteria**:
1. **Strategy Selection** → determines action generation approach (single/batch/vision)
2. **Template Tier Selection** → determines token budget and feature richness (compact/standard/premium)  
3. **Model Capability** → enables multimodal features via `vision: True` in variant config
4. **Context Mode** → controls memory usage via `context_mode` (STATELESS/RICH)

---

## 📋 **Final Variant Configuration Summary**

### **Model Capabilities Reference**
| Model | Type | Vision | Think | Size | Notes |
|-------|------|--------|-------|------|-------|
| Llama 3.2 1B | Text-only | ❌ | ❌ | 1B | Lightweight baseline |
| DeepSeek R1 1.5B | Text+Think | ❌ | ✅ | 1.5B | Reasoning specialist |
| **Gemma 3 4B** | **Multimodal** | **✅** | ❌ | **4B** | **Vision + good performance** |
| Qwen 3 0.6B | Text+Think | ❌ | ✅ | 0.6B | Compact reasoning |
| Qwen 2.5VL 3B | Vision Specialist | ✅ | ❌ | 3B | Vision-optimized |
| Qwen 2.5VL 7B | Vision Specialist | ✅ | ❌ | 7B | Premium vision |
| Phi4 Mini 3.8B | Text+Think | ❌ | ✅ | 3.8B | Advanced reasoning |

### **Implemented Variants**
| Variant | Strategy | Template | Model | Vision | Think | Context | Purpose |
|---------|----------|----------|--------|--------|-------|---------|---------|
| `default` | SINGLE | single_compact | Gemma 3 4B | ✅ | ❌ | STATELESS | **Balanced multimodal baseline** |
| `gemma_3_baseline` | SINGLE | single_compact | Gemma 3 4B | ✅ | ❌ | STATELESS | Explicit comparison baseline |
| `qwen_3b_vision` | VISION | vision_standard | Qwen 2.5VL 3B | ✅ | ❌ | STATELESS | Compact vision specialist |
| `qwen_7b_vision` | VISION | vision_premium | Qwen 2.5VL 7B | ✅ | ❌ | STATELESS | Premium vision specialist |
| `qwen_7b_vision_rich` | VISION | vision_premium | Qwen 2.5VL 7B | ✅ | ❌ | RICH | Context-aware premium |
| `qwen_7b_batch_compact` | BATCH | batch_compact | Qwen 2.5VL 7B | ✅ | ❌ | STATELESS | Efficient batch processing |
| `gemma_batch_standard` | BATCH | batch_standard | Gemma 3 4B | ✅ | ❌ | STATELESS | Balanced batch processing |
| `deepseek_r1_single` | SINGLE | single_standard | DeepSeek R1 1.5B | ❌ | ✅ | STATELESS | **Reasoning-focused testing** |
| `qwen3_think_batch` | BATCH | batch_compact | Qwen 3 0.6B | ❌ | ✅ | STATELESS | **Compact reasoning + batch** |
| `phi4_reasoning` | SINGLE | single_premium | Phi4 Mini 3.8B | ❌ | ✅ | RICH | **Advanced reasoning + context** |

### **Usage Examples**
```bash
# Balanced multimodal baseline  
rv-experiment run --tools rvsmart:default

# Premium vision specialist
rv-experiment run --tools rvsmart:qwen_7b_vision

# Reasoning-focused testing
rv-experiment run --tools rvsmart:deepseek_r1_single

# Compact reasoning with batch processing
rv-experiment run --tools rvsmart:qwen3_think_batch@temperature=0.1

# Advanced reasoning with rich context
rv-experiment run --tools rvsmart:phi4_reasoning
```

---

## Implementation Notes

## Complete Fragment Mapping and Cleanup Strategy

### Current Fragment Inventory (19 total)

#### ✅ **Keep and Optimize (11 fragments)**:
1. `system_intro.xml` - Core system introduction 
2. `system_guidelines.xml` - Universal guidelines
3. `context_status.xml` - UI tracker and system state (CRITICAL - balanced optimization)
4. `ui_patterns_guide.xml` - UI interaction patterns
5. `single_format.xml`, `single_guidelines.xml`, `single_instructions.xml` - Single strategy
6. `batch_format.xml`, `batch_guidelines.xml`, `batch_instructions.xml`, `batch_critical_task.xml` - Batch strategy
7. `vision_format.xml`, `vision_guidelines.xml`, `vision_instructions.xml` - Vision strategy

#### 🔄 **Consolidate and Refactor (4 fragments)**:
1. `vision_system_consolidated.xml` - Break into reusable components using inheritance
2. `history_section.xml` - Merge functionality into context_status.xml
3. User_base.xml - Review usage and consolidate if underutilized
4. Vision_system_intro.xml - Replace with inherited system_intro.xml

#### ❌ **Eliminate and Move to Backup (4 fragments)**:
1. `mop_vision_instructions.xml` - Functionality merged into vision strategy
2. Any remaining `standard_*` named fragments - Rename to `single_*`
3. Duplicate system fragments identified during consolidation
4. Obsolete fragments with <20 lines that duplicate existing functionality

### Implementation Approach

This plan consolidates learnings from the previous implementation (24/08/2024) with the four-pillar data hierarchy. The approach prioritizes:

1. **Four-Pillar Data Architecture**: ScreenDescription → UI Tracker → Transitions → System Coverage
2. **Complete MOP_VISION elimination** with functionality preservation in vision strategy  
3. **Template-Visitor alignment** ensuring data structure compatibility
4. **Coordinate validation implementation** at visitor and fragment levels
5. **Strategic UI tracker preservation** preventing over-compression of critical guidance data
6. **Standards compliance** with English comments, error handling, and constants usage

The implementation follows rv-android-core architectural patterns and maintains compatibility with existing tool infrastructure while eliminating all legacy code and redundancies.