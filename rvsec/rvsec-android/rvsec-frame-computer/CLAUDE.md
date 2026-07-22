# CLAUDE.md - rvsec-frame-computer

## Purpose

Standalone ASM CLI that recomputes JVM stack-map frames (`ClassWriter.COMPUTE_FRAMES`)
for all `.class` files in a directory, fixing frames the ajc/BCEL weaver leaves corrupted
for modern bytecode (try-with-resources, lambdas, switch expressions) — avoiding an
`ArrayIndexOutOfBoundsException` in Android's `d8` compiler downstream.

## Role in pipeline

Runs as a post-weaving repair step for the **ajc instrumentation variant** only: after
ajc weaves the JavaMOP aspects into the app's `.class` files and before `d8` converts
them to DEX.

## Relationships

- ⟶ `rv-android/modules/rv-instrumentation-ajc` (Python): invokes the packaged
  `rv-frame-computer.jar` as a subprocess between weaving and `d8`. Not used by the
  dexlib2 instrumentation path (that variant operates on DEX bytecode directly, no ajc/BCEL step).

## Dependencies

- Internal: none.
- External: `org.ow2.asm:asm:9.7.1` (pinned in this module's own `pom.xml`, not the
  parent's managed dependency set).

## Key component

| Component | File | Purpose |
|---|---|---|
| `FrameComputer` | `src/main/java/br/unb/cic/rvsec/frame/FrameComputer.java` | `main(classDir [--classpath cp])` walks `classDir`, rewrites each `.class` with recomputed frames; inner `FrameComputingClassWriter` resolves the type hierarchy via a `URLClassLoader` (`classDir` + `--classpath`) instead of the filesystem, needed because the hierarchy spans multiple jars (android.jar, aspectjrt.jar, ...) |

## Build & invocation

`maven-assembly-plugin` builds a `jar-with-dependencies` fat jar named `rv-frame-computer.jar`
(main class `br.unb.cic.rvsec.frame.FrameComputer`); `maven-resources-plugin` copies it to
`${main.basedir}/rv-android/lib/frame-computer/` on the `install` phase — same
`main.basedir` caveat as `rvsec-apk` (only resolved by the root reactor).

## Gotchas / README corrections

- `processClassFile` catches `Throwable`, not `Exception`: dex2jar-produced classes can
  have illegal modifiers that raise `ClassFormatError` (an `Error`) via `Class.forName()`
  inside `getCommonSuperClass`. On any failure the original bytecode is left untouched
  (best-effort per class, `failed` counter only, no hard exit).
- `ClassReader.SKIP_FRAMES` is passed deliberately: using `ClassWriter(reader, flags)`
  would let ASM copy — and no-op-preserve — an empty/corrupted original `StackMapTable`;
  constructing `ClassWriter` without the reader forces a full recompute from scratch.
