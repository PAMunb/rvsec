# CLAUDE.md - rvsec-mop

## Purpose
Repository of JavaMOP specifications for monitored operations (0 Java source files — resources only). Consumed directly from source (`src/main/resources`), never packaged/used as a runtime jar.

## Role in pipeline
Source-of-truth for the specs that get compiled into runtime monitors (JavaMOP → RV-Monitor → generated Java/AspectJ) and, on the Android side, into dexlib2-woven monitors.

## Content (verified)
- `src/main/resources/jca/` — **23** `.mop` specs (JCA misuse specs, e.g. `CipherSpec.mop`, `SecureRandomSpec.mop`, `SSLContextSpec.mop`) + matching generated `.rvm` intermediates (versioned in git).
- `src/main/resources/generic/` — **118** `.mop` specs (`FSM*.mop`, generic Java API usage patterns).
- `src/main/resources/generic_new/` — **27** `.mop` specs (e.g. `Closeable_MeaninglessClose.mop`, `TreeMap_Comparable.mop`) + `MultiSpec_1MonitorAspect.aj`.
- Total: **168 `.mop` files** (23+118+27).
- `src/main/resources/aspect/` — contains **only `Coverage.aj`** (method-coverage AspectJ aspect; excludes `java/javax/android/androidx/kotlin` packages). There is **no `logging.aj`**.

Spec anatomy: `event` blocks (`call`/`args`/`target`/`condition`) update `ExecutionContext` (singleton, `rvsec-core`) with `Property` enum values; an `ere`/`fsm` block defines the property automaton; `@fail`/`@match` handlers report through `ErrorCollector`/`ErrorDescription` (also `rvsec-core`).

## Relationships
- ⟶ `rv-android/modules/rv-monitor-generator` (Python) — picks **one** spec set (`jca` OR `generic` OR `generic_new`) plus `aspect/Coverage.aj` per run; sets are never mixed in a single experiment.
- ⟶ `rvsec-agent` (`mop-maven-plugin` reads `jca/*.mop` directly, see its `pom.xml` `pathToMopFiles`).
- ⟶ `rvsec-mop-extractor` (parses `.mop` for API-surface extraction).
- ⟶ `rvsec-gator`/GATOR reachability (via `mop-extractor` method list) — used to compute reachability targets.
- ⟶ `rv-experiment`, `rv-static-analysis`, `scripts/check_no_legacy_mop.py` (all Python, `rv-android/`).

## Build
Plain resources jar: `mvn clean install` (no compiled classes; `rvsec-mop-0.9.1-SNAPSHOT.jar` just bundles the resources).

## Gotchas / README corrections
- ⚠ `README.md` is **stale**: claims "336 `.mop` files" and path `src/main/mop` — actual is **168** files under `src/main/resources`.
- ⚠ README's example spec `Cipher_Encrypt.mop` **does not exist**; the real Cipher spec is `jca/CipherSpec.mop`.
- Never mix spec sets in one experiment — one set (jca/generic/generic_new) is selected per run.
- Terminology: call this layer "monitored operations" — never "security" (per project convention).
