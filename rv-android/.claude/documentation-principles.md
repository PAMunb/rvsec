# Documentation Principles

The single source of the writing rules that every `rv-doc-*` skill and `rv-docs-sync` apply to
the documents they generate or update (CLAUDE.md, README.md, architecture.md, ADRs, docstrings).
The project-wide principles P1–P4 live in the root `CLAUDE.md` ("Development Principles") and
govern these documents too; the rules below apply them to documentation and add style rules.

## Content

1. **Reader perspective.** Write for the reader's task: what they need to know and what they
   look for first. Structure content around their workflow, not around completeness.
2. **No repetition.** State each fact once, in its most logical location, and cross-reference it
   elsewhere. When a fact has an authoritative source (the root `CLAUDE.md` "Module map",
   `openspec/specs/README.md`, a `pyproject.toml`), point to that source instead of copying it.
3. **No ambiguity.** Define a term on first use. Give exact file paths and exact names as they
   appear in code. Prefer concrete examples to abstract descriptions. When a document uses a
   notation (diagram, table), explain how to read it.
4. **Rationale.** Document why, not only what (P2). Every significant choice carries a short
   explanation, so a later reader can change it with the reasoning in hand.
5. **Current state only (P3, P4).** Describe what the code does now. No migration history,
   version notes, "replaces old X", "new"/"NEW" labels, or planned features. Historical
   context belongs in the thesis or the ICST paper, not in the document. The one exception is an
   ADR (`docs/adr/`), which records a decision as it stood when it was taken: once Accepted, only
   its Status and `Superseded by` lines change, and a revised decision is a new ADR.
6. **Proportionate depth (P1).** Skip what the code makes self-evident. Less documentation is
   better than documentation that restates the code.
7. **Standard organization.** Follow the skill's template and section order; consistent
   structure across modules reduces the cost of finding information. A deviation needs a
   content reason.
8. **Audience.** CLAUDE.md is for LLMs (exact paths, copy-pasteable commands). architecture.md
   and `docs/architecture/*.md` are for developers and researchers (conceptual understanding).
   README.md is for someone who wants to use the module (installation, usage, configuration).

## Style

1. **English, objective tone.** No promotional or evaluative words ("modern", "elegant",
   "sophisticated", "cutting-edge", "better").
2. **Present indicative for behavior.** "`parse_file` returns a `StaticAnalysisData` object", not "will
   return". Docstring summary lines keep the imperative mood defined by `/rv-doc-code`.
3. **Condition before instruction.** "When the module has no CLI, omit the CLI section", not
   "Omit the CLI section when the module has no CLI".
4. **"Must" for requirements, "we recommend" for recommendations.** Avoid "should", which leaves
   the reader unsure whether the statement is a requirement.
5. **Meaningful names in examples.** Use names from the domain (`apk_path`, `TaskExecutor`,
   `br.unb.cic.cryptoapp`), never placeholders such as `foo` or `bar`.
6. **Dates in ISO form** (`YYYY-MM-DD`).
7. **Commands that run as written.** Every test command follows the CI contract:
   `uv run pytest <path> --import-mode=importlib -o "addopts="`.
