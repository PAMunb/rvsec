# architecture-model.json — Schema

This is the contract between `rv-doc-arch-analyze` (writer) and `rv-doc-arch-generate`
(reader). It replaces the role the Neo4j graph plays in the upstream `agente-documentador`
suite: a single file-based intermediate that decouples analysis from generation. Generation
never re-analyzes the code; it only reads this file (and may re-read source to quote a name).

Write it to: `out/arch/<target-slug>/architecture-model.json`
(`<target-slug>` is the target with `:` replaced by `-`, e.g. `subsystem-instrumentation`).

## Depth is the point

The generated document must read as **narrative onboarding for a new engineer** with no
prior exposure to the target (CLAUDE.md P2: narrative, self-contained, explain *why* not just
*what*). That depth must originate **here**, in analysis — the writer has already read the
code; the generator only renders. So most narrative fields below are **paragraphs of prose**,
not labels. Write full sentences. Explain reasons inline. Use concrete names, paths, and
values. Tables in the document are summaries; the prose carries the understanding.

Be descriptive, not prescriptive: include only what the analysis substantiates. Omit empty
arrays rather than inventing content. But do not pad with terse one-liners where a paragraph
is warranted — a one-sentence `how_it_works` is a defect, not brevity.

## Top-level shape

```json
{
  "target": "subsystem:instrumentation",
  "scope": "subsystem",
  "generated_for": "instrumentation",
  "language_mix": [
    { "language": "python", "modules": 4, "approx_loc": 2200 },
    { "language": "java",   "modules": 9, "approx_loc": 6000 }
  ],

  "primer": {
    "what": "2-4 sentence plain-language statement of what this subsystem is and does, for someone who has never seen it. No jargon without defining it.",
    "why_this_approach": "Paragraph: why the subsystem exists and why it is built this way rather than the obvious alternative (e.g. why DEX-native weaving instead of the AspectJ/dex2jar pipeline). Name the alternative and the trade-off.",
    "key_concepts": [
      { "term": "DEX weaving", "explanation": "1-3 sentence definition a newcomer needs before reading further." },
      { "term": "pointcut / advice", "explanation": "..." }
    ]
  },

  "walkthrough": {
    "example": "One concrete, named example that the end-to-end narrative follows (e.g. 'instrumenting a call to javax.crypto.Cipher.getInstance(String) so a before-advice fires').",
    "steps": [
      {
        "stage": "descriptor read",
        "narrative": "Full-sentence prose: what happens at this stage to the running example, which class/method does it, and what artifact it produces.",
        "concrete_detail": "A specific value/name/shape for the example (e.g. 'the descriptor entry advice[2] with pointcut call(* Cipher.getInstance(..))')."
      }
    ]
  },

  "modules": [
    {
      "name": "dex-mutator",
      "language": "java",
      "path": "../rvsec/rvsec-android/rvsec-instrumentation-dexlib2/dex-mutator",
      "role": "One-line role (used in the catalog table).",
      "layer": "executor",
      "key_units": ["DexWeaver", "RegisterAllocator", "RegisterShifter"],
      "source": "generic",
      "how_it_works": "Paragraph (3-6 sentences): the internal mechanics. How does this module do its job, step by step, naming the key classes and the data it transforms? What is the tricky part (e.g. register allocation under DEX's 4-bit/16-bit operand limits)?",
      "why_separate": "Paragraph (2-4 sentences): why this is its own module rather than folded into a neighbor. What design tension does the boundary protect (e.g. keeping bytecode mutation a pure executor, independent of pointcut semantics)?",
      "gotchas": [
        "Concrete non-obvious fact a maintainer must know (e.g. 'RegisterShifter must bump registerCount or the APK fails verification with VerifyError on-device').",
        "..."
      ]
    }
  ],

  "components": [
    {
      "id": "dexlib2-java-engine",
      "name": "DEX-native weaving engine",
      "kind": "subprocess",
      "realized_by": ["rvsec-instrumentation-dexlib2/*"],
      "responsibility": "One-line responsibility (catalog table).",
      "narrative": "Paragraph: what this runtime element is, how it behaves during a run, and how it relates to the others. Use for the components a newcomer must understand to follow the data flow."
    }
  ],

  "relations": [
    { "type": "uses",     "from": "rv-instrumentation", "to": "rv-instrumentation-dexlib2" },
    { "type": "depends",  "from": "rv-instrumentation-dexlib2", "to": "dexlib2-java-engine", "mechanism": "subprocess: java -jar instr-cli.jar" },
    { "type": "contains", "from": "rvsec-instrumentation-dexlib2", "to": "pointcut-engine" }
  ],

  "styles": {
    "module": [
      { "name": "layered", "confidence": "high", "evidence": "core <- variants <- parent; acyclic (INV-INS-41)" }
    ],
    "c_and_c": [
      { "name": "client-server", "confidence": "medium", "evidence": "Python wrapper invokes Java CLI as a subprocess" }
    ],
    "allocation": [
      { "name": "install", "confidence": "high", "evidence": "Maven shade fat JAR auto-copied to python lib/ (design D9)" }
    ]
  },

  "decisions": [
    {
      "title": "Matcher / emitter / mutator separation",
      "summary": "One-line summary (decision table).",
      "drivers": ["single responsibility per stage", "stage-level testability"],
      "invariant": "INV-INS-54",
      "adr_ref": null,
      "narrative": "Paragraph (3-5 sentences): the design tension, the alternative that was rejected, and what would go wrong without this decision. Explain it so a newcomer understands not just the choice but the forces behind it."
    }
  ],

  "nfrs": [
    {
      "name": "Compatibility",
      "prd_id": "NFR07",
      "support": "Paragraph: how the architecture achieves this NFR, with the concrete mechanism (e.g. 'recomputes register counts so instrumented APKs verify on-device').",
      "evidence": "file/class reference"
    }
  ],

  "external_systems": [
    { "name": "rv-monitor-generator", "relation": "produces the JSON descriptor + monitor .java sources consumed by the engine" }
  ],

  "output_artifacts": [
    { "name": "instrumented APKs", "where": "results_dir", "notes": "signed, ready to deploy" }
  ],

  "scenarios": [
    {
      "when": "a before-advice matches a method call whose arguments occupy registers v0–v14 and the advice needs one more register",
      "then": "RegisterShifter widens the invoke to a -range/from16 form and increments registerCount in the method",
      "and": "the woven method still verifies on-device because the register file was grown, not overflowed",
      "why": "DEX packs many operands into 4-bit fields; exceeding v15 without widening produces an invalid instruction and a VerifyError at install time."
    }
  ],

  "views_selected": [
    { "category": "module",     "style": "layered",       "reason": "show the abstraction/variant/parent tiers" },
    { "category": "c_and_c",    "style": "client-server", "reason": "show the Python<->Java subprocess boundary" },
    { "category": "allocation", "style": "install",       "reason": "show the fat-JAR artifact layout / D9 copy" }
  ],
  "views_excluded": [
    { "category": "c_and_c", "style": "pipe-and-filter", "reason": "no streaming connector at this scope" }
  ],

  "sdd": {
    "domain": "instrumentation",
    "spec_file": "openspec/specs/instrumentation/spec.md",
    "frs": ["FR01", "FR02", "FR03"],
    "invariants": ["INV-INS-41", "INV-INS-50", "INV-INS-55"],
    "nfrs": ["NFR07"]
  }
}
```

## Field notes

**Narrative fields (the depth — do not skimp):**
- **primer** — the conceptual on-ramp. A newcomer reads this first. Define every term they
  need before the views. `why_this_approach` must name the rejected alternative and the
  trade-off, not just praise the choice.
- **walkthrough** — one concrete, named example traced through every pipeline stage. This is
  the single most important onboarding aid: it turns a static structure into a story. Each
  step's `narrative` is prose; `concrete_detail` pins it to a real value/name.
- **modules[].how_it_works / why_separate / gotchas** — the per-component depth. `how_it_works`
  is a paragraph on internal mechanics naming key classes; `why_separate` explains the module
  boundary's purpose; `gotchas` are the non-obvious facts a maintainer learns the hard way.
- **components[].narrative** — paragraph for runtime elements a reader must understand to
  follow the data flow.
- **decisions[].narrative** — the forces behind the decision: tension, rejected alternative,
  failure mode if absent. This is *why*, not *what*.
- **nfrs[].support** — a paragraph with the concrete mechanism, not a label.
- **scenarios[]** — WHEN/THEN/AND items with concrete values, one per non-obvious behavior
  (register pressure, phase-tagged failure, coverage exclusion, optional-stage skipping).
  `why` explains the underlying reason. These satisfy CLAUDE.md P2's scenario requirement.

**Structural fields (as before):**
- **target / scope** — `scope` ∈ `system | module | subsystem`; `target` is the raw argument.
- **language_mix** — multiple entries → cross-language target; note the boundary in the doc.
- **modules[].source** — `rv-analyze-module` (Python, reused skill) or `generic` (Java/other).
- **components[].kind** — `class | service | subprocess | store | external`.
- **relations[].type** — `uses | depends | contains | generalizes`; add `mechanism` for
  non-obvious links (subprocess, network, shared file).
- **styles** — each entry needs `evidence`; `confidence` ∈ `high | medium | low`.
- **decisions** — link `invariant` (INV-XX-NN) and/or `adr_ref` when one exists. Do not author
  ADRs here — that is `rv-doc-adr`'s job; only reference them.
- **sdd** — from `openspec/specs/<domain>/spec.md` and `docs/PRD.md` §7. Leave arrays empty
  (not invented) when a cross-tree subsystem maps only partially.
