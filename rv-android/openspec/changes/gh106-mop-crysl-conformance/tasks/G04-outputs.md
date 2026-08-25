# G04 · outputs

**Depends on:** G00. **Blocks:** G10, G12.
**Parallel with:** G01, G02, G03, G05.
**Size:** ~5 files in `rvsec-crysl-core`.

The emitters are where INV-CONF-02 becomes real. A counting rule that lives in a comment is not a
counting rule; it has to be data the emitter reads.

## Reference
- `specs/conformance/spec.md` — INV-CONF-01, -02, -08, -15
- Committed schemas to match: `data/jca_android/{predicate_graph,constraint_table,order_alphabet_map,divergence_record}.csv`
- Markdown shape to match: `data/gh104/evidence/harness/*.md`

## Tasks

- [x] 4.1 `emit/StampedTable.java` — the single choke point every emitter goes through. It takes the aggregate, its counting rule and the `Version`, and **refuses to render** a table whose counting rule is absent (INV-CONF-02). Nothing bypasses it.
- [x] 4.2 `emit/JsonEmitter.java` — throws `MissingVersionError` on an unstamped model (INV-CONF-01). Document at the class that JSON here is an **output** of the canonical model, never an interchange format between processes (D-01), so nobody reintroduces the three-process seam by writing a reader for it.
- [x] 4.3 `emit/CsvEmitter.java` — emit in the **existing** committed schemas, column for column, so the component substitutes the manual tables instead of creating a parallel island. Read the four headers from the committed files at build time and assert the emitted headers match, so a schema drift fails the build rather than producing a second dialect. The emitter produces `.crysl` (upstream) references; the committed files, anchored on `.cryptsl` paths, are the test's historical-read case, not the emitted format — the producing component re-anchors them.
- [x] 4.4 The M4 CSV emits **both** vocabularies side by side: the site-level `disposition`/`verdict` of `predicate_graph.csv` and the clause-level fidelity class. They describe different objects; emitting one as a substitute for the other would replace a manual table with an automatic table that measures something else.
- [x] 4.5 Every M4 row carries `origin ∈ {derived, inherited}` and every M4 aggregate carries the human-judgement caveat (INV-CONF-15), so a reader can compute the derived fraction rather than take the whole table on trust.
- [x] 4.6 `emit/MarkdownEmitter.java` — evidence reports in the shape of `data/gh104/evidence/*.md`. It **refuses** to place a false-positive or false-negative claim beside a witness whose status is `ABSTRACT` (INV-CONF-08), and prints the normalizations beside every verdict.
- [x] 4.7 Every emitted artifact — JSON, CSV and Markdown — carries the commit stamp in a fixed position, so a reader can tell at a glance which corpus state a table describes.
- [x] 4.8 `test_inv_conf_02_table_carries_rule` — a table constructed without a counting rule cannot be rendered.
- [x] 4.9 `test_inv_conf_01_unstamped_refused` and `test_inv_conf_08_abstract_no_claim`.
- [x] 4.10 Round-trip the CSV: emit, re-read with the existing Python readers under `scripts/`, and assert they parse. The component's output has to be consumable by what already exists during the coexistence window.
- [x] 4.11 `mvn -pl rvsec/rvsec-crysl/rvsec-crysl-core test` green.

## Closing
G04 closes when 4.1–4.11 are `[x]`.
