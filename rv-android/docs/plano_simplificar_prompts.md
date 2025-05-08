# RV-Android Prompt System Refactoring Documentation

## Table of Contents
1. [Introduction](#introduction)
2. [Objectives and Principles](#objectives-and-principles)
3. [Fragment Refactoring](#fragment-refactoring)
4. [Template Structure](#template-structure)
5. [Marking Monitored Operations](#marking-monitored-operations)
6. [Implementation Considerations](#implementation-considerations)
7. [Appendix A: Rendered Prompt Examples](#appendix-a-rendered-prompt-examples)
8. [Appendix B: Key System Components](#appendix-b-key-system-components)

## Introduction

This document details the refactoring of the RV-Android prompt system for Large Language Model (LLM) integration in Android application testing. The prompt system is a critical component that bridges the gap between application state information and LLM-based decision making for test action generation.

The refactoring aims to create more efficient prompts while maintaining effectiveness, with a focus on prioritizing logical interaction sequences while still highlighting operations that are instrumented for runtime verification.

## Objectives and Principles

### Objectives
- Reduce prompt size to improve inference performance
- Maintain clarity and specificity of instructions
- Prioritize logical interaction sequences
- Integrate information about monitored operations in a non-intrusive way
- Remove UI pattern detection to simplify processing

### Guiding Principles
1. **Simplicity over verbosity** - Clear, concise language
2. **Logical sequence as priority** - Emphasize natural interaction order
3. **Essential information first** - Prioritize most relevant content
4. **Consistent formatting** - Facilitate LLM processing
5. **Modularity** - Maintain flexibility through component structure

## Fragment Refactoring

### System Introduction Fragment

**Before:**
You are an Android UI testing expert. Your task is to analyze the current app state and suggest effective testing actions to maximize coverage and find potential issues.

Focus on:

Maximizing code coverage by targeting untested UI elements
Prioritizing testing of methods of interest that directly or indirectly affect monitored operations
Systematically exploring all application states in a logical sequence
Testing complex UI interactions and edge cases

**After:**
You are an Android testing specialist. Your task is to select effective testing actions in a logical sequence.

KEY OBJECTIVES:

TEST SYSTEMATICALLY - Follow natural interaction order for the current UI
MAXIMIZE COVERAGE - Test all interactive elements when appropriate
PRIORITIZE KEY METHODS - Give special attention to operations marked with [M] or [DM]
EXPLORE THOROUGHLY - Test edge cases and complex interactions

**Justification:**
- Reduced word count by approximately 22%
- Emphasized logical sequence as the first priority
- Introduced [M] and [DM] markers for monitored operations
- More direct language ("select" vs "suggest")

### System Guidelines Fragment

**Before:**
GUIDELINES FOR ACTION SELECTION:

ORDERING MATTERS - arrange actions in a logical testing sequence (e.g., fill a form before submitting it)
If an action leads to a screen transition, it should typically be the last action in your sequence
For text inputs, generate contextually appropriate values based on the field type (email, password, etc.)
Prioritize actions that trigger operations of interest (marked as [CRITICAL] or [IMPORTANT])
Ensure your suggested actions form a coherent testing strategy
For login forms: first fill username, then password, THEN click login button
For registration forms: fill ALL fields in a logical order before submission
If a screen has a primary action (OK, NEXT, CONTINUE), it should be the LAST action
For dropdowns/spinners: click to open them first, then select an option
For checkboxes in a form: handle them BEFORE clicking submit buttons

**After:**
TESTING GUIDELINES:

FOLLOW LOGICAL ORDER - Complete form fields before submitting, open dropdowns before selecting
PRIORITIZE NEW AREAS - Explore untested functionality before revisiting familiar screens
USE APPROPRIATE VALUES - Match input values to field types (email, password, etc.)
TARGET MARKED OPERATIONS - When appropriate, select actions marked with [M] or [DM]
CONSIDER SEQUENCES - For multi-step interactions (forms, dialogs, menus), follow a complete sequence

**Justification:**
- Reduced from 10 to 5 guidelines
- Eliminated redundancies (items 6-10 were variations of logical order)
- Simplified and grouped related concepts
- Introduced consistent marking for monitored operations

### Standard Instructions Fragment

**Before:**
IMPORTANT: You will be provided with a list of possible actions, each with a unique action_id. Your job is to select exactly ONE action to perform. Choose the most effective action for thorough testing.


**After:**
Select EXACTLY ONE action from the available options. Choose the action that most effectively advances testing coverage while following a logical interaction sequence.


**Justification:**
- Simplified instruction
- Clarified selection criteria (coverage + logical sequence)
- Reduced word count while maintaining essential information

### Standard Format Fragment

**Before:**
Format your response as a valid JSON object with an actions array containing one action following this schema:
{
"actions": [
{
"action_id": "5",
"params": {},
"explanation": "Detailed explanation of why this action was chosen"
}
]
}

For actions that require parameters (like SET_TEXT), you must include appropriate values:
{
"actions": [
{
"action_id": "5",
"params": {"text": "test@example.com"},
"explanation": "Entering a valid email address in the email field"
}
]
}

IMPORTANT: You must select EXACTLY ONE action, so your actions array should contain exactly one element.

DO NOT include any additional text outside of the JSON object. Your response must be valid JSON that can be parsed directly.


**After:**
RESPONSE FORMAT (JSON only):
{
"actions": [
{
"action_id": "6",
"params": {},
"explanation": "Clicking the submit button to test form submission"
}
]
}

For actions that require parameters (like SET_TEXT):
{
"actions": [
{
"action_id": "5",
"params": {"text": "test@example.com"},
"explanation": "Entering a valid email address in the email field"
}
]
}

You must select EXACTLY ONE action. Your response must be valid, parseable JSON with no additional text.


**Justification:**
- Maintained both examples (with and without parameters)
- Simplified instructions
- Reduced word count while preserving essential format information

### Batch Instructions Fragment

**Before:**
Your task is to analyze the current app state and suggest a BATCH OF RELATED ACTIONS to efficiently test the current UI flow.

IMPORTANT: You should identify a specific UI pattern and generate a batch of related actions to efficiently interact with it.

For a FORM pattern, include actions to:

Enter text in all text fields
Select options in dropdowns/spinners
Toggle checkboxes/switches appropriately
Click the submit/save button
For a LIST pattern, include actions to:

Scroll through the list
Select specific items
Perform operations on list items
Navigate between list sections
For a TAB pattern, include actions to:

Navigate through each tab
Interact with content on each tab
Test tab switching behavior
For a DIALOG pattern, include actions to:

Interact with dialog elements
Test both positive and negative dialog paths
Ensure proper dialog dismissal

**After:**
Analyze the current UI and create a BATCH OF RELATED ACTIONS that form a logical testing sequence.

Create a sequence of actions that:

Follow natural interaction order
Test all relevant elements
Complete a coherent testing flow
Prioritize marked operations [M] or [DM] when appropriate
Ensure all actions in your batch are currently available on the screen.


**Justification:**
- Simplified instructions
- Removed pattern detection references
- Focused on general principles of logical sequencing
- Introduced consistent marking for monitored operations
- Reduced word count by approximately 60%

### History Section Fragment

**Before:**
{% if action_history %}
HISTORY:
{{ action_history }}
{% endif %}

{% if memory_insights %}
{{ memory_insights }}
{% endif %}

{% if transition_guidance %}
NAVIGATION GUIDANCE:
{% if transition_guidance is mapping %}
{% if transition_guidance.visit_count is defined %}

This screen has been visited {{ transition_guidance.visit_count }} time(s) {% endif %} {% if transition_guidance.unexplored_elements is defined and transition_guidance.unexplored_elements > 0 %}
There are {{ transition_guidance.unexplored_elements }} UI elements on this screen that have not yet been tested {% endif %} {% if transition_guidance.suggested_targets is defined and transition_guidance.suggested_targets %}
Suggested exploration targets: {% for target in transition_guidance.suggested_targets %}
{{ target.name }} ({{ target.visits }} visits) {% endfor %} {% endif %} {% else %} {{ transition_guidance }} {% endif %} {% endif %}

**After:**
{% if action_history %}
RECENT ACTIONS:
{% for iteration in action_history %}

{{ iteration }} {% endfor %} {% endif %}
{% if transition_guidance %}
TRANSITIONS:
{% for action, target in transition_guidance.transitions %}

{{ action }} -> {{ target }} {% endfor %} {% endif %}

**Justification:**
- Simplified format with one line per iteration
- Clear mapping between actions and resulting activities
- Consistent formatting for easier LLM processing
- Conditional inclusion preserved
- Reduced template complexity

### User Base Fragment

**Before:**
Current Activity: {{ activity | default("Unknown") }}

{% if static_context is defined %}
{{ static_context }}
{% endif %}

Current UI Elements and Available Actions:
{% if ui_elements is defined %}
{{ ui_elements }}
{% else %}
No UI elements information available.
{% endif %}

{% if action_history %}
{% include "history_section" %}
{% endif %}


**After:**
SCREEN: {{ activity | default("Unknown") }}

{% if ui_elements is defined %}
{{ ui_elements }}
{% else %}
No UI elements available.
{% endif %}

{% if action_history %}{% include "history_section" %}{% endif %}


**Justification:**
- Simplified header labeling
- Reduced descriptive text
- Maintained conditional inclusion logic
- Overall reduction in template size

## Template Structure

The refactored template structure maintains the modular approach but simplifies interaction:

### Standard Template Structure
SYSTEM INSTRUCTION (system_intro + system_guidelines)
UI ELEMENTS (screen details with monitored operation markers)
HISTORY & TRANSITIONS (compact representation of past actions and transitions)
TASK INSTRUCTION (standard_instructions)
RESPONSE FORMAT (standard_format)

### Batch Template Structure
SYSTEM INSTRUCTION (system_intro + system_guidelines)
UI ELEMENTS (screen details with monitored operation markers)
HISTORY & TRANSITIONS (compact representation of past actions and transitions)
TASK INSTRUCTION (batch_instructions)
RESPONSE FORMAT (batch_format)

## Marking Monitored Operations

### Marker Format
- **[M]** - For methods that indirectly reach a monitored operation (reaches_mop)
- **[DM]** - For methods that directly call a monitored operation (directly_reaches_mop)

### Integration in UI Elements
These markers appear directly in the UI element descriptions:
Button with text 'GENERATE HASH'. Actions: CLICK (6) [M]
EditText with hint 'Enter text'. Actions: SET_TEXT (3)
Button with text 'VALIDATE'. Actions: CLICK (8) [DM]


### Justification
- Short markers save space in the prompt
- Mnemonic for easier understanding ([M] = Monitored, [DM] = Directly Monitored)
- Visually distinct without being intrusive
- Preserves focus on logical sequence while indicating priority

## Implementation Considerations

### UI Element Fragment Modification
The UIElementsFragment class should be modified to include the markers:
if action.directly_reaches_mop:
action_text += " [DM]"
elif action.reaches_mop:
action_text += " [M]"


### Pattern Detection Removal
The following files should be removed or ignored:
- `batch_ui_pattern_detection.xml`
- `batch_critical_task.xml`
- References to `detected_pattern` in templates

### History Formatting
The MemoryManager should format history entries to match the new compact format:
Action history lines should follow the format:

SET_TEXT(3)="test", CLICK(7)
CLICK(2), SET_TEXT(4)="password", CLICK(8)

## Appendix A: Rendered Prompt Examples

### Example 1: Standard Single Action Prompt
You are an Android testing specialist. Your task is to select effective testing actions in a logical sequence.

KEY OBJECTIVES:

TEST SYSTEMATICALLY - Follow natural interaction order for the current UI
MAXIMIZE COVERAGE - Test all interactive elements when appropriate
PRIORITIZE KEY METHODS - Give special attention to operations marked with [M] or [DM]
EXPLORE THOROUGHLY - Test edge cases and complex interactions
TESTING GUIDELINES:

FOLLOW LOGICAL ORDER - Complete form fields before submitting, open dropdowns before selecting
PRIORITIZE NEW AREAS - Explore untested functionality before revisiting familiar screens
USE APPROPRIATE VALUES - Match input values to field types (email, password, etc.)
TARGET MARKED OPERATIONS - When appropriate, select actions marked with [M] or [DM]
CONSIDER SEQUENCES - For multi-step interactions (forms, dialogs, menus), follow a complete sequence
SCREEN: br.unb.cic.cryptoapp.messagedigest.MessageDigestActivity

The current screen has the following UI views and corresponding actions:

Text view with text 'Crypto App'.
Text view with text 'Message Digest'.
Dropdown spinner with no text. Actions: CLICK (1), SCROLL UP (2), SCROLL DOWN (3)
Editable text field with text 'Input text ...'. Actions: CLICK (4), SET_TEXT (5)
Button with text 'GENERATE HASH'. Actions: CLICK (6) [M]
System back button. Actions: BACK (7)
RECENT ACTIONS:

SET_TEXT(5)="test123", CLICK(1)
CLICK(3), CLICK(6)
TRANSITIONS:

CLICK(6) -> br.unb.cic.cryptoapp.messagedigest.ResultActivity
Select EXACTLY ONE action from the available options. Choose the action that most effectively advances testing coverage while following a logical interaction sequence.

RESPONSE FORMAT (JSON only):
{
"actions": [
{
"action_id": "6",
"params": {},
"explanation": "Clicking the submit button to test form submission"
}
]
}

For actions that require parameters (like SET_TEXT):
{
"actions": [
{
"action_id": "5",
"params": {"text": "test@example.com"},
"explanation": "Entering a valid email address in the email field"
}
]
}

You must select EXACTLY ONE action. Your response must be valid, parseable JSON with no additional text.


### Example 2: Batch Actions Prompt
You are an Android testing specialist. Your task is to select effective testing actions in a logical sequence.

KEY OBJECTIVES:

TEST SYSTEMATICALLY - Follow natural interaction order for the current UI
MAXIMIZE COVERAGE - Test all interactive elements when appropriate
PRIORITIZE KEY METHODS - Give special attention to operations marked with [M] or [DM]
EXPLORE THOROUGHLY - Test edge cases and complex interactions
TESTING GUIDELINES:

FOLLOW LOGICAL ORDER - Complete form fields before submitting, open dropdowns before selecting
PRIORITIZE NEW AREAS - Explore untested functionality before revisiting familiar screens
USE APPROPRIATE VALUES - Match input values to field types (email, password, etc.)
TARGET MARKED OPERATIONS - When appropriate, select actions marked with [M] or [DM]
CONSIDER SEQUENCES - For multi-step interactions (forms, dialogs, menus), follow a complete sequence
SCREEN: com.example.testapp.LoginActivity

The current screen has the following UI views and corresponding actions:

Text view with text 'Login'.
Editable text field with hint 'Username'. Actions: CLICK (1), SET_TEXT (2)
Editable text field with hint 'Password'. Actions: CLICK (3), SET_TEXT (4)
Checkbox with text 'Remember me'. Actions: CLICK (5)
Button with text 'Login'. Actions: CLICK (6) [M]
Text view with text 'Forgot password?'. Actions: CLICK (7)
System back button. Actions: BACK (8)
RECENT ACTIONS:
This is your first interaction with this screen.

Analyze the current UI and create a BATCH OF RELATED ACTIONS that form a logical testing sequence.

Create a sequence of actions that:

Follow natural interaction order
Test all relevant elements
Complete a coherent testing flow
Prioritize marked operations [M] or [DM] when appropriate
Ensure all actions in your batch are currently available on the screen.

RESPONSE FORMAT (JSON only):
{
"actions": [
{
"action_id": "2",

"params": {"text": "testuser"},

"explanation": "Entering a username in the username field"
},
{
"action_id": "4",
"params": {"text": "password123"},
"explanation": "Entering a password in the password field"
},
{
"action_id": "5",
"params": {},
"explanation": "Checking the 'Remember me' checkbox"
},
{
"action_id": "6",
"params": {},
"explanation": "Clicking the Login button to submit the form"
}
],
"batch_explanation": "This batch completes the login form in a logical order: filling the username, then password, checking the remember option, and finally submitting the form"
}

Your response must be valid, parseable JSON with no additional text.


## Appendix B: Key System Components

### Framework Components

1. **PromptFramework**
   - Central orchestration component
   - Manages information gathering and template rendering
   - Coordinates between information fragments, template repository, and strategies

2. **InformationManager**
   - Manages information fragments
   - Composes information from various sources
   - Coordinates fragment priorities and inclusion

3. **TemplateRepository**
   - Manages template loading and rendering
   - Supports template inheritance and versioning
   - Renders templates with variable substitution

4. **ComponentConfigurator**
   - Central configuration point
   - Manages strategy selection and registration
   - Configures LLM parameters and system behavior

### Information Fragments

1. **UIElementsFragment**
   - Converts screen description to text representation
   - Adds monitored operation markers
   - Prioritizes interactive elements

2. **HistoryFragment**
   - Formats action history in compact representation
   - Limits history to recent relevant actions
   - Provides context for decision making

3. **TransitionGuidanceFragment**
   - Maps actions to resulting activities
   - Provides navigation context
   - Highlights unexplored paths

4. **MonitoredOperationsFragment**
   - Provides information about monitored methods
   - Integrated into UI elements representation
   - Helps focus testing on instrumented code paths

### Templates and Strategies

1. **Templates**
   - XML-based with Jinja2 templating
   - Support inheritance and fragment inclusion
   - Modular design with conditional sections

2. **Strategies**
   - StandardStrategy: Generates single action
   - BatchActionStrategy: Generates multiple related actions
   - Coordinate information gathering and template selection

### Domain Components

1. **ScreenDescription**
   - Represents the current UI state
   - Contains UI elements and available actions
   - Provides structured access to screen information

2. **ItemAction**
   - Represents available actions on UI elements
   - Contains action properties (ID, type, parameters)
   - Tracks relation to monitored operations

3. **ScreenItem**
   - Represents a UI element on the screen
   - Contains view data and available actions
   - Provides description of the element

4. **StaticAnalysisData**
   - Contains information from static analysis
   - Maps activities to classes and methods
   - Provides monitored operation information
   


markdown# Appendix C: Prompt Optimization Techniques for Models with Reasoning Capabilities

## Introduction: Reasoning Capabilities in LLMs

When we say a model has strong "reasoning" capabilities, it means it can:
1. **Follow complex logical chains** - Connect facts and premises to reach valid conclusions
2. **Decompose problems** - Break complex tasks into smaller, manageable steps
3. **Apply contextual knowledge** - Use information from the prompt to guide specific decisions
4. **Maintain consistency** - Keep logical coherence throughout multiple reasoning steps
5. **Generalize from examples** - Apply learned principles to new, similar situations

In the context of Android testing, reasoning is particularly important because the model needs to:
* Analyze UI structure to identify patterns
* Decide which elements to test based on strategic priorities
* Connect UI elements with potential monitored operations
* Plan logically valid sequences of actions

## Fundamental Techniques for Optimizing Prompts with Reasoning Models

### 1. Explicit Relationship Encoding

#### 1.1 Consistent Identification Schema
- Use a consistent ID system throughout the prompt
- Maintain cross-references using these IDs
- Create a common "language" for relating different prompt sections

**Example:**
Button "Login" [id=btn_login][M] → Actions: CLICK(1)
EditText "Username" [id=edit_user] → Actions: SET_TEXT(2)
HISTORY: SET_TEXT(2) → CLICK(1) → LoginActivity

#### 1.2 Relational Notation
- Use symbols and formats that indicate relationships (arrows, colons, parentheses)
- Create visual hierarchies or indentation to show relationships
- Establish visual conventions the model can "learn" during the prompt

**Example:**
FORM: Login

username: EditText [id: username] → CLICK(1), SET_TEXT(2)
password: EditText [id: password] → CLICK(3), SET_TEXT(4)
submit: Button [id: login_button][M] → CLICK(5)


#### 1.3 Multi-dimensional Contextualization
- Connect elements in different dimensions (spatial, temporal, functional)
- Create cross-references between different prompt sections
- Allow the model to build a "mental graph" of relationships

**Example:**
UI: EditText "Password" [sec=high][form=login]
APP: LoginActivity [visits=2][pattern=form]
HISTORY: LoginActivity → MainActivity → SettingsActivity

### 2. Advanced Reasoning-Oriented Techniques

#### 2.1 Reasoning Tags
- Use short, specific tags to trigger reasoning pathways
- Create a compact taxonomy of instructions
- Leverage the model's ability to interpret tag semantics

**Example:**
[NAV] Button "Menu" → CLICK(1)
[FORM] EditText "Username" → SET_TEXT(2)
[SEC][M] Button "Encrypt" → CLICK(3)

#### 2.2 Dynamic Contextualization
- Adapt context presentation based on the current state
- Provide relevant contextual clues compactly
- Focus context on decision-critical information

**Example:**
CONTEXT: [First visit][Form pattern][2/5 fields filled]

#### 2.3 Counterposed Goals Encoding
- Explicitly encode competing objectives
- Use compact notation to represent trade-offs
- Allow the model to reason about priority balancing

**Example:**
GOALS: [A] Test monitored ops | [A] New states | [B] Complete flows

#### 2.4 Input-Process-Output (IPO) Framework
- Structure information in a computational-like framework
- Create clear distinctions between different data roles
- Leverage the model's understanding of information flow

**Example:**
INPUT: EditText "Message" → SET_TEXT(1)
PROCESS[M]: Button "Encrypt" → CLICK(2)
OUTPUT: TextView "Result" → VISIBLE(3)

#### 2.5 Decision Tree Hinting
- Provide compact decision pathways
- Use conditional notation to encode decision logic
- Leverage the model's ability to follow implied branching

**Example:**
if [form] → fill_all → submit
if [dialog] → read → select_positive
if [list] → scroll → select_item

### 3. Specialized Prompt Structures for Testing

#### 3.1 Hierarchical Goal Structuring
- Structure test objectives at strategic and tactical levels
- Create a clear reasoning framework
- Focus on key decision factors

**Example:**
Android Testing
Strategic Goals:

Test monitored security operations
Maximize state coverage

Tactical Goal:

Select 1 action advancing these goals in current state


#### 3.2 Implicit Chain-of-Thought
- Structure prompts to induce reasoning steps without explicitly requesting them
- Use a format that guides through logical assessment stages
- Reduce verbosity while maintaining reasoning guidance

**Example:**
Activity: {activity}
UI Elements:
{ui_elements}
Monitored Ops: {monitored_operations.summary}
Evaluate and decide:

Which elements relate to monitored operations?
What is the most effective next testing action?


#### 3.3 Priority Encoding
- Use compact notation for multi-level priorities
- Create a consistent schema for importance indication
- Allow the model to reason about competing priorities

**Example:**
Priorities [A=High, M=Medium, L=Low]:
[A] Test methods with monitored operations
[A] Explore unvisited states
[M] Complete existing UI flows
[L] Return to previously visited states

#### 3.4 Structured Reasoning Format
- Format prompts to facilitate reasoning about patterns and relationships
- Create clear connections between different elements
- Guide reasoning without explicit instructions

**Example:**
UI Pattern → Logical Sequence → Test Objective
Elements: {ui_elements}
Patterns: {ui_patterns}
Identify: [main pattern] → [2-5 related actions] → [test goal]
Format: JSON with pattern_type, actions[], batch_explanation

#### 3.5 Compact Diagnostic Questions
- Use short, targeted questions to guide reasoning
- Focus on key decision factors
- Reduce verbosity while maintaining guidance

**Example:**
Activity: {activity}
Elements: {ui_elements}

Does this state access monitored methods?
Which element has highest coverage potential?
Best testing action and why?


### 4. Temporal and Sequential Encoding

#### 4.1 Action History Compression
- Represent history in a compact, connected format
- Use arrow notation to show action flow
- Include only decision-relevant history

**Example:**
HISTORY: SET_TEXT(2)="username" → CLICK(3)="login" → LoginActivity → CLICK(7)="settings"

#### 4.2 State Transition Mapping
- Create compact representations of state transitions
- Use reference IDs to link actions and states
- Provide transition context efficiently

**Example:**
TRANSITIONS:
MainActivity[1] -(CLICK(3))→ LoginActivity[2]
LoginActivity[2] -(CLICK(5))→ DashboardActivity[3][M]

#### 4.3 Pattern-Focused Sequencing
- Encode common action sequences compactly
- Reference known UI patterns to imply action sequences
- Leverage the model's understanding of UI conventions

**Example:**
PATTERN: Login (expects: username→password→submit)
PATTERN: List (expects: scroll→select→action)

### 5. Information Density Optimization

#### 5.1 Semantic Compression
- Remove redundant information
- Use domain-specific abbreviations
- Focus on information useful for reasoning

**Example:**
Instead of:
"The current screen contains a button with text 'Login' that is enabled and clickable"
Use:
"Button: 'Login' [en][click] → CLICK(1)"

#### 5.2 Attribute Selectors
- Use compact notation for property filtering
- Create consistent patterns for attribute description
- Eliminate verbose property listings

**Example:**
Instead of:
"Find all buttons that are enabled and related to security operations"
Use:
"Find: Button[en][sec][M]"

#### 5.3 Contextual References
- Use short references to previous content
- Create a compact cross-referencing system
- Eliminate repeated information

**Example:**
Instead of:
"The username field mentioned earlier in the form should be filled first"
Use:
"Fill: $form.username first"

#### 5.4 Multi-level Formatting
- Use formatting hierarchy to indicate information importance
- Create visual patterns for different information types
- Leverage formatting for implicit relationship encoding

**Example:**
MainActivity

Form: Login


Username [id=user] → SET_TEXT(1)
Password [id=pass] → SET_TEXT(2)
Submit [id=login][M] → CLICK(3)


## Implementation Considerations for RV-Android

When applying these techniques to RV-Android prompts, consider:

1. **Template Compatibility**: Ensure techniques work within the Jinja2 templating system

2. **Gradual Adoption**: Test changes incrementally to verify model performance

3. **Balanced Approach**: Combine multiple techniques rather than relying on just one

4. **Monitoring**: Track token reduction while maintaining test effectiveness

5. **Model-Specific Tuning**: Adjust techniques based on the specific LLM being used

By applying these reasoning-oriented techniques, RV-Android's prompt system can achieve significant token reduction while maintaining or even improving the effectiveness of LLM-guided testing.



# Appendix D: Simplified Template Structure for 8GB GPU Optimization

## D.1 Optimization Objectives

This appendix outlines a streamlined template structure specifically designed for running RV-Android on systems with limited GPU memory (8GB). The optimization focuses on:

1. **Reducing token count** in prompts through concise language and efficient structures
2. **Improving clarity** of instructions to maintain effective LLM decision making
3. **Maintaining flexibility** for future extensions while reducing overhead
4. **Prioritizing critical information** like ScreenDescription for action selection
5. **Handling complex interactions** with clearer guidance on proper sequencing

## D.2 Template System Overview

The updated template system maintains the XML-based approach with CDATA sections for human-readable content, while significantly reducing token count through strategic simplification.

### D.2.1 High-Level Template Organization

```
/templates/
    ├── system_base.xml          # Base template with common structure
    ├── standard_modular.xml     # For single action generation
    └── batch_action_modular.xml # For multi-action sequences
/fragments/
    ├── core/                    # Essential fragments
    │   ├── system_intro.xml     # System role definition
    │   ├── guidelines.xml       # Core testing guidelines
    │   ├── user_base.xml        # Base user prompt structure
    │   └── history_section.xml  # Compact history representation
    ├── format/                  # Response format fragments
    │   ├── standard_format.xml  # Single action format
    │   └── batch_format.xml     # Multi-action format  
    └── instructions/            # Task-specific fragments
        ├── standard_instructions.xml
        └── batch_instructions.xml
```

## D.3 Key Template Components

### D.3.1 System Base Template

The system base template provides the overall structure for all prompts, with extensible blocks for strategy-specific content.

```xml
<template name="system_base" version="1.0">
  <roles>
    <system><![CDATA[
{% block system_intro %}
You are an Android testing specialist. Your task is to select effective testing actions in a logical sequence.

KEY OBJECTIVES:
TEST SYSTEMATICALLY - Follow natural interaction order for the current UI
MAXIMIZE COVERAGE - Test all interactive elements when appropriate
PRIORITIZE KEY METHODS - Give special attention to operations marked with [M] or [DM]
EXPLORE THOROUGHLY - Test edge cases and complex interactions
{% endblock %}

{% block strategy_specific_instructions %}
{{ strategy_specific_instructions }}
{% endblock %}

{% block response_format_instructions %}
{{ response_format_instructions }}
{% endblock %}

{% block system_guidelines %}
TESTING GUIDELINES:
FOLLOW LOGICAL ORDER - Complete form fields before submitting, open dropdowns before selecting
PRIORITIZE NEW AREAS - Explore untested functionality before revisiting familiar screens
USE APPROPRIATE VALUES - Match input values to field types (email, password, etc.)
TARGET MARKED OPERATIONS - When appropriate, select actions marked with [M] or [DM]
CONSIDER SEQUENCES - For multi-step interactions (forms, dialogs, menus), follow a complete sequence
{% endblock %}

{% if additional_guidelines %}
{% block additional_guidelines %}
{{ additional_guidelines }}
{% endblock %}
{% endif %}]]>
    </system>
  </roles>
</template>
```

### D.3.2 Standard Action Template

The standard action template focuses on generating a single action with precise instructions.

```xml
<template name="standard_modular" version="1.0" extends="system_base">
  <roles>
    <system>
      <variable name="strategy_specific_instructions">
        <![CDATA[Select EXACTLY ONE action from the available options. Choose the action that most effectively advances testing coverage while following a logical interaction sequence.]]>
      </variable>
      <variable name="response_format_instructions">
        <![CDATA[RESPONSE FORMAT (JSON only):
{
  "actions": [
    {
      "action_id": "6",
      "params": {},
      "explanation": "Clicking the submit button to test form submission"
    }
  ]
}

For actions that require parameters (like SET_TEXT):
{
  "actions": [
    {
      "action_id": "5",
      "params": {"text": "test@example.com"},
      "explanation": "Entering a valid email address in the email field"
    }
  ]
}

You must select EXACTLY ONE action. Your response must be valid, parseable JSON with no additional text.]]>
      </variable>
    </system>
    <user><![CDATA[
SCREEN: {{ activity }}

{{ ui_elements }}

{% if action_history %}
RECENT ACTIONS:
{% for iteration in action_history %}
{{ iteration }}
{% endfor %}
{% endif %}

{% if transition_guidance %}
TRANSITIONS:
{% for action, target in transition_guidance.transitions %}
{{ action }} -> {{ target }}
{% endfor %}
{% endif %}
    ]]></user>
  </roles>
</template>
```

### D.3.3 Batch Action Template

The batch action template enables generation of multiple related actions as a coherent sequence.

```xml
<template name="batch_action_modular" version="1.0" extends="system_base">
  <roles>
    <system>
      <variable name="strategy_specific_instructions">
        <![CDATA[Analyze the current UI and create a BATCH OF RELATED ACTIONS that form a logical testing sequence.

Create a sequence of actions that:
- Follow natural interaction order
- Test all relevant elements
- Complete a coherent testing flow
- Prioritize marked operations [M] or [DM] when appropriate
- Ensure all actions in your batch are currently available on the screen.]]>
      </variable>
      <variable name="response_format_instructions">
        <![CDATA[RESPONSE FORMAT (JSON only):
{
  "actions": [
    {
      "action_id": "2",
      "params": {"text": "testuser"},
      "explanation": "Entering a username in the username field"
    },
    {
      "action_id": "4",
      "params": {"text": "password123"},
      "explanation": "Entering a password in the password field"
    },
    {
      "action_id": "6",
      "params": {},
      "explanation": "Clicking the Login button to submit the form"
    }
  ],
  "batch_explanation": "This batch completes the login form in a logical order: filling the username, then password, then submitting"
}

Your response must be valid, parseable JSON with no additional text.]]>
      </variable>
    </system>
    <user><![CDATA[
SCREEN: {{ activity }}

{{ ui_elements }}

{% if action_history %}
RECENT ACTIONS:
{% for iteration in action_history %}
{{ iteration }}
{% endfor %}
{% endif %}

{% if transition_guidance %}
TRANSITIONS:
{% for action, target in transition_guidance.transitions %}
{{ action }} -> {{ target }}
{% endfor %}
{% endif %}
    ]]></user>
  </roles>
</template>
```

## D.4 Core Fragments

### D.4.1 UI Elements Fragment

The UI Elements fragment is the most critical component, presenting screen elements and actions with monitored operation markers.

```xml
<fragment name="ui_elements_format">
  <![CDATA[
The current screen has the following UI views and corresponding actions:

{% for item in screen_items %}
{{ item.description }} {% if item.has_monitored_ops %}[M]{% endif %}{% if item.has_direct_monitored_ops %}[DM]{% endif %}
  Available actions:
  {% for action in item.actions %}
  - {{ action.text }} ({{ action.id }}){% if action.reaches_mop %} [M]{% endif %}{% if action.directly_reaches_mop %} [DM]{% endif %}
  {% endfor %}

{% endfor %}
  ]]>
</fragment>
```

### D.4.2 History Section Fragment

The history section presents recent actions in a compact format to provide context without excessive tokens.

```xml
<fragment name="history_section">
  <![CDATA[
{% if action_history %}
RECENT ACTIONS:
{% for iteration in action_history %}
{{ iteration }}
{% endfor %}
{% endif %}

{% if transition_guidance %}
TRANSITIONS:
{% for action, target in transition_guidance.transitions %}
{{ action }} -> {{ target }}
{% endfor %}
{% endif %}
  ]]>
</fragment>
```

## D.5 Token Optimization Techniques

The template system employs several techniques to optimize token usage:

1. **Concise Instructions**: Replacing verbose explanations with direct, actionable guidelines
2. **Compact Markers**: Using [M] and [DM] for monitored and directly monitored operations
3. **Simplified Structure**: Flattening nested sections and reducing indentation
4. **Strategic Information Presentation**: Prioritizing critical information at the top
5. **Optional Content**: Using conditional sections to include only relevant information
6. **Consistent Formatting**: Maintaining a predictable structure for easier LLM processing
7. **Reduced Repetition**: Eliminating redundant instructions or explanations
8. **Short Line Length**: Breaking text into smaller, focused lines
9. **Targeted Guidance**: Providing specific guidance for complex interactions

## D.6 Comparative Examples

### Example 1: Action Description (Before)

```
Button with text 'GENERATE HASH' that is enabled and clickable. This button can trigger a method that reaches operations of interest.
Available Actions: 
  - CLICK (6) [This action may trigger important operations that should be tested]
```

### Example 1: Action Description (After)

```
Button with text 'GENERATE HASH'. Actions: CLICK (6) [M]
```

### Example 2: Testing Guidance (Before)

```
GUIDELINES FOR ACTION SELECTION:
1. ORDERING MATTERS - arrange actions in a logical testing sequence (e.g., fill a form before submitting it)
2. If an action leads to a screen transition, it should typically be the last action in your sequence
3. For text inputs, generate contextually appropriate values based on the field type (email, password, etc.)
4. Prioritize actions that trigger operations of interest (marked as [CRITICAL] or [IMPORTANT])
5. Ensure your suggested actions form a coherent testing strategy
6. For login forms: first fill username, then password, THEN click login button
7. For registration forms: fill ALL fields in a logical order before submission
8. If a screen has a primary action (OK, NEXT, CONTINUE), it should be the LAST action
9. For dropdowns/spinners: click to open them first, then select an option
10. For checkboxes in a form: handle them BEFORE clicking submit buttons
```

### Example 2: Testing Guidance (After)

```
TESTING GUIDELINES:
FOLLOW LOGICAL ORDER - Complete form fields before submitting, open dropdowns before selecting
PRIORITIZE NEW AREAS - Explore untested functionality before revisiting familiar screens
USE APPROPRIATE VALUES - Match input values to field types (email, password, etc.)
TARGET MARKED OPERATIONS - When appropriate, select actions marked with [M] or [DM]
CONSIDER SEQUENCES - For multi-step interactions (forms, dialogs, menus), follow a complete sequence
```

## D.7 Implementation Recommendations

1. **Phased Migration**: Implement the new template structure in phases, starting with the most used templates
2. **Memory Profiling**: Monitor token usage and memory consumption during template rendering
3. **Template Validation**: Create a validation system to ensure new templates meet token efficiency guidelines
4. **Dynamic Content Control**: Implement mechanisms to limit content based on available system resources
5. **Template Composition**: Use template composition over inheritance when possible
6. **Content Pruning**: Regularly review templates to identify and remove unnecessary content
7. **Token Budgeting**: Set token budgets for different sections of the prompt

## D.8 Handling Complex Interaction Patterns

The template system includes specific guidance for handling complex interaction patterns:

### D.8.1 Multi-Step Interactions

```xml
<fragment name="multi_step_guidance">
  <![CDATA[
COMPLEX INTERACTION HANDLING:

DROPDOWNS/SPINNERS:
- First click to open (ActionID)
- A new screen will appear with options
- You'll get another chance to select an option from that screen

NAVIGATION ACTIONS:
- Actions that navigate to new screens should be last in a sequence
- Never include actions that might execute on a different screen

FORM SUBMISSION:
- Always fill ALL required fields before submitting
- Validate input constraints before submission (min length, format, etc.)
  ]]>
</fragment>
```

### D.8.2 Navigation Awareness

```xml
<fragment name="navigation_awareness">
  <![CDATA[
TRANSITION AWARENESS:
{% if has_navigation_actions %}
The following actions may cause navigation to a different screen:
{% for action in navigation_actions %}
- {{ action.text }} ({{ action.id }}) → {{ action.target_activity }}
{% endfor %}
Select these actions only when you've completed testing the current screen.
{% endif %}
  ]]>
</fragment>
```

## D.9 Expected Impact Analysis

The optimized template structure is expected to yield the following benefits:

1. **Token Reduction**: ~50-60% reduction in overall token count
2. **Memory Usage**: ~40% reduction in GPU memory usage during prompt processing
3. **Clarity Improvement**: Increased focus on logical sequences and critical operations
4. **Performance**: Faster prompt generation and LLM response times
5. **Maintainability**: Simplified template structure for easier updates and extensions

For an 8GB GPU environment, these optimizations should allow the system to handle more complex applications while maintaining effective testing capabilities.
