# RVSmart Prompt Refactoring Plan

## Context and Motivation

RVSmart is a testing tool developed as an adaptation of RVAndroid, replacing DroidBot with UIAutomator for Android application testing. The primary objective is to discover monitored operations violations and increase test coverage. Currently, prompts are too large, impacting inference speed and potentially reducing effectiveness in finding errors.

### Hardware Constraints
- **Available GPU**: 16GB VRAM
- **Implications**: 
  - Limit maximum prompt size for large models :: nao vamos controlar isso ... o usuario que eh responsavel por configurar o experimento, se ele acha que o modelo cabe na memoria é decisao dele
  - Consider 4-bit quantization for models above 7B parameters
  - Optimize for efficient models (7B-13B) that fit comfortably in memory

## Current System Analysis

### RVSmart Architecture
- **Modular architecture** based on fragments
- **Structured XML templates** with system/user roles
- **Specialized strategies**: single, batch, vision (mop_vision will be merged)
- **Framework based on rv-llm** focused on monitored operations discovery and coverage increase

### Implementation Status from Previous Plan (24/08/2024)

#### ✅ Already Implemented in RVSmart:

1. **UICoverageTracker System** :: ressaltar a importancia pois contem diversas metricas sobre os elementos de UI visitados (nao confundir com a cobertura do sistema (atividades/classes/metodos/etc))
   - Location: `modules/rvsmart-tool/src/rvsmart_tool/core/memory/ui_coverage_tracker.py`
   - Features: [UNTESTED]/[TESTED-Nx] annotations, coverage statistics
   - Integration: ActionService recording, fragment system

2. **MOPVisionStrategy** (to be consolidated) :: NAO!!! ja falei mil vezes ... isso eh lixo ... deve ser consolidado eh o merge das funcionalidades disso dentro de vision
   - Location: `modules/rvsmart-tool/src/rvsmart_tool/llm/prompt/strategies/mop_vision_strategy.py`
   - Features: Screen context analysis, action sequence suggestions
   - **Action Required**: Merge functionality into VisionStrategy, move to backup

3. **Fragment System**
   - Coverage guidance fragment implemented
   - Template structure established with 19 fragments identified

4. **Template Architecture**
   - Current hierarchy: `vision.xml` + `mop_vision.xml` (extends vision) :: mop_vision eh lixo
   - **Issue**: vision.xml does not inherit from system_base.xml
   - **Action Required**: Fix template inheritance structure

#### ❌ Consolidation Required:

1. **MOP_VISION Merge**: Complete consolidation of mop_vision → vision with conditional flags :: esta muito confuso o texto ... la em cima fala que vai ter mop_vision (e ja falei que eh lixo, nao vamos ter) e aqui desmente o que voce disse la em cima ... muito confuso ... revise toda a estrutura do plano
2. **Template Hierarchy**: Correct vision.xml to extend system_base.xml
3. **Legacy Cleanup**: Move obsolete files (MOPVisionStrategy, mop_vision templates) to backup

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

**Solution**: Provide explicit coordinates in format: `"button 'OK' at position (540, 1306)"` :: ok, vamos fazer aonde? no visitor ou no fragment (.py)? lembre que [M] e [DM] sao incluidos no visitor ... e estamos discutindoa padronizacao de [], {}, () entao deve usar nos exemplos, o plano deve ser consistente ... aproveite para olhar outros casos tambem 
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
- **Conservative approach**: Prioritize natural and systematic exploration :: nas instrucoes dos prompts

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
**Objective**: Complete standardization from previous plan :: explique o que é ... pois quem le pode nao ter acesso ao outro plano ... esse plano deve ser completo e auto-contido ... todas as informacoes necessarias para sua implementacao ja devem estar presentes ... e se alguma etapa for de analise a analise deve ser feita previamente e o resultado escrito no plano ... nao vamos deixar nada para depois ... o plano deve estar pronto para execucao

**Actions**:
- Ensure `single_format.xml` (not `standard_format.xml`)
- Ensure `single_guidelines.xml` (not `standard_guidelines.xml`)
- Verify consistent naming across all strategy fragments

### Phase 2: Fragment System Optimization

#### 2.1 Core Fragment Consolidation
**Target fragments for optimization**:

1. **vision_system_consolidated.xml** (98 lines → target 60-70 lines)
   - **Issues**: Duplicates content from system_intro and system_guidelines
   - **Solution**: Leverage system_base inheritance, compress examples
   - **Action**: Refactor to use inherited content, focus on vision-specific instructions

2. **context_status.xml** (49 lines → target 25-30 lines)
   - **Issues**: Complex RICH vs STATELESS mode logic, nested conditionals
   - **Solution**: Simplify conditional structure, narrative summaries vs raw listings :: ok, mas lembre da importancia do ui tracker, as metricas de visitas a elementos da tela podem guiar a llm (incluindo a distribuicao de acoes por tipo) ... entao eh importante e talvez compactar demais possa nao ter o beneficio esperado ... ou vamos tratar essas informacoes de outra forma? acho que vi algo relacioando a guidance ...

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

#### 3.1 Multi-Provider Template Variants

**Template Portfolio**: :: esse template porfolio deve ter relacao direta com os visitors ... devemos repensar, entao analise profundamente para propor uma nova solucao
- `single_compact.xml` (~800 tokens) - Fast inference, minimal context
- `single_standard.xml` (~1200 tokens) - Balanced reasoning, moderate context
- `single_premium.xml` (~1800 tokens) - Deep reasoning, rich context

- `batch_compact.xml` (~1000 tokens) - Quick planning sequences
- `batch_standard.xml` (~1500 tokens) - Comprehensive multi-action planning
- `batch_premium.xml` (~2000 tokens) - Complex scenario handling

- `vision_compact.xml` (~1200 tokens) - Essential multimodal analysis
- `vision_standard.xml` (~1800 tokens) - Full coordinate validation
- `vision_premium.xml` (~2200 tokens) - Advanced visual reasoning

**Template Selection Architecture**:
Leverage existing `get_template_name()` system in base_strategy.py:
1. **Context override**: `context[ContextEntry.TEMPLATE]` (runtime)
2. **Config override**: `strategy.config["template_name"]` (user configuration)
3. **Strategy default**: `DEFAULT_TEMPLATE` constants

#### 3.2 Coordinate Validation Implementation

**Critical for RVSmart**: UIAutomator provides precise coordinates natively

**Implementation Strategy**:
1. **ScreenDescription enhancement**: Include coordinate information in element descriptions
2. **Template instructions**: Explicit coordinate usage guidance
3. **Format standardization**: `"element 'text' at position (x, y) - bounds[[x1,y1],[x2,y2]]"`

**Expected Impact**: Coordinate precision improvement from 30% to 95-100%

### Phase 4: Advanced Prompt Engineering

#### 4.1 Chain-of-Thought Implementation
**Usage**: Complex decisions affecting coverage and monitored operations discovery
**Format**:
```xml
<thinking>
Current state analysis:
1. Form completion status → 80% complete
2. Available monitored operations → 2 [DM], 3 [M] elements
3. Logical next action → Complete remaining field, then submit [DM]
</thinking>
```

#### 4.2 Few-Shot Examples Optimization
**ExamplesFragment**: 2-3 concise examples focused on:
- Systematic exploration effectiveness
- Coordinate precision usage
- Form completion before submit
- Monitored operations prioritization

**Structure**: `<state>` + `<action>` + `<rationale>` (eliminate verbose thinking)

#### 4.3 Token Optimization Techniques
- **Semantic compression**: Remove redundant explanations
- **Imperative format**: Direct instructions vs explanatory text
- **Conditional inclusion**: Context-aware fragment selection
- **Structured XML**: Maintain clear organization while reducing verbosity

### Phase 5: Implementation Standards and Quality

#### 5.1 Code Standards
- **Language**: English throughout codebase
- **Documentation**: Follow EventBus/ExecutionManager/TaskExecutor comment templates
- **Error Handling**: Use ErrorHandler decorators, proper exception hierarchy
- **Logging**: LoggingManager integration with structured context
- **Constants**: Utilize existing constants across rv-android-core, rv-llm, rv-experiment modules

#### 5.2 Architectural Integration
- **Component Reuse**: Maximum utilization of rv-android-core infrastructure
- **Clean Implementation**: No legacy compatibility layers
- **Universal Application**: Features work across all strategies
- **Task Isolation**: No state persistence between executions

#### 5.3 Terminology Standardization
- **"Monitored Operations"**: For specification-neutral context (not "security")
- **[M]/[DM] annotations**: Maintained for backward compatibility
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
2. **Performance regression**: Mitigated by benchmarking and A/B testing
3. **Template selection complexity**: Mitigated by user configuration approach

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

---

## Implementation Notes

This plan consolidates learnings from the previous implementation (24/08/2024) with new optimization strategies. The approach prioritizes:

1. **Completion of planned consolidation** (MOP_VISION merge)
2. **Correction of architectural issues** (template hierarchy)
3. **Advanced optimization techniques** (coordinate validation, token reduction)
4. **Standards compliance** (English comments, error handling, constants usage)

The implementation follows rv-android-core architectural patterns and maintains compatibility with existing tool infrastructure while eliminating legacy code and redundancies.