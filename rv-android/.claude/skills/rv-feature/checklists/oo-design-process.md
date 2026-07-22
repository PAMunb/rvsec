# Object-Oriented Design Process

A structured approach to designing object-oriented systems.

---

## Overview

The OO design process transforms requirements into a design that can be implemented. It consists of five iterative stages:

```
┌───────────────────────────────────────────────────────────────────┐
│                         OO Design Process                         │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────┐                                              │
│  │ 1. Context &    │  Define system boundaries and interactions  │
│  │    Interactions │                                              │
│  └────────┬────────┘                                              │
│           │                                                       │
│           ▼                                                       │
│  ┌─────────────────┐                                              │
│  │ 2. Architecture │  Identify major components and structure    │
│  │                 │                                              │
│  └────────┬────────┘                                              │
│           │                                                       │
│           ▼                                                       │
│  ┌─────────────────┐                                              │
│  │ 3. Object       │  Identify classes using multiple techniques │
│  │    Identification│                                             │
│  └────────┬────────┘                                              │
│           │                                                       │
│           ▼                                                       │
│  ┌─────────────────┐                                              │
│  │ 4. Design       │  Create structural and behavioral models    │
│  │    Models       │                                              │
│  └────────┬────────┘                                              │
│           │                                                       │
│           ▼                                                       │
│  ┌─────────────────┐                                              │
│  │ 5. Interface    │  Define public interfaces for each class    │
│  │    Specification│                                              │
│  └─────────────────┘                                              │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

---

## Stage 1: Context and Interactions

**Goal**: Define system boundaries and how the feature interacts with its environment.

### Context Model

Shows the feature as a single entity and its external relationships:

```markdown
## Context Model

### Feature: [Name]

### External Entities
| Entity | Type | Interaction |
|--------|------|-------------|
| [entity] | User/System/Service | [what it provides/consumes] |

### Diagram
```
            ┌────────────┐
    ────────► Feature    ◄────────
   Input A  │            │ Service B
            └─────┬──────┘
                  │
                  ▼
              Output C
```

### Boundaries
- **In Scope**: [what the feature handles]
- **Out of Scope**: [what external systems handle]
```

### Interaction Model

Shows the sequence of interactions:

```markdown
## Interaction Model

### Use Case: [Name]

**Actors**: [list]
**Trigger**: [what starts the interaction]

**Sequence**:
1. [Actor] → [Feature]: [action/message]
2. [Feature] → [External]: [action/message]
3. [External] → [Feature]: [response]
4. [Feature] → [Actor]: [result]

**Diagram**:
```
Actor      Feature     External
  │           │           │
  │──request─►│           │
  │           │──query───►│
  │           │◄─response─│
  │◄──result──│           │
```
```

---

## Stage 2: Architectural Design

**Goal**: Identify the high-level components and their organization.

### Component Identification

```markdown
## Architectural Components

### Components
| Component | Responsibility | Layer |
|-----------|----------------|-------|
| [name] | [what it does] | Presentation/Domain/Data |

### Dependencies
```
┌─────────────┐     ┌─────────────┐
│ Component A │────►│ Component B │
└─────────────┘     └─────────────┘
        │
        ▼
┌─────────────┐
│ Component C │
└─────────────┘
```

### Architectural Pattern
- **Pattern**: [e.g., Layered, Repository, Service]
- **Rationale**: [why this pattern fits]
```

---

## Stage 3: Object/Class Identification

**Goal**: Identify the classes needed to implement the feature.

### Technique 1: Grammatical Analysis

Analyze the requirements text:

| Text Element | Design Element |
|--------------|----------------|
| **Nouns** → | Objects/Classes |
| **Verbs** → | Operations/Methods |
| **Adjectives** → | Attributes/Properties |
| **Relationships ("has", "uses")** → | Associations |

**Example**:
```
Requirement: "The user submits a form that validates input and stores data."

Nouns (candidates): User, Form, Input, Data
Verbs (operations): submit(), validate(), store()
```

### Technique 2: Domain Entity Analysis

Identify real-world entities the system models:

```markdown
## Domain Entities

| Entity | Description | Key Attributes | Key Operations |
|--------|-------------|----------------|----------------|
| [entity] | [what it represents] | [data it holds] | [actions it performs] |
```

### Technique 3: Scenario-Based Analysis

Walk through scenarios to discover objects:

```markdown
## Scenario Analysis: [Scenario Name]

**Step-by-step analysis**:

| Step | Action | Objects Involved | Operations |
|------|--------|------------------|------------|
| 1 | User clicks submit | Button, Form | handleClick() |
| 2 | Form validates data | Form, Validator | validate() |
| 3 | Data is saved | Repository, Entity | save() |

**Discovered Classes**: [list]
```

### Technique 4: Behavioral Analysis

Focus on what the system must do:

```markdown
## Behavioral Analysis

### Required Behaviors
| Behavior | Responsibility | Candidate Class |
|----------|----------------|-----------------|
| [behavior] | [what must happen] | [class that should own it] |

### State Changes
| State | Trigger | New State | Class |
|-------|---------|-----------|-------|
| [initial] | [event] | [final] | [owner] |
```

### Class Identification Output

```markdown
## Identified Classes

### Class: [Name]
- **Responsibility**: [single responsibility description]
- **Attributes**: [list of data it holds]
- **Operations**: [list of methods]
- **Collaborators**: [other classes it works with]

### Class Relationships
```
┌─────────────┐           ┌─────────────┐
│   ClassA    │──────────►│   ClassB    │
│             │  uses     │             │
├─────────────┤           ├─────────────┤
│ attr1       │           │ attr1       │
│ attr2       │           │ attr2       │
├─────────────┤           ├─────────────┤
│ method1()   │           │ method1()   │
│ method2()   │           │ method2()   │
└─────────────┘           └─────────────┘
```
```

---

## Stage 4: Design Models

**Goal**: Create detailed structural and behavioral models.

### Structural Models (Static)

Show class structure and relationships:

```markdown
## Class Diagram

### Classes
```
┌──────────────────────┐
│ <<interface>>        │
│ IRepository          │
├──────────────────────┤
│ + save(entity): void │
│ + find(id): Entity   │
└──────────────────────┘
          △
          │ implements
          │
┌──────────────────────┐
│ ConcreteRepository   │
├──────────────────────┤
│ - connection: DB     │
├──────────────────────┤
│ + save(entity): void │
│ + find(id): Entity   │
└──────────────────────┘
```

### Relationships
| From | To | Type | Cardinality |
|------|----|----- |-------------|
| ClassA | ClassB | Association | 1..* |
| ClassC | ClassD | Composition | 1..1 |
| ClassE | ClassF | Inheritance | - |
```

### Behavioral Models (Dynamic)

Show how objects interact over time:

```markdown
## Sequence Diagram: [Use Case]

```
Client          Service         Repository
   │               │                │
   │──request()───►│                │
   │               │──validate()───►│
   │               │◄──result──────│
   │               │──save()───────►│
   │               │◄──confirmation─│
   │◄──response────│                │
```

## State Machine: [Class with complex state]

```
         ┌──────────┐
         │  Idle    │
         └────┬─────┘
              │ start()
              ▼
         ┌──────────┐
    ┌───►│ Running  │───┐
    │    └────┬─────┘   │ error()
    │         │         ▼
    │         │    ┌──────────┐
    │         │    │  Error   │
    │         │    └────┬─────┘
    │         │         │ reset()
    │         │         │
    │         │ complete()
    │         ▼         │
    │    ┌──────────┐   │
    └────│ Complete │◄──┘
         └──────────┘
```
```

---

## Stage 5: Interface Specification

**Goal**: Define clear public interfaces for each class.

### Interface Template

```markdown
## Interface: [ClassName]

### Purpose
[One sentence describing what this class does]

### Public Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| method1 | param1: Type | ReturnType | What it does |
| method2 | param1: Type, param2: Type | ReturnType | What it does |

### Exceptions
| Method | Raises | When |
|--------|--------|------|
| method1 | ValueError | When param1 is invalid |

### Usage Example
```python
# How to use this class
obj = ClassName(config)
result = obj.method1(value)
```

### Contracts (Pre/Post Conditions)
| Method | Pre-condition | Post-condition |
|--------|---------------|----------------|
| method1 | param1 is not None | result is valid |
```

---

## Design Quality Checklist

Before finalizing the design:

- [ ] **Single Responsibility**: Each class has one reason to change
- [ ] **Open/Closed**: Open for extension, closed for modification
- [ ] **Liskov Substitution**: Subtypes substitutable for base types
- [ ] **Interface Segregation**: Clients don't depend on unused methods
- [ ] **Dependency Inversion**: Depend on abstractions, not concretions

- [ ] **High Cohesion**: Related functionality grouped together
- [ ] **Low Coupling**: Minimal dependencies between classes
- [ ] **Encapsulation**: Internal state hidden behind methods
- [ ] **Testability**: Each class can be tested in isolation

---

## Output Summary

After completing all stages, document:

```markdown
## Design Summary

### Context
- **Feature**: [name]
- **Boundaries**: [in/out scope]
- **External Interactions**: [list]

### Architecture
- **Pattern**: [chosen pattern]
- **Components**: [list]

### Classes
| Class | Responsibility | Key Methods |
|-------|----------------|-------------|
| [class] | [responsibility] | [methods] |

### Relationships
| From | To | Type |
|------|----|----- |
| [class] | [class] | [association/composition/inheritance] |

### Interfaces
[List of public interfaces defined]

### Design Patterns Applied
| Pattern | Where | Why |
|---------|-------|-----|
| [pattern] | [class/component] | [problem solved] |
```
