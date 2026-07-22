package br.unb.cic.rv.pointcut;

import com.android.tools.smali.dexlib2.AccessFlags;
import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.dexbacked.DexBackedClassDef;
import com.android.tools.smali.dexlib2.dexbacked.DexBackedDexFile;
import com.android.tools.smali.dexlib2.dexbacked.DexBackedMethod;
import com.android.tools.smali.dexlib2.iface.Annotation;
import com.android.tools.smali.dexlib2.iface.AnnotationElement;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.DexFile;
import com.android.tools.smali.dexlib2.iface.Method;
import com.android.tools.smali.dexlib2.iface.value.EncodedValue;
import com.android.tools.smali.dexlib2.immutable.ImmutableAnnotation;
import com.android.tools.smali.dexlib2.immutable.ImmutableAnnotationElement;
import com.android.tools.smali.dexlib2.immutable.ImmutableClassDef;
import com.android.tools.smali.dexlib2.immutable.ImmutableDexFile;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethod;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethodParameter;
import com.android.tools.smali.dexlib2.immutable.value.ImmutableArrayEncodedValue;
import com.android.tools.smali.dexlib2.immutable.value.ImmutableStringEncodedValue;
import com.android.tools.smali.dexlib2.writer.pool.DexPool;
import org.junit.jupiter.api.Test;

import java.io.BufferedInputStream;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Covers {@link CpsDetector}, the Kotlin coroutine state-machine recogniser used
 * by {@code PointcutMatcher} for CPS-aware pointcut lowering (INV-INS-61). The
 * class had no dedicated test (≈12% branch coverage), so every superclass case,
 * both annotation walks ({@code @DebugMetadata.m} / {@code .c}), the
 * generated-suffix heuristic, and the {@code invokeSuspend} signature probe were
 * dark.
 *
 * <p>Detection drives whether a suspend-fun pointcut is redirected onto the
 * synthetic {@code invokeSuspend} body: a false negative silently drops
 * monitoring of every coroutine, a false positive lowers an ordinary class into
 * a body that does not exist. The scenarios below pin each recognised shape and,
 * for every heuristic, a near-miss control that must NOT be recognised.
 */
class CpsDetectorTest {

    private static final String DEBUG_METADATA = "Lkotlin/coroutines/jvm/internal/DebugMetadata;";

    // --- fixture builders -------------------------------------------------

    private static ClassDef classDef(String type, String superclass, List<Annotation> anns) {
        return new ImmutableClassDef(
                type, 0, superclass, null, null, anns,
                Collections.emptyList(), Collections.emptyList());
    }

    private static Annotation debugMetadata(AnnotationElement... elements) {
        return new ImmutableAnnotation(0, DEBUG_METADATA, Arrays.asList(elements));
    }

    private static AnnotationElement element(String name, EncodedValue value) {
        return new ImmutableAnnotationElement(name, value);
    }

    /**
     * Build a single abstract method inside a synthetic class, serialise it to a
     * temp .dex, and parse it back as a {@link DexBackedMethod}. The round-trip is
     * required because {@code CpsDetector.isInvokeSuspend} compares parameter
     * types with {@code String.equals}: a raw {@code ImmutableMethod} exposes its
     * parameter types as {@code ImmutableMethodParameter} (a CharSequence, not a
     * String) so the equality would spuriously fail, whereas a DexBacked method —
     * exactly what production feeds the detector — yields real String descriptors.
     */
    private static Method dexBackedMethod(String name, String returnType, String... paramTypes)
            throws Exception {
        List<ImmutableMethodParameter> params = new java.util.ArrayList<>();
        for (String p : paramTypes) params.add(new ImmutableMethodParameter(p, null, null));
        int flags = AccessFlags.PUBLIC.getValue() | AccessFlags.ABSTRACT.getValue();
        ImmutableMethod m = new ImmutableMethod("LOwner$1;", name, params, returnType, flags,
                null, null, null);
        ClassDef cd = new ImmutableClassDef("LOwner$1;",
                AccessFlags.PUBLIC.getValue() | AccessFlags.ABSTRACT.getValue(),
                "Ljava/lang/Object;", null, null, null,
                Collections.emptyList(), List.of(m));
        DexFile file = new ImmutableDexFile(Opcodes.getDefault(), List.of(cd));
        Path tmp = Files.createTempFile("cps-method-", ".dex");
        try {
            DexPool.writeTo(tmp.toString(), file);
            try (InputStream in = new BufferedInputStream(Files.newInputStream(tmp))) {
                DexBackedDexFile parsed = DexBackedDexFile.fromInputStream(Opcodes.getDefault(), in);
                for (DexBackedClassDef c : parsed.getClasses()) {
                    for (DexBackedMethod dm : c.getMethods()) {
                        if (name.equals(dm.getName())) return dm;
                    }
                }
                throw new AssertionError("method " + name + " not found in parsed dex");
            }
        } finally {
            Files.deleteIfExists(tmp);
        }
    }

    // --- isStateMachine: superclass switch --------------------------------

    @Test
    void recognisesEachKnownContinuationSuperclass() {
        // All five recognised coroutine base classes must classify as state
        // machines regardless of annotations/name.
        for (String sup : List.of(
                "Lkotlin/coroutines/jvm/internal/ContinuationImpl;",
                "Lkotlin/coroutines/jvm/internal/BaseContinuationImpl;",
                "Lkotlin/coroutines/jvm/internal/SuspendLambda;",
                "Lkotlin/coroutines/jvm/internal/RestrictedSuspendLambda;",
                "Lkotlin/coroutines/jvm/internal/RestrictedContinuationImpl;")) {
            assertTrue(CpsDetector.isStateMachine(classDef("LFoo;", sup, Collections.emptyList())),
                    "superclass " + sup + " must be recognised as a coroutine state machine");
        }
    }

    @Test
    void nullSuperclassIsNotStateMachine() {
        // Interfaces (e.g. the class model for an annotation) have a null
        // superclass — must short-circuit to false without NPE.
        assertFalse(CpsDetector.isStateMachine(classDef("LFoo;", null, Collections.emptyList())));
    }

    @Test
    void unrelatedSuperclassWithoutMetadataOrSuffixIsNotStateMachine() {
        assertFalse(CpsDetector.isStateMachine(
                classDef("LFoo;", "Ljava/lang/Object;", Collections.emptyList())));
    }

    @Test
    void debugMetadataAnnotationAloneMakesStateMachine() {
        // A plain-Object superclass but a @DebugMetadata annotation → recognised
        // via the annotation heuristic.
        assertTrue(CpsDetector.isStateMachine(
                classDef("LFoo;", "Ljava/lang/Object;", List.of(debugMetadata()))));
    }

    @Test
    void generatedSuffixMakesStateMachine() {
        // Compiler-generated inline-lambda name shape Outer$name$1 with an
        // all-digit tail and no metadata → recognised via the suffix heuristic.
        assertTrue(CpsDetector.isStateMachine(
                classDef("Lcom/example/Foo$bar$1;", "Ljava/lang/Object;", Collections.emptyList())));
    }

    @Test
    void generatedSuffixHeuristicRejectsNonDigitAndMissingDollarTails() {
        // Near-miss controls for hasGeneratedSuffix: a named inner class (tail
        // has letters), a dollar-less name, and an empty tail ("Foo$;") must all
        // be rejected so an ordinary class is never lowered onto invokeSuspend.
        assertFalse(CpsDetector.isStateMachine(
                classDef("Lcom/example/Foo$Bar;", "Ljava/lang/Object;", Collections.emptyList())),
                "named inner class (non-digit tail) is not a generated state machine");
        assertFalse(CpsDetector.isStateMachine(
                classDef("Lcom/example/Foo;", "Ljava/lang/Object;", Collections.emptyList())),
                "a dollar-less class name has no generated suffix");
        assertFalse(CpsDetector.isStateMachine(
                classDef("Lcom/example/Foo$;", "Ljava/lang/Object;", Collections.emptyList())),
                "an empty tail after '$' is not a digit suffix");
    }

    // --- enclosingSuspendFun ----------------------------------------------

    @Test
    void enclosingSuspendFunReadsMElement() {
        ClassDef cd = classDef("LFoo$1;", "Ljava/lang/Object;",
                List.of(debugMetadata(element("m", new ImmutableStringEncodedValue("doWork")))));
        assertEquals("doWork", CpsDetector.enclosingSuspendFun(cd));
    }

    @Test
    void enclosingSuspendFunNullWhenNoDebugMetadata() {
        // No @DebugMetadata at all → null (the matcher falls back to naming).
        // Positive control: the m-carrying class above returns non-null, so this
        // null is the missing-annotation path, not a broken parse.
        assertNull(CpsDetector.enclosingSuspendFun(
                classDef("LFoo$1;", "Ljava/lang/Object;", Collections.emptyList())));
    }

    @Test
    void enclosingSuspendFunSkipsForeignAnnotationsAndMissingMElement() {
        // A non-DebugMetadata annotation is skipped, and a DebugMetadata with
        // only a "c" element (no "m") yields null — exercises both the
        // annotation-type filter and the element-name filter.
        Annotation foreign = new ImmutableAnnotation(0, "Lkotlin/Metadata;",
                List.of(element("m", new ImmutableStringEncodedValue("ignored"))));
        ClassDef cd = classDef("LFoo$1;", "Ljava/lang/Object;",
                List.of(foreign,
                        debugMetadata(element("c", new ImmutableStringEncodedValue("Lcom/example/Src;")))));
        assertNull(CpsDetector.enclosingSuspendFun(cd));
    }

    // --- debugMetadataOwner -----------------------------------------------

    @Test
    void debugMetadataOwnerReadsStringCElement() {
        ClassDef cd = classDef("LFoo$1;", "Ljava/lang/Object;",
                List.of(debugMetadata(element("c", new ImmutableStringEncodedValue("Lcom/example/Src;")))));
        assertEquals("Lcom/example/Src;", CpsDetector.debugMetadataOwner(cd));
    }

    @Test
    void debugMetadataOwnerReadsFirstStringOfArrayCElement() {
        // Older kotlinc emits "c" as an array of strings — the detector takes the
        // first string element.
        EncodedValue array = new ImmutableArrayEncodedValue(List.of(
                new ImmutableStringEncodedValue("Lcom/example/First;"),
                new ImmutableStringEncodedValue("Lcom/example/Second;")));
        ClassDef cd = classDef("LFoo$1;", "Ljava/lang/Object;",
                List.of(debugMetadata(element("c", array))));
        assertEquals("Lcom/example/First;", CpsDetector.debugMetadataOwner(cd));
    }

    @Test
    void debugMetadataOwnerNullWhenAbsent() {
        assertNull(CpsDetector.debugMetadataOwner(
                classDef("LFoo$1;", "Ljava/lang/Object;", Collections.emptyList())));
    }

    // --- isInvokeSuspend --------------------------------------------------

    @Test
    void isInvokeSuspendTrueForCanonicalSignature() throws Exception {
        assertTrue(CpsDetector.isInvokeSuspend(
                dexBackedMethod("invokeSuspend", "Ljava/lang/Object;", "Ljava/lang/Object;")));
    }

    @Test
    void isInvokeSuspendRejectsWrongNameArityAndParamType() throws Exception {
        // Three distinct near-misses: wrong name, wrong arity (2 params), wrong
        // single-param type. Each must be false so only the real CPS entry point
        // is redirected.
        assertFalse(CpsDetector.isInvokeSuspend(
                dexBackedMethod("invoke", "Ljava/lang/Object;", "Ljava/lang/Object;")),
                "a differently-named method is not the CPS entry");
        assertFalse(CpsDetector.isInvokeSuspend(
                dexBackedMethod("invokeSuspend", "Ljava/lang/Object;",
                        "Ljava/lang/Object;", "Ljava/lang/Throwable;")),
                "the state-machine entry we lower onto takes exactly one Object param");
        assertFalse(CpsDetector.isInvokeSuspend(
                dexBackedMethod("invokeSuspend", "Ljava/lang/Object;", "Ljava/lang/String;")),
                "the single param must be java.lang.Object");
    }
}
