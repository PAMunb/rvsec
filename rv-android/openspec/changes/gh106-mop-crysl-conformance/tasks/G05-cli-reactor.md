# G05 · CLI + reactor

**Depends on:** G00. **Blocks:** G12.
**Parallel with:** G01, G02, G03, G04.
**Size:** ~4 files plus the reactor integration test.

## Reference
- `specs/conformance/spec.md` — "Reactor Placement, Dependency Discipline and CLI", INV-CONF-16
- Shape template: `rvsec/rvsec-mop-extractor` — pom, CLI, facade, visitor, writer. **By shape, not by code.**

## Tasks

- [ ] 5.1 **Decide and record where the CLI lives.** It needs `-core`, `-mop` and `-crysl` at once, and the three-module shape gives it no natural home. Recommendation: `rvsec-crysl-crysl`, adding a dependency on `-mop`, because that is the module the single-JVM probe actually ran in — both parsers on one classpath under Guava 33.5. The alternative is a fourth `-cli` module, which contradicts the recorded three-module decision. Write the choice and its reason into the module's package-info; do not leave it implicit.
- [ ] 5.2 `cli/ConformanceCli.java` — `main` plus three subcommands: `compare` (the M0–M4 run against the upstream oracle), `lower` (`mop.lower` plus the round-trip gate), `calibrate` (the G12 gate on its own). Follow the argument-parsing and facade conventions of `rvsec-mop-extractor`.
- [ ] 5.3 `compare` takes the **single** oracle: `compare(mop, rule, alphabet, androidJar)`. There is no two-oracle mode to offer; the emitted report names the oracle (repository and commit) and the pairing rule in its header (INV-CONF-11).
- [ ] 5.4 `compare` requires an explicit `--commit`; there is no default and no auto-detection from `git`. The caller states which corpus state they are measuring, and a wrong stamp is then their assertion rather than a silent inference.
- [ ] 5.5 Exit codes: `0` clean; a non-zero code for `CorpusReadError`, `MissingVersionError` and `CalibrationMismatch`. `LiftFailure` and `Unknown` are **not** failures — they are results, and a run that produces many of them still exits `0` with the counts in the report.
- [ ] 5.6 `ReactorBuildIT` — the four modules build under the reactor's existing command with no change to it, and `main.basedir` resolves in the new modules.
- [ ] 5.7 `DependencyDisciplineTest` — the effective pom has `guava.version = 33.5.0-jre` and `scala.version = 2.11.12`; `ptltl` is on the `-mop` classpath; `slf4j-simple` is absent from `-crysl`; Guava is absent from the `-mop` resolved classpath (INV-CONF-16). Assert the effective pom rather than trusting a silent build: the Guava failure is a runtime `NoSuchMethodError`, not a compile error, so a build that succeeds proves nothing.
- [ ] 5.8 A smoke run of `compare` over one specification against the upstream oracle, asserting the three output formats appear with their stamps.
- [ ] 5.9 `mvn clean install -DskipMopAgent` at the reactor root, JDK 21, green with tests enabled for the four new modules.
- [ ] 5.10 **Add the CI step, or everything above is a local-only green.** `.github/workflows/ci.yml:30` builds the reactor with `-DskipTests`; the only module whose tests run is dexlib2 `grammar-tests`, through an explicit `-DskipTests=false` step at `:44`. Without a matching step, the 17 invariant tests, the ArchUnit rules, the 40-shuffle order-invariance test and the calibration gate never execute in CI — the same false green this repository has shipped twice. Copy the shape of the `grammar-tests` step. `risk-register.md` RISK-001.
- [ ] 5.11 **Split the suite by what CI can reach.** `rvsec-cognicrypt` is a separate git repository and `android.jar` comes from `$ANDROID_HOME`; the CI checkout has neither. Tag the oracle-dependent tests (G02 2.6/2.7/2.8 and calibration targets 4–6) so CI excludes them by tag, and document the local setup that runs them. **Declare the split** in the workflow and in `G14`: a partial green that looks total is worse than a red. `risk-register.md` RISK-002.

## Closing
G05 closes when 5.1–5.11 are `[x]`.
