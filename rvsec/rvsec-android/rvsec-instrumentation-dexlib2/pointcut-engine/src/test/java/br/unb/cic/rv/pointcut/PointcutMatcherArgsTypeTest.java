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
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction11n;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction3rc;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableMethodReference;

import org.junit.jupiter.api.Test;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * §4.AT — {@code args(Type)} type-matching at {@link PointcutMatcher#matchArgs}
 * (spec.md:1546). The type form constrains the matched call's DECLARED argument
 * descriptors POSITIONALLY (round-8 V-decision: declared static types, not
 * runtime instance-of), with subtype expansion via {@code isAssignableFrom}, a
 * trailing {@code ..} accept-rest, and {@code *} / binding-name positions that
 * accept any single argument.
 *
 * <p>Coverage gap this closes: {@link ArgsPC} was 36.7% instruction / 0% branch —
 * {@link ArgsPC#hasTypeConstraint()} and the whole type-form body of
 * {@code matchArgs:268-306} were dark. The binding-only always-match path was the
 * only one exercised. The arity / mismatch / wildcard assertions here are the
 * regression guards: a type-form {@code args(...)} that silently reverted to the
 * inert always-match collector would flip every negative case to a match.
 */
class PointcutMatcherArgsTypeTest {

    private static final String OWNER = "Ljava/lang/StringBuilder;";
    private static final String APP_OWNER = "Lcom/example/app/Site;";
    private static final String STRING_DESC = "Ljava/lang/String;";
    private static final String PROVIDER_DESC = "Ljava/security/Provider;";

    // ------------------------------------------------------------------
    // Fixtures — invoke-static/range with fully controlled param descriptors.
    // A static invoke has no receiver, so the register operand list equals the
    // argument list (simplest shape for arg-type matching).
    // ------------------------------------------------------------------

    /** {@code invoke-static/range {v0..vN}, OWNER.m(<params>)V}. */
    private static Fixture invokeStatic(List<String> paramDescs) {
        ImmutableMethodReference ref = new ImmutableMethodReference(
                OWNER, "append", paramDescs, "V");
        List<com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction> body =
                new ArrayList<>();
        // Instruction3rc (range) sidesteps the 5-register limit of 35c and keeps
        // the register list trivially aligned with the parameter list.
        body.add(new ImmutableInstruction3rc(
                Opcode.INVOKE_STATIC_RANGE, /*startReg=*/ 0,
                /*regCount=*/ Math.max(1, paramDescs.size()), ref));
        body.add(new ImmutableInstruction10x(Opcode.RETURN_VOID));
        return buildFixture(body, Math.max(1, paramDescs.size()));
    }

    /** A {@code const/4 v0, #0} join point — NOT a ReferenceInstruction. */
    private static Fixture nonReferenceInstruction() {
        List<com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction> body =
                new ArrayList<>();
        body.add(new ImmutableInstruction11n(Opcode.CONST_4, 0, 0));
        body.add(new ImmutableInstruction10x(Opcode.RETURN_VOID));
        return buildFixture(body, 1);
    }

    private static Fixture buildFixture(
            List<com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction> body,
            int registerCount) {
        ImmutableMethodImplementation impl = new ImmutableMethodImplementation(
                registerCount, body, Collections.emptyList(), Collections.emptyList());
        ImmutableMethod m = new ImmutableMethod(
                APP_OWNER, "site", Collections.emptyList(), "V",
                AccessFlags.PUBLIC.getValue() | AccessFlags.STATIC.getValue(),
                null, null, impl);
        ClassDef cd = new ImmutableClassDef(
                APP_OWNER, AccessFlags.PUBLIC.getValue(), "Ljava/lang/Object;",
                Collections.emptyList(), null, null, Collections.emptyList(), List.of(m));
        List<Instruction> instructions = new ArrayList<>(body);
        return new Fixture(cd, m, instructions.get(0), instructions);
    }

    /** ArgsPC in TYPE form: positions drive matching; names are irrelevant to the
     *  matcher but required by the record — reuse the positions list for names. */
    private static ArgsPC argsType(String... positions) {
        List<String> names = new ArrayList<>();
        for (String p : positions) if (p != null) names.add(p);
        return new ArgsPC(names, Arrays.asList(positions));
    }

    private static PointcutMatcher matcher() {
        TypeResolver tr = new TypeResolver(List.of(
                "java.lang.String", "java.lang.Object", "java.security.Provider"));
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
    // Inert binding-only form: hasTypeConstraint() == false → always-match.
    // ------------------------------------------------------------------

    @Test
    void bindingOnlyArgsAlwaysMatchesRegardlessOfActualArity() {
        // args(o, o1) — pure binding names, no positional Type. hasTypeConstraint()
        // is false, so the matcher stays the inert always-match collector even when
        // the actual call has a completely different arity.
        PointcutMatcher pm = matcher();
        ArgsPC bindingOnly = new ArgsPC(List.of("o", "o1"));  // types = []
        Fixture threeArgs = invokeStatic(List.of("I", STRING_DESC, PROVIDER_DESC));
        assertTrue(match(pm, bindingOnly, threeArgs).isPresent(),
                "a binding-only args(...) MUST always match (no positional type constraint)");
    }

    @Test
    void wildcardAndRestOnlyArgsHaveNoTypeConstraint() {
        // args(*, ..) — a '*' and a trailing '..' are NOT concrete types, so
        // hasTypeConstraint() is false and the form stays inert.
        PointcutMatcher pm = matcher();
        Fixture twoArgs = invokeStatic(List.of("I", STRING_DESC));
        assertTrue(match(pm, argsType("*", ".."), twoArgs).isPresent(),
                "args(*, ..) carries no type constraint and MUST always match");
    }

    // ------------------------------------------------------------------
    // Positive type matching (exact + subtype).
    // ------------------------------------------------------------------

    @Test
    void argsTypeMatchesExactSingleArgument() {
        // args(String) vs append(String) — exact declared type match.
        PointcutMatcher pm = matcher();
        Fixture f = invokeStatic(List.of(STRING_DESC));
        assertTrue(match(pm, argsType("String"), f).isPresent(),
                "args(String) MUST match a call whose sole declared arg type is String");
    }

    @Test
    void argsTypeMatchesSubtypeThroughObjectFastPath() {
        // args(Object) vs append(String) — Object is assignable from any reference
        // type via InheritanceResolver's Object fast-path (subtype-aware §4.AT).
        PointcutMatcher pm = matcher();
        Fixture f = invokeStatic(List.of(STRING_DESC));
        assertTrue(match(pm, argsType("Object"), f).isPresent(),
                "args(Object) MUST match a String argument (subtype via Object fast-path)");
    }

    @Test
    void argsTypePlusMarkerIsStrippedAndSubtypeAware() {
        // args(Object+) — the trailing '+' is stripped; subtype checking is
        // unconditional, so it matches the String arg exactly like args(Object).
        PointcutMatcher pm = matcher();
        Fixture f = invokeStatic(List.of(STRING_DESC));
        assertTrue(match(pm, argsType("Object+"), f).isPresent(),
                "args(Object+) MUST match a String argument (subtype marker)");
    }

    // ------------------------------------------------------------------
    // Negative type matching (mismatch + primitive guard).
    // ------------------------------------------------------------------

    @Test
    void argsTypeRejectsUnrelatedArgumentType() {
        // args(String) vs append(int) — int is not assignable to String, and the
        // primitive guard prevents the Object fast-path from leaking in.
        PointcutMatcher pm = matcher();
        Fixture f = invokeStatic(List.of("I"));
        assertTrue(match(pm, argsType("String"), f).isEmpty(),
                "args(String) MUST NOT match a call whose sole arg is a primitive int");
    }

    // ------------------------------------------------------------------
    // Arity gating (exact vs trailing ..).
    // ------------------------------------------------------------------

    @Test
    void argsTypeExactArityRejectsHigherArity() {
        // args(String) (no trailing ..) MUST NOT match append(String, Provider):
        // the positional count must equal the actual arity.
        PointcutMatcher pm = matcher();
        Fixture twoArgs = invokeStatic(List.of(STRING_DESC, PROVIDER_DESC));
        assertTrue(match(pm, argsType("String"), twoArgs).isEmpty(),
                "exact args(String) MUST NOT match a 2-argument call (arity gate)");
    }

    @Test
    void argsTypeTrailingRestAcceptsHeadPlusAnyTail() {
        // args(String, ..) matches both (String) and (String, Provider): the head
        // String must match; the trailing .. accepts any remaining arguments.
        PointcutMatcher pm = matcher();
        assertTrue(match(pm, argsType("String", ".."), invokeStatic(List.of(STRING_DESC))).isPresent(),
                "args(String, ..) MUST match a call with exactly the head argument");
        assertTrue(match(pm, argsType("String", ".."),
                        invokeStatic(List.of(STRING_DESC, PROVIDER_DESC))).isPresent(),
                "args(String, ..) MUST match a call with the head plus extra tail args");
    }

    @Test
    void argsTypeTrailingRestStillGatesTheHeadType() {
        // args(String, ..) MUST NOT match append(int, Provider): even with the
        // accept-rest tail, the head position is a concrete type gate.
        PointcutMatcher pm = matcher();
        Fixture f = invokeStatic(List.of("I", PROVIDER_DESC));
        assertTrue(match(pm, argsType("String", ".."), f).isEmpty(),
                "args(String, ..) MUST reject a non-String head even with a trailing rest");
    }

    // ------------------------------------------------------------------
    // Mixed wildcard head: '*' accepts any single arg, later position type-gated.
    // ------------------------------------------------------------------

    @Test
    void argsTypeWildcardPositionAcceptsAnyThenGatesLater() {
        // args(*, String) matches (int, String) — the '*' accepts the int in
        // position 0, and position 1 is type-checked against String.
        PointcutMatcher pm = matcher();
        assertTrue(match(pm, argsType("*", "String"),
                        invokeStatic(List.of("I", STRING_DESC))).isPresent(),
                "args(*, String) MUST match (int, String): '*' accepts any first arg");
        // ...but MUST NOT match (int, int): the type-gated second position fails.
        assertTrue(match(pm, argsType("*", "String"),
                        invokeStatic(List.of("I", "I"))).isEmpty(),
                "args(*, String) MUST NOT match (int, int): the second position is type-gated");
    }

    // ------------------------------------------------------------------
    // Non-reference join point with a type constraint → no match.
    // ------------------------------------------------------------------

    @Test
    void argsTypeRejectsNonReferenceInstruction() {
        // A const/4 has no MethodReference, so a type-form args(...) cannot read
        // argument descriptors — it MUST return no match (matchArgs:272 guard).
        PointcutMatcher pm = matcher();
        assertTrue(match(pm, argsType("String"), nonReferenceInstruction()).isEmpty(),
                "type-form args(...) MUST NOT match a non-ReferenceInstruction join point");
    }
}
