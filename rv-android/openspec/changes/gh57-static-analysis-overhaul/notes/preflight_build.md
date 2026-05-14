# Pre-flight 1.5: JAR sync and build baseline

**Date:** 2026-05-14
**Task:** Phase-0 §16.3 / tasks.md 1.5
**Scope:** Confirm both `rvsec-analysis-client.jar` and `ape-rv.jar` build cleanly with `mvn install` (NOT `mvn package` — `install` is required so downstream consumers find the artifact in the local Maven repo). Record baseline timestamps for the change's "after" comparison.

## Build commands (canonical)

Both modules build to-completion in a few minutes on a warm `~/.m2/`. Use `mvn install`, not `mvn package`:

```bash
# rvsec-gator (Java external repo — Soot + GUI analysis client)
cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-android/rvsec-gator
mvn install -DskipTests -q

# ape (Java external repo — APE-RV monkey + MopData reader)
cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ape
mvn install -DskipTests -q
```

**Why `install` and not `package`:**
- `package` produces the artifact only in `target/`.
- `install` additionally copies it to `~/.m2/repository/...`, where:
  - The `rvsec-gator-client-0.9.0-SNAPSHOT.jar` is found by `rvsec/rvsec-android/rvsec-gator/sootandroid` and any other module that depends on it.
  - The `ape-rv-1.0.0-SNAPSHOT.jar` is found by anything that resolves the ape Maven coordinates.
- Without `install`, a downstream `mvn` build that resolves the parent's dependency tree picks up a STALE jar from the previous install (or fails to find it), causing the "build succeeds but runtime uses old code" class of bugs. Captured in user-feedback memory `feedback_mvn_install_not_package.md`.

## Baseline timestamps (pre-change snapshot, 2026-05-14T16:14:33–16:15)

| Artifact path | Size | mtime | Notes |
|---------------|------|-------|-------|
| `rvsec-gator/client/target/rvsec-analysis-client.jar` | 61 863 240 B | 2026-05-14 16:14 | Built by `mvn install` in this pre-flight |
| `~/.m2/.../rvsec-gator-client/0.9.0-SNAPSHOT/rvsec-gator-client-0.9.0-SNAPSHOT.jar` | 61 863 240 B | 2026-05-14 16:14 | Installed by same `mvn install` |
| `ape/target/ape-rv.jar` | 236 967 B | 2026-05-14 16:15 | Built by `mvn install` in this pre-flight |
| `ape/target/ape-rv-classes.jar` | 585 496 B | 2026-05-14 16:15 | Built by same `mvn install` |
| `~/.m2/.../ape-rv/1.0.0-SNAPSHOT/ape-rv-1.0.0-SNAPSHOT.jar` | – | 2026-05-14 16:15 | Installed by same `mvn install` |
| `ape/ape.jar` (deploy file) | 199 596 B | **2026-03-13 09:51** | ⚠️ STALE — see below |

## Caveat: `ape/ape.jar` is the device-side deployable and is NOT refreshed by `mvn install`

`ape/install.py` pushes `ape/ape.jar` (not the freshly-built `ape/target/ape-rv.jar`) to `/data/local/tmp/` on the device. The root-level `ape.jar` is older (March 2026) than the just-built `target/ape-rv.jar` (May 14, 2026).

**Implication for Group 7 (schema bump + MopData reader update):** the implementer MUST copy `ape/target/ape-rv.jar` → `ape/ape.jar` after rebuilding, otherwise `install.py` keeps deploying the stale binary and the schema-version reader changes never reach the device. This step is missing from `tasks.md` 7.7 as currently written; will surface it in the task list before Group 7 starts.

```bash
# Step that Group 7 must add (preferably automated by the eventual deploy script):
cp /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ape/target/ape-rv.jar \
   /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ape/ape.jar
```

There is no equivalent caveat for the gator JAR — `rv-static-analysis` consumes the JAR via the path `rvsec-gator/client/target/rvsec-analysis-client.jar` directly (no rename step), so `mvn install` is sufficient.

## Build warnings noted (informative, non-blocking)

- gator build emits Maven WARNING lines about restricted JDK methods (jansi, guava `Unsafe`) — known noise from Maven 3.9.x on JDK 21+; does not affect bytecode.
- ape build emits multiple "Type … was not found, required for desugaring" warnings from the d8 step (java.lang.Cloneable, RuntimeException, IActivityController$Stub, IPackageStatsObserver, etc.). These are expected because the ape monkey targets the Android system internal API which is not in the build classpath. The resulting `ape-rv.jar` is functional on-device.

## Decision

- **Both builds pass clean.** ~/.m2 has fresh artifacts. Ready for Group 2 onwards.
- **Action item for Group 7:** add a task between 7.7 and 7.8 to `cp target/ape-rv.jar ape.jar`.
