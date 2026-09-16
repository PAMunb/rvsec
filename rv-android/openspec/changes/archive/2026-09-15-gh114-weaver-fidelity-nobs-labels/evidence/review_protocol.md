# gh114 — pre-registered review protocol

Written 2026-09-15 before any deep reading of the change artifacts. Criteria below are frozen;
any check added after results are seen is appended under "Post-hoc checks" with the suffix `-post`.

Change under review: `openspec/changes/gh114-weaver-fidelity-nobs-labels/` (commit `9025e557`, not implemented).

## Method

- Three areas: consistency (C), weaver TODO scan (T), CrySL adherence (R).
- Each area is reviewed by two independent subagents given this same checklist, the same file
  lists, and no hypotheses. Neither sees the other's output.
- Per check: record A result, B result, agreement (agree / disagree / one-sided). Every
  disagreement is adjudicated by the orchestrator against the source with the rationale written.
- Every surviving finding of severity ≥ medium goes to a third subagent instructed to refute it
  on the source. It survives only if refutation fails.
- Finding types: defect, inconsistency, gap, drift, scope-creep, suggestion.
  Severities: blocker, high, medium, low.
- Every claim cites a `file:line` read in this session. `docs/analise_*` and the handoff prompt
  are not sources. Counts come from a command recorded in the report.

## C — consistency checks

| ID | Check | Pass criterion |
|---|---|---|
| C-01 | Proposal "affected specs" vs delta spec directories | The set of specs named in `proposal.md` equals `{instrumentation, core, analysis, platform}` (the delta dirs). |
| C-02 | Proposal items → delta requirements | Every item in the proposal scope (A1–A6; six labels; trust-manager per-element credit; `REPORTED_UPSTREAM`; `vfp`/`vcls`; RSA alignment; `unique_msg` exclusion; coverage fields; task-major pass; repository release) has at least one ADDED/MODIFIED requirement in a delta spec. |
| C-03 | Delta requirements → design | Every ADDED/MODIFIED requirement is addressed by at least one design decision, or the design says explicitly it needs none. |
| C-04 | Design decisions → tasks | Every design decision has at least one task. |
| C-05 | Scenarios → tasks | Every `#### Scenario:` in the delta specs has a task that makes it testable (a test task or a verification task naming it or its requirement). |
| C-06 | Tasks → requirements/design | Every task in `tasks.md` traces to a requirement, invariant, or design decision (by ID or by unambiguous wording). |
| C-07 | MODIFIED headers vs base | Every `### Requirement:` under a MODIFIED section in a delta spec matches a `### Requirement:` header in the corresponding base spec character for character. |
| C-08 | Restated invariants vs base | INV-CORE-25, INV-PLT-14, INV-PLT-15 as restated differ from the base text only in the points the design says it changes. |
| C-09 | REMOVED consistency | The REMOVED requirement exists in the base spec with the same header; no other delta text, base text kept by the change, or task still relies on INV-INS-122 as live. |
| C-10 | New invariant IDs | INV-INS-159..167, INV-CORE-63, INV-ANA-72, INV-PLT-38 do not already exist in the base specs; no duplicate IDs inside the deltas. |
| C-11 | `file:line` citations vs code | Every `file:line` cited in proposal/design/tasks/specs is re-read; the line holds what the artifact says. Drift is a finding of type drift. |
| C-12 | Parallel ownership | No two groups marked parallel in the same wave list the same file as edited. |
| C-13 | Dependencies | Every stated dependency is real (the dependent group uses an output of the prerequisite); every real dependency is stated (a group that edits a file defined by another group's contract depends on it). |
| C-14 | Generic-tool rule | No artifact text introduces a rule keyed to a dataset, app, library, or package prefix. Class-loader and API-semantics rules pass. |
| C-15 | P1–P4 wording | Normative text (requirements, invariants, design decisions, tasks) contains no migration history, promotional adjectives, or "v2"-style names. |
| C-16 | §2 decisions reflected | One sub-check per decision: (a) one change, A6 in; (b) gh112 treated as archived; (c) no ajc execution/comparison/oracle; (d) only `jca_android`; (e) nothing dataset-specific; (f) labelling not silencing, identity comparison kept; (g) value lists as transcribed except RSA; (h) value fingerprint in; (i) one smoke at end with `ape`, platform manages emulator, no monkey without flags; (j) A3 = branch/switch targets + line-number entries only; (k) cascade = direct producers + `getEncoded` bridge, value/origin reports only, no SecureRandom/KeyGenerator marks, no ORDER-triggered marks; (l) ORDER-01/02 persist on the monitor; (m) `ENVELOPE_RE` of `experimento-gh104/scripts/gh104_gates.py` accepts `vfp`/`vcls` without moving the script; (n) no `wrappersAliasedToFrameworkSubtype`; (o) trust managers only, no key-manager credit/label/property; (p) `vfp` only for `byte[]`, `vcls` only for `TrustManager[]`. Each passes if the artifacts state exactly that and nothing contradicting it. |
| C-17 | Scope creep | No requirement, design decision, or task introduces work not listed in §1/§2 of the mandate. Known removed items (alias counter, key-manager credit, wide evidence, try-range moves, SecureRandom cascade marks, ajc differential) are absent. |
| C-18 | Scenario format | Every scenario uses WHEN/THEN(/AND) with concrete values. |
| C-19 | Proposal header | `GitHub Issue: #114` present; every FR/NFR ID referenced exists in `docs/PRD.md`. |
| C-20 | Validation | `openspec validate gh114-weaver-fidelity-nobs-labels` passes. |

## T — weaver TODO / future-work scan

| ID | Check | Pass criterion |
|---|---|---|
| T-01 | Source markers | `rg -n "TODO\|FIXME\|XXX"` over `rvsec-instrumentation-dexlib2/**/src/main` (excluding `target/`); every hit listed with `file:line`. |
| T-02 | Prose deferrals | `rg -n -i "future work\|not implemented\|recorded as future work\|deferred\|out of scope"` over `rvsec-instrumentation-dexlib2/architecture.md`, every `CLAUDE.md` under that module and under `modules/rv-instrumentation-dexlib2`, `modules/rv-instrumentation-dexlib2/docs/architecture.md`, `openspec/specs/instrumentation/spec.md`; every hit listed. |
| T-03 | Findings documents | Every deferred/open item in `docs/20260827_achados_instrumentador_dexlib2.md` and `docs/20260827_divergencia_after_dexlib2_ajc.md` listed with `file:line`. |
| T-04 | Archived designs | Every Open Question in `design.md` of archived gh100/gh104/gh105/gh109 that concerns the DEX weaver listed with `file:line`. |
| T-05 | Still true | For each candidate, the current code is read and the item is marked still-true / already-fixed / partially-fixed with `file:line`. |
| T-06 | Class | Each candidate classified: repair that does not alter the accused set, or change that alters it. |
| T-07 | Cost / benefit / verifiability | Each candidate has files touched, risk, measured or measurable effect, and whether static verification (unit test on bytecode shape, grep) suffices. |
| T-08 | Overlap with gh114 | Each candidate marked as already covered by A1–A5/A6, partially covered, or not covered; recommendation is one of include / separate change / leave, phrased as a question. |

## R — CrySL adherence (oracle: pinned expert rules)

| ID | Check | Pass criterion |
|---|---|---|
| R-01 | Oracle integrity | sha256 over `RVSec-replication-package/tools/rules/*.crysl` equals the freeze value in `data/jca_android/README.md`; 49 files. |
| R-02 | `platform-default` | TMF/KMF `init(null)` and the three `SSLContext.init` `null` arguments: the rule text (`TrustManagerFactory.crysl`, `KeyManagerFactory.crysl`, `SSLContext.crysl`) either admits null, requires a predicate, or is silent; the label keeps the same accused set and only changes the code. |
| R-03 | `application-manager` | The class-loader criterion vs `SSLContext.crysl` REQUIRES on `TrustManager[]`; label only. |
| R-04 | `upstream-refused` / `REPORTED_UPSTREAM` | Producers (direct + `getEncoded` bridge) and consumers named in the artifacts match the ENSURES/REQUIRES chains of the rules and the `ensure`/`validate` calls of the `.mop` files; no SecureRandom/KeyGenerator mark. |
| R-05 | `random-key-material` | vs `SecretKeySpec.crysl` REQUIRES (`randomized` / `preparedKeyMaterial` or equivalent); label only. |
| R-06 | `creation-unobserved` (ORDER-01) | vs the ORDER clause of each rule whose spec gets the label; the monitor's start state and first-event transition confirm. |
| R-07 | `reuse-after-final` (ORDER-02) | vs `Cipher.crysl` ORDER (line ~85) and `Mac.crysl` ORDER (line ~41); monitor transition table confirms the accused transition. |
| R-08 | RSA alignment | `RSAKeyGenParameterSpec.crysl:15` vs `KeyPairGenerator.crysl:29`; the `oracle-wart` row is planned and consistent with D-20.4 precedent; departure kind named. |
| R-09 | Trust-manager per-element credit | vs `SSLContext.crysl` REQUIRES and `TrustManagerFactory.crysl` ENSURES; all-elements rule stated and its effect on the accused set acknowledged. |
| R-10 | A5 window clauses | Rows in `data/jca_android/conformance_record.csv` written in the no-finally semantics are identified and the artifacts plan their re-founding. |
| R-11 | Three oracles | For every R item where rule and `.mop` disagree, or where ORDER/emission is involved, the generated monitor is read; a disagreement between any two oracles is a finding. |
| R-12 | Specsheet §7 | Items 3, 5, 7, 8, 10, 11, 14 re-checked against rule, `.mop`, monitor; each marked resolved-by-gh114 / untouched / contradicted. |
| R-13 | Classification | Every item classified: faithful transcription / relabel only / departure (kind, recorded?) / defect. |
| R-14 | Accused set | Only the trust-manager per-element credit changes which (site, event) pairs report; every other label is code-only. |

## Post-hoc checks

(none yet)
