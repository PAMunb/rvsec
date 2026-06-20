# Views and Beyond — Method Reference

This reference distills the SEI method *Documenting Software Architectures: Views and
Beyond* (Clements et al.) as applied by the `rv-doc-arch-*` skill suite. It is the shared
vocabulary for the analyze and generate phases. Read it before inferring styles or
filling the output template.

The core idea: an architecture is documented as a set of **views** (each view shows the
system from one category of structure) plus **beyond-views** information that applies
across all views (overview, rationale, mappings, glossary).

## 1. The three view categories

Every structure in a software architecture falls into one of three categories. Each
category has a small set of **styles**; a view documents the system in one style.

### Module views (code-time structure)
What the units of implementation are and how they relate statically.
Styles:
- **Decomposition** — is-part-of. Modules contain submodules.
- **Uses** — depends-on. A unit requires another to be correct.
- **Generalization** — is-a. Inheritance / interface implementation.
- **Layered** — allowed-to-use, restricted by layer ordering.
- **Aspects** — cross-cutting concerns woven across modules.
- **Data model** — entities and their relationships (ER).

### Component-and-connector (C&C) views (run-time structure)
What the runtime elements are (components) and their interaction channels (connectors).
Styles:
- **Pipe-and-filter** — stream transformation through stages.
- **Client-server** — request/response across a service boundary.
- **Peer-to-peer** — symmetric collaborating peers.
- **Service-oriented (SOA)** — independent services, often over a network/process boundary.
- **Publish-subscribe** — event-driven, decoupled producers/consumers.
- **Shared-data** — components communicate through a common store.

### Allocation views (mapping software to environment)
How software maps onto non-software structures.
Styles:
- **Deployment** — C&C elements onto execution nodes (devices, hosts, emulators).
- **Install** — components onto the file system / artifact layout (JARs, packages, images).
- **Work assignment** — modules onto teams / responsibilities.

## 2. The view template (5 sections per view)

Each view in the output document is written with the same five sections:

1. **Primary presentation** — the main diagram (Mermaid) showing the elements and
   relations of this view, with a short legend.
2. **Element catalog** — a table describing each element, its responsibility, and the
   relations/interfaces it participates in. Everything in the diagram appears here.
3. **Context diagram** — how this view's scope connects to its surroundings. Reference
   the single system context diagram in Part I (do not redraw it per view).
4. **Variability guide** — the variation points: where and how the structure can change
   (configuration, plug-in variants, optional elements).
5. **Rationale** — *why* this structure: the decisions, trade-offs, and constraints that
   produced it. Reference the relevant decisions in Part I rather than restating them.

## 3. Beyond-views information (Part I)

Information that spans all views, documented once:

- **Documentation overview** — purpose, scope, intended audience, how to read the doc.
- **System overview & context** — what the system does, its constraints, and the single
  **system context diagram** (external actors and systems). All views reference this.
- **Core components** — the principal elements, with a one-paragraph role each.
- **Mapping between views** — how elements in one view correspond to elements in another
  (e.g. which modules realize which runtime components; which components deploy where).
- **Rationale** — the cross-cutting architectural decisions, the patterns used, and the
  NFRs they serve.
- **Output artifacts** — what the system emits (files, logs, reports, results JSON).
- **Directory** — glossary, acronyms, references.

## 4. Stakeholder → view selection

Document the views that serve the stakeholders who will read the document. Do not produce
every style mechanically; select and record *why* in the model's `views_selected`.

| Stakeholder | Primary concern | Typical views |
|-------------|-----------------|---------------|
| Developer / maintainer | Code organization, dependencies | Module: Decomposition, Uses, Layered |
| Integrator | Interfaces, contracts | Module: Uses; C&C: Client-Server |
| Architect | Whole structure, trade-offs | All categories + Part I rationale |
| Tester | Isolation, test paths | Module: Uses, Decomposition |
| DevOps / SRE | Deployment, packaging | Allocation: Deployment, Install |
| Manager | Work division | Allocation: Work assignment |
| Performance analyst | Throughput, bottlenecks | C&C: Pipe-Filter, Shared-Data |

## 5. How this maps to RV-Android targets

- A **module** target usually needs Module views (Decomposition/Uses/Layered) plus a
  small C&C view if it has meaningful runtime behavior.
- A **subsystem** target (possibly cross-language, e.g. instrumentation = Python wrappers
  + Java/dexlib2 backend) needs Module + C&C + an Allocation (Install/Deployment) view to
  show the process boundary (e.g. `java -jar` subprocess) and artifact layout (the fat JAR).
- A **system** target needs all three categories, with the Mapping-between-views section
  doing the heavy lifting (module → component → deployment).
