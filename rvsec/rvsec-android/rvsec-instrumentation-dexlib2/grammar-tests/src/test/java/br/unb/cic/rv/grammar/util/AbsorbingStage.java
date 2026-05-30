package br.unb.cic.rv.grammar.util;

/**
 * The closed set of upstream pipeline stages that may absorb an AspectJ construction before it
 * reaches the dexlib2 instrumenter, per the {@code Requirement: Upstream Absorption Verdict} in
 * {@code specs/instrumentation/spec.md}. Used by NOT-NEEDED β assertion tests to name the absorber
 * (INV-INS-96): a path-β row's assertion test declares its absorber via a static field of this type.
 */
public enum AbsorbingStage {

    /** JavaMOP compiler folds the source construction into emitted runtime-monitor dispatch
     *  (e.g. {@code condition(...)}, {@code __STATICSIG}) before the {@code .aj} is produced. */
    JAVA_MOP_COMPILER,

    /** The dexlib2 {@code coverage-weaver} module emits the Coverage instrumentation directly,
     *  absorbing the {@code Coverage.aj} consumer (e.g. positive {@code execution()}/{@code within()},
     *  the {@code org.aspectj.lang.JoinPoint} runtime linkage). */
    COVERAGE_WEAVER,

    /** The generated {@code *RuntimeMonitor} dispatch loop consumes the construction at runtime. */
    MONITOR_RUNTIME_DISPATCH_LOOP,

    /** {@code DescriptorReader} flattens the construction into the {@code AspectDescriptor} JSON
     *  (e.g. {@code aspect Foo {…}} / named-pointcut declarations resolved at descriptor-emit time). */
    DESCRIPTOR_READER,

    /** The dexlib2 inline-call emission model makes the construction vacuously satisfied
     *  (e.g. {@code !adviceexecution()} — no synthetic advice methods are emitted). */
    DEXLIB2_INLINE_EMISSION_MODEL
}
