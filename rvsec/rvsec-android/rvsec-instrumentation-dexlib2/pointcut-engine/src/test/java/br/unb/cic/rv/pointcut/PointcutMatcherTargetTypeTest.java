package br.unb.cic.rv.pointcut;

import com.android.tools.smali.dexlib2.AccessFlags;
import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.DexFile;
import com.android.tools.smali.dexlib2.iface.Method;
import com.android.tools.smali.dexlib2.iface.instruction.Instruction;
import com.android.tools.smali.dexlib2.immutable.ImmutableClassDef;
import com.android.tools.smali.dexlib2.immutable.ImmutableDexFile;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethod;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethodImplementation;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction10x;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction11n;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction35c;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableMethodReference;

import org.junit.jupiter.api.Test;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * §4.TT — {@code target(Type)} type-matching at {@link PointcutMatcher#matchTarget}
 * (spec.md:1539). The matcher constrains a call's DECLARED receiver type (the
 * invoke owner in the {@link com.android.tools.smali.dexlib2.iface.reference.MethodReference})
 * to the pattern type or a subtype ({@code isAssignableFrom}, subtype-aware),
 * per the round-8 V-decision (static declared type, not runtime instance-of).
 *
 * <p>Coverage gap this closes: the type form of {@code target(...)} was entirely
 * dark ({@code TargetPC} 0% branch, {@code matchTarget:220-246} unhit) — only the
 * inert binding form {@code target(o)} was reached, indirectly. The negative and
 * static-invoke cases are the regression guards: if the type form ever degraded to
 * the always-match binding behaviour, an unrelated receiver (or a receiverless
 * static invoke) would wrongly report a match.
 */
class PointcutMatcherTargetTypeTest {

    private static final String CIPHER_OWNER = "Ljavax/crypto/Cipher;";
    private static final String SUBTYPE_OWNER = "Lcom/example/app/MyCipher;";
    private static final String UNRELATED_OWNER = "Ljava/util/ArrayList;";
    private static final String APP_OWNER = "Lcom/example/app/Site;";

    // ------------------------------------------------------------------
    // Fixtures
    // ------------------------------------------------------------------

    /** Single {@code invoke-virtual {v2}, owner.name()ret} fixture (receiver in v2). */
    private static Fixture invokeVirtual(String ownerDesc, String name, String returnDesc) {
        ImmutableMethodReference ref = new ImmutableMethodReference(
                ownerDesc, name, Collections.emptyList(), returnDesc);
        List<com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction> body =
                new ArrayList<>();
        body.add(new ImmutableInstruction35c(
                Opcode.INVOKE_VIRTUAL, /*regCount=*/ 1,
                /*c=*/ 2, /*d=*/ 0, /*e=*/ 0, /*f=*/ 0, /*g=*/ 0, ref));
        body.add(new ImmutableInstruction10x(Opcode.RETURN_VOID));
        return buildFixture(body);
    }

    /** Single {@code invoke-static {v2}, owner.name(int)ret} fixture (no receiver). */
    private static Fixture invokeStatic(String ownerDesc, String name, String returnDesc) {
        ImmutableMethodReference ref = new ImmutableMethodReference(
                ownerDesc, name, List.of("I"), returnDesc);
        List<com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction> body =
                new ArrayList<>();
        body.add(new ImmutableInstruction35c(
                Opcode.INVOKE_STATIC, /*regCount=*/ 1,
                /*c=*/ 2, /*d=*/ 0, /*e=*/ 0, /*f=*/ 0, /*g=*/ 0, ref));
        body.add(new ImmutableInstruction10x(Opcode.RETURN_VOID));
        return buildFixture(body);
    }

    /** A {@code const/4 v0, #0} join point — NOT a {@link
     *  com.android.tools.smali.dexlib2.iface.instruction.ReferenceInstruction}. */
    private static Fixture nonReferenceInstruction() {
        List<com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction> body =
                new ArrayList<>();
        body.add(new ImmutableInstruction11n(Opcode.CONST_4, /*reg=*/ 0, /*lit=*/ 0));
        body.add(new ImmutableInstruction10x(Opcode.RETURN_VOID));
        return buildFixture(body);
    }

    private static Fixture buildFixture(
            List<com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction> body) {
        ImmutableMethodImplementation impl = new ImmutableMethodImplementation(
                /*registerCount=*/ 3, body, Collections.emptyList(), Collections.emptyList());
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

    /** A synthetic APK {@link DexFile} declaring {@code MyCipher extends Cipher},
     *  giving {@link InheritanceResolver} a real subtype edge without android.jar. */
    private static DexFile cipherSubtypeDex() {
        ClassDef sub = new ImmutableClassDef(
                SUBTYPE_OWNER, AccessFlags.PUBLIC.getValue(), CIPHER_OWNER,
                Collections.emptyList(), null, null,
                Collections.emptyList(), Collections.emptyList());
        return new ImmutableDexFile(Opcodes.getDefault(), List.of(sub));
    }

    /** Matcher whose imports resolve {@code Cipher} and whose inheritance index
     *  optionally carries the {@code MyCipher extends Cipher} APK edge. */
    private static PointcutMatcher matcher(DexFile... apkDexes) {
        TypeResolver tr = new TypeResolver(List.of("javax.crypto.Cipher"));
        InheritanceResolver ir = new InheritanceResolver(
                new AndroidClassIndex(Path.of("/tmp/nope.jar")), List.of(apkDexes));
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
    // Positive: declared receiver is exactly the pattern type
    // ------------------------------------------------------------------

    @Test
    void targetTypeMatchesExactDeclaredReceiver() {
        // invoke-virtual {v2}, Cipher.doFinal()[B — receiver declared as Cipher.
        // target(Cipher) MUST match via the reflexive isAssignableFrom.
        PointcutMatcher pm = matcher();
        Fixture f = invokeVirtual(CIPHER_OWNER, "doFinal", "[B");
        assertTrue(match(pm, TargetPC.type("Cipher"), f).isPresent(),
                "target(Cipher) MUST match a receiver whose declared type IS Cipher");
    }

    // ------------------------------------------------------------------
    // Positive: declared receiver is a subtype of the pattern type
    // ------------------------------------------------------------------

    @Test
    void targetTypeMatchesSubtypeReceiver() {
        // invoke-virtual {v2}, MyCipher.doFinal()[B where MyCipher extends Cipher.
        // target(Cipher) MUST match through the subtype-aware isAssignableFrom
        // (§4.TT: "or a subtype"). Without the APK edge this would fail closed.
        PointcutMatcher pm = matcher(cipherSubtypeDex());
        Fixture f = invokeVirtual(SUBTYPE_OWNER, "doFinal", "[B");
        assertTrue(match(pm, TargetPC.type("Cipher"), f).isPresent(),
                "target(Cipher) MUST match a receiver declared as a Cipher subtype");
    }

    @Test
    void targetTypePlusMarkerMatchesSubtypeReceiver() {
        // target(Cipher+) — the trailing '+' is stripped and redundant (subtype
        // checking is unconditional), so it MUST match the same subtype receiver.
        PointcutMatcher pm = matcher(cipherSubtypeDex());
        Fixture f = invokeVirtual(SUBTYPE_OWNER, "doFinal", "[B");
        assertTrue(match(pm, TargetPC.type("Cipher+"), f).isPresent(),
                "target(Cipher+) MUST match a Cipher subtype receiver (the '+' is redundant here)");
    }

    // ------------------------------------------------------------------
    // Negative: unrelated declared receiver (the core regression guard)
    // ------------------------------------------------------------------

    @Test
    void targetTypeRejectsUnrelatedReceiver() {
        // invoke-virtual {v2}, ArrayList.clear()V — ArrayList is not assignable
        // to Cipher (no edge in the empty inheritance index). target(Cipher) MUST
        // NOT match. If the type form degraded to the inert binding always-match,
        // this would wrongly report present.
        PointcutMatcher pm = matcher();
        Fixture f = invokeVirtual(UNRELATED_OWNER, "clear", "V");
        assertTrue(match(pm, TargetPC.type("Cipher"), f).isEmpty(),
                "target(Cipher) MUST NOT match a receiver whose declared type is unrelated to Cipher");
    }

    // ------------------------------------------------------------------
    // Negative: no receiver on a static invoke; non-reference join point
    // ------------------------------------------------------------------

    @Test
    void targetTypeRejectsStaticInvokeWithNoReceiver() {
        // invoke-static getInstance(int) — a static invoke has no receiver, so a
        // target(Type) constraint cannot be satisfied (matchTarget:229 guard).
        PointcutMatcher pm = matcher();
        Fixture f = invokeStatic(CIPHER_OWNER, "getInstance", CIPHER_OWNER);
        assertTrue(match(pm, TargetPC.type("Cipher"), f).isEmpty(),
                "target(Cipher) MUST NOT match a static invoke (no receiver to constrain)");
    }

    @Test
    void targetTypeRejectsNonReferenceInstruction() {
        // A const/4 join point carries no MethodReference — target(Type) cannot
        // read a receiver, so it MUST return no match (matchTarget:224 guard).
        PointcutMatcher pm = matcher();
        Fixture f = nonReferenceInstruction();
        assertTrue(match(pm, TargetPC.type("Cipher"), f).isEmpty(),
                "target(Cipher) MUST NOT match a non-ReferenceInstruction join point");
    }
}
