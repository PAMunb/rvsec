package br.unb.cic.rv.pointcut;

import com.android.tools.smali.dexlib2.AccessFlags;
import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.Method;
import com.android.tools.smali.dexlib2.iface.instruction.Instruction;
import com.android.tools.smali.dexlib2.immutable.ImmutableClassDef;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethod;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethodImplementation;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction10x;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction35c;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableMethodReference;

import org.junit.jupiter.api.Test;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Unit tests that cover matcher logic which does not require a live dexlib2
 * fixture. Full call-site matching is covered by {@code dex-mutator}
 * integration tests (task 5.8/5.9) where real APK inputs are available.
 *
 * <p>gh61 Group B adds coverage for {@code CombinedPC.AND/OR} short-circuit
 * semantics, {@code NotWithinPC} class-FQN filtering, and the JCA base-aspect
 * platform-namespace filter that chains three {@code NotWithinPC} via AND.
 */
class PointcutMatcherTest {

    private static final String APP_OWNER = "Lcom/example/app/MyService;";
    private static final String PLATFORM_OWNER = "Lsun/security/ssl/SSLContextImpl;";
    private static final String STRING_DESC = "Ljava/lang/String;";

    // ------------------------------------------------------------------
    // Existing pre-gh61 coverage — kept verbatim.
    // ------------------------------------------------------------------

    @Test
    void typePatternMatchesExactName() {
        assertTrue(PointcutMatcher.matchesTypePattern("com.example.Foo", "com.example.Foo"));
        assertFalse(PointcutMatcher.matchesTypePattern("com.example.Foo", "com.example.Bar"));
    }

    @Test
    void typePatternDotDotStarIsPackageWildcard() {
        assertTrue(PointcutMatcher.matchesTypePattern("com.example.Foo", "com.example..*"));
        assertTrue(PointcutMatcher.matchesTypePattern("com.example.sub.Foo", "com.example..*"));
        assertFalse(PointcutMatcher.matchesTypePattern("com.other.Foo", "com.example..*"));
    }

    @Test
    void typePatternSingleDotStarIsSinglePackage() {
        // "com.example.*" matches direct children only — not sub-packages.
        assertTrue(PointcutMatcher.matchesTypePattern("com.example.Foo", "com.example.*"));
        assertFalse(PointcutMatcher.matchesTypePattern("com.example.sub.Foo", "com.example.*"));
    }

    @Test
    void typePatternTrailingPlusIsStripped() {
        // At the matcher level, T+ patterns are validated against the bare type.
        // The "+" prefix is consumed elsewhere (InheritanceResolver.isAssignableFrom).
        assertTrue(PointcutMatcher.matchesTypePattern("com.example.Foo", "com.example.Foo+"));
    }

    @Test
    void inheritanceResolverDegradesOnMissingClass() {
        // Smoke test — construct against a missing android.jar and empty APK set.
        AndroidClassIndex android = new AndroidClassIndex(Path.of("/tmp/nope.jar"));
        InheritanceResolver resolver = new InheritanceResolver(android, List.of());
        // Even with empty state, exact match must work.
        assertTrue(resolver.isAssignableFrom("java.lang.Object", "com.example.Foo"));
        assertTrue(resolver.isAssignableFrom("com.example.Foo", "com.example.Foo"));
        // Unknown relationship returns false rather than throwing.
        assertFalse(resolver.isAssignableFrom("com.example.Bar", "com.example.Foo"));
    }

    // ------------------------------------------------------------------
    // gh61 Group B helpers — synthetic ClassDef + invoke-static call site.
    // ------------------------------------------------------------------

    /**
     * Build a 1-method synthetic class whose only instruction is
     * {@code invoke-static {v0, v1}, callee.name(I, Ljava/lang/String;)V}.
     * The class FQN is {@code declaringClassDesc} so {@code NotWithinPC}
     * tests can target it.
     */
    private static Fixture buildCallSiteFixture(String declaringClassDesc) {
        ImmutableMethodReference calleeRef = new ImmutableMethodReference(
                "Ljava/lang/String;", "valueOf",
                List.of("I"),
                STRING_DESC);
        List<com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction> body =
                new ArrayList<>();
        body.add(new ImmutableInstruction35c(
                Opcode.INVOKE_STATIC, /*regCount=*/ 1,
                /*c=*/ 0, /*d=*/ 0, /*e=*/ 0, /*f=*/ 0, /*g=*/ 0,
                calleeRef));
        body.add(new ImmutableInstruction10x(Opcode.RETURN_VOID));

        ImmutableMethodImplementation impl = new ImmutableMethodImplementation(
                /*registerCount=*/ 2,
                body,
                Collections.emptyList(),
                Collections.emptyList());
        ImmutableMethod m = new ImmutableMethod(
                declaringClassDesc, "doStuff",
                Collections.emptyList(),
                "V",
                AccessFlags.PUBLIC.getValue() | AccessFlags.STATIC.getValue(),
                null, null, impl);
        ClassDef cd = new ImmutableClassDef(
                declaringClassDesc, AccessFlags.PUBLIC.getValue(),
                "Ljava/lang/Object;",
                Collections.emptyList(),
                null, null,
                Collections.emptyList(),
                List.of(m));
        List<Instruction> instructions = new ArrayList<>(body);
        return new Fixture(cd, m, instructions.get(0), instructions);
    }

    private static List<CallPC.ParamSpec> exactSpecs(String... descriptors) {
        List<CallPC.ParamSpec> out = new java.util.ArrayList<>(descriptors.length);
        for (String d : descriptors) out.add(new CallPC.ParamSpec(d, false));
        return out;
    }

    /** A {@code CallPC} that matches the {@code String.valueOf(int)} call site
     *  produced by {@link #buildCallSiteFixture(String)}. */
    private static CallPC valueOfPc() {
        return new CallPC(/*isConstructor*/ false,
                /*returnType*/ "String",
                /*declaringType*/ "java.lang.String",
                /*methodName*/ "valueOf",
                exactSpecs("int"),
                /*varargs*/ false);
    }

    /** A {@code CallPC} that does NOT match the call site (different name). */
    private static CallPC neverMatchesPc() {
        return new CallPC(/*isConstructor*/ false,
                /*returnType*/ "String",
                /*declaringType*/ "java.lang.String",
                /*methodName*/ "noSuchMethod",
                exactSpecs("int"),
                /*varargs*/ false);
    }

    /** A {@code CallPC} that would NPE if its {@code matchCall} body were
     *  ever entered — {@code declaringType} is null, so the first call to
     *  {@code typeResolver.toDescriptor(cp.declaringType())} in
     *  {@code PointcutMatcher.matchCall:153} throws. Used to assert that
     *  OR short-circuits past an already-matched left side. */
    private static CallPC bombPc() {
        return new CallPC(/*isConstructor*/ false,
                /*returnType*/ "String",
                /*declaringType*/ null,
                /*methodName*/ "valueOf",
                exactSpecs("int"),
                /*varargs*/ false);
    }

    private static PointcutMatcher newMatcher() {
        TypeResolver tr = new TypeResolver(List.of());
        InheritanceResolver ir = new InheritanceResolver(
                new AndroidClassIndex(Path.of("/tmp/nope.jar")), List.of());
        return new PointcutMatcher(tr, ir);
    }

    private static Optional<Match> match(PointcutMatcher pm, PointcutExpression pe, Fixture f) {
        return pm.match(pe, f.classDef, f.method, f.instruction,
                /*instructionIndex*/ 0, /*totalInstructions*/ f.instructions.size(),
                f.instructions);
    }

    private static final class Fixture {
        final ClassDef classDef;
        final Method method;
        final Instruction instruction;
        final List<Instruction> instructions;

        Fixture(ClassDef cd, Method m, Instruction ins, List<Instruction> all) {
            this.classDef = cd;
            this.method = m;
            this.instruction = ins;
            this.instructions = all;
        }
    }

    // ------------------------------------------------------------------
    // Task 1.2 — CombinedPC.AND
    // ------------------------------------------------------------------

    @Test
    void combinedAndIntersectsMatches() {
        // Both sides match: CallPC (produces argBindings) AND NotWithinPC
        // (matches because the class is NOT under sun..*). Merge MUST retain
        // the CallPC's argBindings.
        PointcutMatcher pm = newMatcher();
        Fixture f = buildCallSiteFixture(APP_OWNER);

        CombinedPC bothMatch = new CombinedPC(CombinedPC.Op.AND,
                valueOfPc(), new NotWithinPC("sun..*"));
        Optional<Match> r = match(pm, bothMatch, f);
        assertTrue(r.isPresent(), "AND with two matching children MUST succeed");
        assertEquals(0, r.get().argBindings.get("arg00"),
                "merged Match retains CallPC's arg00 binding (regs[0]=0)");

        // Right child fails: CallPC matches but NotWithinPC excludes the class.
        CombinedPC rightFails = new CombinedPC(CombinedPC.Op.AND,
                valueOfPc(), new NotWithinPC("com.example..*"));
        assertTrue(match(pm, rightFails, f).isEmpty(),
                "AND with right child failing MUST yield Optional.empty()");

        // Left child fails: CallPC mis-matches; AND short-circuits.
        CombinedPC leftFails = new CombinedPC(CombinedPC.Op.AND,
                neverMatchesPc(), new NotWithinPC("sun..*"));
        assertTrue(match(pm, leftFails, f).isEmpty(),
                "AND with left child failing MUST yield Optional.empty()");
    }

    // ------------------------------------------------------------------
    // Task 1.3 — CombinedPC.OR short-circuit semantics
    // ------------------------------------------------------------------

    @Test
    void combinedOrShortCircuitsOnLeftMatch() {
        // Left matches → right MUST NOT be evaluated. The bomb on the right
        // would NPE inside matchCall (declaringType=null) if reached.
        PointcutMatcher pm = newMatcher();
        Fixture f = buildCallSiteFixture(APP_OWNER);

        CombinedPC leftWins = new CombinedPC(CombinedPC.Op.OR,
                valueOfPc(), bombPc());
        Optional<Match> r = match(pm, leftWins, f);
        assertTrue(r.isPresent(), "OR with matching left MUST succeed without evaluating right");
        // Result is left's match — argBindings present.
        assertEquals(0, r.get().argBindings.get("arg00"),
                "OR returns left's Match when left matches");
    }

    @Test
    void combinedOrFallsThroughToRight() {
        PointcutMatcher pm = newMatcher();
        Fixture f = buildCallSiteFixture(APP_OWNER);

        // Left does not match; right does. Result is right's.
        CombinedPC rightWins = new CombinedPC(CombinedPC.Op.OR,
                neverMatchesPc(), valueOfPc());
        Optional<Match> r = match(pm, rightWins, f);
        assertTrue(r.isPresent(), "OR with non-matching left MUST evaluate right");
        assertEquals(0, r.get().argBindings.get("arg00"));
    }

    @Test
    void combinedOrReturnsEmptyWhenNeitherMatches() {
        PointcutMatcher pm = newMatcher();
        Fixture f = buildCallSiteFixture(APP_OWNER);

        CombinedPC neither = new CombinedPC(CombinedPC.Op.OR,
                neverMatchesPc(), neverMatchesPc());
        assertTrue(match(pm, neither, f).isEmpty(),
                "OR with no matching child MUST yield Optional.empty()");
    }

    // ------------------------------------------------------------------
    // Task 1.4 — NotWithinPC standalone
    // ------------------------------------------------------------------

    @Test
    void notWithinExcludesMatchingClassFqn() {
        PointcutMatcher pm = newMatcher();
        Fixture platform = buildCallSiteFixture(PLATFORM_OWNER);

        NotWithinPC excludesSun = new NotWithinPC("sun..*");
        assertTrue(match(pm, excludesSun, platform).isEmpty(),
                "NotWithinPC MUST exclude classes whose FQN prefix-matches the pattern");
    }

    @Test
    void notWithinAllowsNonMatchingClassFqn() {
        PointcutMatcher pm = newMatcher();
        Fixture app = buildCallSiteFixture(APP_OWNER);

        NotWithinPC excludesSun = new NotWithinPC("sun..*");
        Optional<Match> r = match(pm, excludesSun, app);
        assertTrue(r.isPresent(),
                "NotWithinPC MUST allow classes whose FQN does not match the pattern");
        assertNotNull(r.get());
    }

    // ------------------------------------------------------------------
    // Task 1.5 — JCA base-aspect filter: chain three NotWithinPC via AND.
    // ------------------------------------------------------------------

    // ------------------------------------------------------------------
    // gh61 Group C — Object+ subtype operator in call(...) parameters.
    // ------------------------------------------------------------------

    /**
     * Build a call-site fixture whose only instruction is
     * {@code invoke-static {v0, v1}, javax/crypto/Cipher.getInstance(<params>)}
     * with the given DEX descriptors for the params and a
     * {@code Ljavax/crypto/Cipher;} return type. The class is rooted under
     * {@code com.example.app} so it survives the base-aspect filter; the
     * resolver/inheritance fixture below uses real FQNs.
     */
    private static Fixture cipherGetInstanceFixture(List<String> paramDescriptors) {
        ImmutableMethodReference calleeRef = new ImmutableMethodReference(
                "Ljavax/crypto/Cipher;", "getInstance",
                paramDescriptors,
                "Ljavax/crypto/Cipher;");
        List<com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction> body =
                new java.util.ArrayList<>();
        body.add(new ImmutableInstruction35c(
                Opcode.INVOKE_STATIC, /*regCount=*/ paramDescriptors.size(),
                /*c=*/ 0, /*d=*/ 1, /*e=*/ 0, /*f=*/ 0, /*g=*/ 0,
                calleeRef));
        body.add(new ImmutableInstruction10x(Opcode.RETURN_VOID));

        ImmutableMethodImplementation impl = new ImmutableMethodImplementation(
                /*registerCount=*/ 2,
                body,
                Collections.emptyList(),
                Collections.emptyList());
        ImmutableMethod m = new ImmutableMethod(
                APP_OWNER, "useCipher",
                Collections.emptyList(),
                "V",
                AccessFlags.PUBLIC.getValue() | AccessFlags.STATIC.getValue(),
                null, null, impl);
        ClassDef cd = new ImmutableClassDef(
                APP_OWNER, AccessFlags.PUBLIC.getValue(),
                "Ljava/lang/Object;",
                Collections.emptyList(),
                null, null,
                Collections.emptyList(),
                List.of(m));
        List<Instruction> instructions = new java.util.ArrayList<>(body);
        return new Fixture(cd, m, instructions.get(0), instructions);
    }

    /** call(public static Cipher Cipher.getInstance(String, Object+)) — with
     *  the subtype operator on the second param. */
    private static CallPC cipherGetInstanceStringObjectPlusPc() {
        return new CallPC(/*isConstructor*/ false,
                /*returnType*/ "Cipher",
                /*declaringType*/ "javax.crypto.Cipher",
                /*methodName*/ "getInstance",
                List.of(new CallPC.ParamSpec("String", false),
                        new CallPC.ParamSpec("Object", true)),
                /*varargs*/ false);
    }

    /** call(public static Cipher Cipher.getInstance(String)) — exact match,
     *  no subtype operator. */
    private static CallPC cipherGetInstanceStringPc() {
        return new CallPC(/*isConstructor*/ false,
                "Cipher", "javax.crypto.Cipher", "getInstance",
                List.of(new CallPC.ParamSpec("String", false)),
                /*varargs*/ false);
    }

    /** Resolver pre-loaded with the imports needed for the Cipher fixtures. */
    private static PointcutMatcher cipherMatcher() {
        TypeResolver tr = new TypeResolver(List.of(
                "javax.crypto.Cipher", "java.lang.String", "java.lang.Object"));
        // The fixture uses the InheritanceResolver's Object fast-path
        // (InheritanceResolver.java:66) for the positive case. No APK dex
        // is supplied — the fast-path returns true for any non-primitive
        // FQN, including Provider, without needing an Android index.
        InheritanceResolver ir = new InheritanceResolver(
                new AndroidClassIndex(Path.of("/tmp/nope.jar")), List.of());
        return new PointcutMatcher(tr, ir);
    }

    @Test
    void callParamSubtypeMarkerMatchesSubclass() {
        // call(... getInstance(String, Object+)) against
        // invoke-static getInstance(String, Provider): Object+ MUST match
        // Provider through InheritanceResolver's Object fast-path.
        PointcutMatcher pm = cipherMatcher();
        Fixture f = cipherGetInstanceFixture(
                List.of("Ljava/lang/String;", "Ljava/security/Provider;"));
        Optional<Match> r = match(pm, cipherGetInstanceStringObjectPlusPc(), f);
        assertTrue(r.isPresent(),
                "Object+ MUST match Provider (subtype of Object) — INV-INS-86");
    }

    @Test
    void callParamSubtypeMarkerRejectsPrimitive() {
        // call(... getInstance(String, Object+)) against
        // invoke-static getInstance(String, I): Object+ MUST reject the
        // primitive int. Without the gh61 fromDescriptor primitive
        // mapping, InheritanceResolver's Object fast-path would compute
        // !isPrimitive("I")=true and incorrectly accept.
        PointcutMatcher pm = cipherMatcher();
        Fixture f = cipherGetInstanceFixture(
                List.of("Ljava/lang/String;", "I"));
        assertTrue(match(pm, cipherGetInstanceStringObjectPlusPc(), f).isEmpty(),
                "Object+ MUST NOT match primitive int — INV-INS-86 (fromDescriptor primitive guard)");
    }

    @Test
    void callParamExactMatchPreservedWithoutPlus() {
        // call(... getInstance(String)) against
        // invoke-static getInstance(CharSequence): exact match MUST fail.
        PointcutMatcher pm = cipherMatcher();
        Fixture f = cipherGetInstanceFixture(
                List.of("Ljava/lang/CharSequence;"));
        assertTrue(match(pm, cipherGetInstanceStringPc(), f).isEmpty(),
                "exact-match param MUST fail when descriptors differ "
                        + "(no implicit widening to CharSequence) — INV-INS-86 negative case");
    }

    @Test
    void baseAspectFilterExcludesPlatformNamespaces() {
        PointcutMatcher pm = newMatcher();

        // !within(sun..*) && !within(java..*) && !within(javax..*) — left-
        // associative: ((!sun) && (!java)) && (!javax).
        PointcutExpression baseAspect = new CombinedPC(CombinedPC.Op.AND,
                new CombinedPC(CombinedPC.Op.AND,
                        new NotWithinPC("sun..*"),
                        new NotWithinPC("java..*")),
                new NotWithinPC("javax..*"));

        // App class matches the call site AND survives the base-aspect filter.
        // Compose with the CallPC so the result carries argBindings.
        PointcutExpression appExpr = new CombinedPC(CombinedPC.Op.AND, baseAspect, valueOfPc());
        Optional<Match> appResult = match(pm, appExpr, buildCallSiteFixture(APP_OWNER));
        assertTrue(appResult.isPresent(),
                "app class MUST survive the base-aspect platform-namespace filter");
        assertEquals(0, appResult.get().argBindings.get("arg00"),
                "argBindings MUST be preserved through CombinedPC merge with the filter");

        // Platform class is rejected by the filter.
        Optional<Match> platformResult = match(pm, appExpr, buildCallSiteFixture(PLATFORM_OWNER));
        assertTrue(platformResult.isEmpty(),
                "platform class (sun..*) MUST be rejected by the base-aspect filter");
    }
}
