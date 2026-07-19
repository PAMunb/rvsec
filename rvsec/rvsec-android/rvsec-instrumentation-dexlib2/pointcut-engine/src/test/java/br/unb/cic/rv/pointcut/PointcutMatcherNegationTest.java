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
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction3rc;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableMethodReference;

import org.junit.jupiter.api.Test;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * §4.N — {@code !target(T)} / {@code !args(T)} generic negation at
 * {@link PointcutMatcher#matchNegation} (spec.md:1521). The matcher evaluates the
 * inner {@link TargetPC} / {@link ArgsPC} type form and INVERTS the verdict: a
 * present inner match yields no match; an empty inner verdict (the type did not
 * match, OR the join point is a receiverless static invoke) yields a match that
 * carries NO bindings.
 *
 * <p>Coverage gap this closes: {@link NegationPC} was 0% (entirely dead) —
 * {@code matchNegation:194-200} was never reached. Because negation wraps the
 * target/args type forms, its correctness depends on theirs (covered by the
 * sibling target/args type-form tests); these tests pin the inversion itself and
 * the no-bindings contract.
 */
class PointcutMatcherNegationTest {

    private static final String CIPHER_OWNER = "Ljavax/crypto/Cipher;";
    private static final String UNRELATED_OWNER = "Ljava/util/ArrayList;";
    private static final String APP_OWNER = "Lcom/example/app/Site;";
    private static final String STRING_DESC = "Ljava/lang/String;";

    // ------------------------------------------------------------------
    // Fixtures
    // ------------------------------------------------------------------

    /** {@code invoke-virtual {v2}, owner.doWork()V} — receiver in v2. */
    private static Fixture invokeVirtual(String ownerDesc) {
        ImmutableMethodReference ref = new ImmutableMethodReference(
                ownerDesc, "doWork", Collections.emptyList(), "V");
        return singleInvoke(new ImmutableInstruction35c(
                Opcode.INVOKE_VIRTUAL, 1, /*c=*/ 2, 0, 0, 0, 0, ref), 3);
    }

    /** {@code invoke-static/range {v0}, owner.take(<param>)V} — no receiver. */
    private static Fixture invokeStatic(String paramDesc) {
        ImmutableMethodReference ref = new ImmutableMethodReference(
                CIPHER_OWNER, "take", List.of(paramDesc), "V");
        return singleInvoke(new ImmutableInstruction3rc(
                Opcode.INVOKE_STATIC_RANGE, /*startReg=*/ 0, /*regCount=*/ 1, ref), 1);
    }

    private static Fixture singleInvoke(
            com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction invoke,
            int registerCount) {
        List<com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction> body =
                new ArrayList<>();
        body.add(invoke);
        body.add(new ImmutableInstruction10x(Opcode.RETURN_VOID));
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

    private static ArgsPC argsType(String... positions) {
        List<String> names = new ArrayList<>();
        for (String p : positions) if (p != null) names.add(p);
        return new ArgsPC(names, Arrays.asList(positions));
    }

    private static PointcutMatcher matcher() {
        TypeResolver tr = new TypeResolver(List.of("javax.crypto.Cipher", "java.lang.String"));
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
    // !target(T)
    // ------------------------------------------------------------------

    @Test
    void negatedTargetRejectsWhenInnerTypeMatches() {
        // !target(Cipher) at a Cipher receiver: the inner target(Cipher) matches,
        // so the negation inverts to no match (spec §4.N: "the receiver IS a
        // MyClass, so its negation is false").
        PointcutMatcher pm = matcher();
        NegationPC neg = new NegationPC(TargetPC.type("Cipher"));
        assertTrue(match(pm, neg, invokeVirtual(CIPHER_OWNER)).isEmpty(),
                "!target(Cipher) MUST NOT match when the receiver IS a Cipher");
    }

    @Test
    void negatedTargetMatchesWhenInnerTypeDoesNotMatch() {
        // !target(Cipher) at an unrelated receiver: the inner target(Cipher) fails,
        // so the negation matches — and carries NO bindings.
        PointcutMatcher pm = matcher();
        NegationPC neg = new NegationPC(TargetPC.type("Cipher"));
        Optional<Match> r = match(pm, neg, invokeVirtual(UNRELATED_OWNER));
        assertTrue(r.isPresent(),
                "!target(Cipher) MUST match when the receiver is unrelated to Cipher");
        assertTrue(r.get().argBindings.isEmpty(),
                "a negation carries no argument bindings");
        assertEquals(-1, r.get().targetRegister,
                "a negation carries no target binding (targetRegister = -1)");
    }

    @Test
    void negatedTargetMatchesReceiverlessStaticInvoke() {
        // !target(Cipher) at a static invoke: the inner target(Cipher) returns empty
        // because a static invoke has no receiver to constrain, so the negation
        // MATCHES (spec §4.N: "the join point is a static invoke ... yields a match").
        PointcutMatcher pm = matcher();
        NegationPC neg = new NegationPC(TargetPC.type("Cipher"));
        assertTrue(match(pm, neg, invokeStatic(STRING_DESC)).isPresent(),
                "!target(Cipher) MUST match a receiverless static invoke");
    }

    // ------------------------------------------------------------------
    // !args(T)
    // ------------------------------------------------------------------

    @Test
    void negatedArgsRejectsWhenInnerTypeMatches() {
        // !args(String) at take(String): inner args(String) matches → negation inverts.
        PointcutMatcher pm = matcher();
        NegationPC neg = new NegationPC(argsType("String"));
        assertTrue(match(pm, neg, invokeStatic(STRING_DESC)).isEmpty(),
                "!args(String) MUST NOT match when the sole arg IS a String");
    }

    @Test
    void negatedArgsMatchesWhenInnerTypeDoesNotMatch() {
        // !args(String) at take(int): inner args(String) fails on the primitive →
        // negation matches, no bindings.
        PointcutMatcher pm = matcher();
        NegationPC neg = new NegationPC(argsType("String"));
        Optional<Match> r = match(pm, neg, invokeStatic("I"));
        assertTrue(r.isPresent(),
                "!args(String) MUST match when the sole arg is a primitive int");
        assertTrue(r.get().argBindings.isEmpty(),
                "a negation carries no argument bindings");
    }
}
