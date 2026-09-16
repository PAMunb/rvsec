# Fragments of the specification wave (gh114)

The `jca_android` workers of WAVE 1 (G6, G7, G8, G9a, G9b) edit only their own `.mop` files. The
files every worker would otherwise touch at once — `jca_android/codes.csv`, `Property.java` and the
records under `data/jca_android/` — belong to the closing groups of WAVE 2 (design D14). Each worker
hands its share over as the fragments below, and G13a merges them.

## `codes_g<n>.csv` — new rows of `codes.csv`

One file per worker (`codes_g6.csv`, `codes_g7.csv`, `codes_g8.csv`, `codes_g9a.csv`,
`codes_g9b.csv`), with the header and the seven columns of `jca_android/codes.csv`:

```
spec,code,error_type,site_kind,event,file_line,label
TrustManagerFactorySpec,TRUSTMANAGERFACTORY-NOBS-01,UnsatisfiedConstraint,NOBS,init,TrustManagerFactorySpec.mop:152,platform-default
TrustManagerFactorySpec,TRUSTMANAGERFACTORY-ORDER-01,InvalidSequenceOfMethodCalls,ORDER,@fail,TrustManagerFactorySpec.mop:260,creation-unobserved
```

- **Only new codes.** A row whose code already exists is not repeated. An existing row whose
  `file_line` moved because of an edit above it is listed too, with its new anchor, in the same
  file under the same header; G13a replaces the existing row with it.
- **Numbering.** The next free number of the family in the file (`NEW_SPEC_CONVENTIONS.md:167`):
  read the highest `<SPEC>-<KIND>-NN` of that spec in `codes.csv` and add one.
- **`site_kind`** is the family (`NOBS` or `ORDER` for every label code), **`event`** is the event
  name or `@fail`, **`file_line`** is `<File>.mop:<line of the new ErrorDescription(>`, which is
  what the `code-anchor` check of `scripts/gh104_message_gate.py` compares.
- **`label`** is one of `violation`, `sequence`, `not-observed`, `platform-default`,
  `upstream-refused`, `application-manager`, `random-key-material`, `creation-unobserved`,
  `reuse-after-final`, and must agree with the family (INV-INS-164).

## `traces_g<n>/` — harness traces

One file per scenario, in the grammar of `data/gh104/traces/` (documented in
`rvsec/rvsec-mop/src/test/java/br/unb/cic/mop/harness/TraceRunner.java`), named
`<Spec>-<scenario>.txt` — for example `traces_g6/SSLContextSpec-tls_copied_array.txt`.

The leading `#` comment block of each trace states, in prose, the situation, the code and label the
set emits for it after gh114, and whether the same `(spec, event)` reported before gh114. That
comment is what G13a turns into the harness expectation (task 13.2) and what the same-sites
comparison of task 13.5 is checked against. A trace that expects a reported site to disappear is
allowed only for the per-element trust-manager credit, and its comment says so.

## Hand-over notes

A worker that needs a record row (`divergence_record.csv`, `conformance_record.csv`,
`predicate_graph.csv`) does not write it. It lists the hunk and the reason in
`notes_g<n>.md` here; G13b and G13c read those notes.
