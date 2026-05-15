package br.unb.cic.rv.pointcut;

import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.iface.instruction.Instruction;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction10x;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction11x;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction12x;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableMethodReference;

import org.junit.jupiter.api.Test;

import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * gh56 task 3.1: unit tests for {@link PointcutMatcher#buildCallMatch}.
 *
 * <p>Exercises the canonical seat of the bug fix at the unit level —
 * register offset (INV-INS-70), {@code $return} synthetic peek (INV-INS-72),
 * and the D3 two-predicate constructor gate. Full-pipeline coverage
 * (PointcutMatcher → MonitorInvokeBuilder → DexWeaver) lives in
 * {@code dex-mutator}'s {@code DexWeaverConstructorAdviceTest}; this class
 * is the belt-and-suspenders layer.
 *
 * <p>The method under test is package-private (no {@code private} on
 * {@code buildCallMatch}) — see the rationale comment in
 * {@link PointcutMatcher}.
 */
class PointcutMatcherConstructorTest {

    private static final String OWNER = "Ljavax/crypto/spec/SecretKeySpec;";
    private static final String OBJECT_OWNER = "Ljava/lang/Object;";
    private static final String FOO_OWNER = "LFoo;";

    // -------------------------------------------------------------------------
    // Helpers
    // -------------------------------------------------------------------------

    /** Constructor-flavoured CallPC: {@code isConstructor=true, methodName=<init>}. */
    private static CallPC constructorPc(String declaring, List<String> paramTypes) {
        return new CallPC(/*isConstructor*/ true, /*returnType*/ "",
                declaring, /*methodName*/ "<init>", paramTypes, /*varargs*/ false);
    }

    /** Non-constructor CallPC. */
    private static CallPC virtualPc(String declaring, String returnType, String methodName,
                                    List<String> paramTypes) {
        return new CallPC(/*isConstructor*/ false, returnType, declaring, methodName,
                paramTypes, /*varargs*/ false);
    }

    private static MethodReference ref(String owner, String name, List<String> paramTypes,
                                       String returnType) {
        return new ImmutableMethodReference(owner, name, paramTypes, returnType);
    }

    /** {@code move-result-object vDest}. */
    private static Instruction moveResultObject(int vDest) {
        return new ImmutableInstruction11x(Opcode.MOVE_RESULT_OBJECT, vDest);
    }

    /** {@code move-result-wide vDest} — pair (vDest, vDest+1). */
    private static Instruction moveResultWide(int vDest) {
        return new ImmutableInstruction11x(Opcode.MOVE_RESULT_WIDE, vDest);
    }

    /** {@code return-void}. */
    private static Instruction returnVoid() {
        return new ImmutableInstruction10x(Opcode.RETURN_VOID);
    }

    /** A non-move-result follow-up so the peek finds nothing useful. */
    private static Instruction nop12x() {
        return new ImmutableInstruction12x(Opcode.MOVE, 0, 1);
    }

    // -------------------------------------------------------------------------
    // INV-INS-70: constructor offset captures receiver + arg shift +1
    // -------------------------------------------------------------------------

    @Test
    void constructorOffsetCapturesReceiverAndShiftsArgs() {
        // invoke-direct {v4, v3, v0}, SecretKeySpec.<init>([B, String)V
        // followed by return-void (constructors return void → no move-result*)
        CallPC cp = constructorPc("javax.crypto.spec.SecretKeySpec",
                List.of("byte[]", "String"));
        MethodReference mr = ref(OWNER, "<init>",
                List.of("[B", "Ljava/lang/String;"), "V");
        int[] regs = {4, 3, 0};
        List<Instruction> insns = List.of(
                /*idx 0:*/ returnVoid(),  // placeholder before
                /*idx 1:*/ returnVoid(),  // the invoke would conceptually live here
                /*idx 2:*/ returnVoid()); // peek target

        Match m = PointcutMatcher.buildCallMatch(cp, mr, regs,
                /*isStaticInvoke*/ false, insns, /*invokeIndex*/ 1);

        assertTrue(m.isConstructor,
                "both predicates agree (cp.isConstructor && mr.name==<init>): isConstructor=true");
        assertEquals(4, m.targetRegister,
                "constructor receiver MUST equal regs[0] (the freshly-allocated instance)");
        assertEquals(3, m.argBindings.get("arg00"),
                "arg00 MUST equal regs[1] (first user-visible param) under offset 1");
        assertEquals(0, m.argBindings.get("arg01"),
                "arg01 MUST equal regs[2] under offset 1");
        assertFalse(m.argBindings.containsKey("$return"),
                "no $return key for constructors (no move-result* after <init>)");
    }

    // -------------------------------------------------------------------------
    // INV-INS-72: move-result-object follow-up → $return synthetic key
    // -------------------------------------------------------------------------

    @Test
    void virtualInvokeWithMoveResultObjectCapturesDollarReturn() {
        // invoke-virtual {v2}, KeyGenerator.generateKey()Ljavax/crypto/SecretKey;
        // move-result-object v5
        CallPC cp = virtualPc("javax.crypto.KeyGenerator", "SecretKey",
                "generateKey", List.of());
        MethodReference mr = ref("Ljavax/crypto/KeyGenerator;", "generateKey",
                List.of(), "Ljavax/crypto/SecretKey;");
        int[] regs = {2};
        List<Instruction> insns = List.of(
                returnVoid(),                  // idx 0
                moveResultObject(5));          // idx 1 — peeked from invokeIndex=0

        Match m = PointcutMatcher.buildCallMatch(cp, mr, regs,
                /*isStaticInvoke*/ false, insns, /*invokeIndex*/ 0);

        assertFalse(m.isConstructor);
        assertEquals(2, m.targetRegister,
                "virtual instance receiver MUST equal regs[0]");
        assertEquals(5, m.argBindings.get("$return"),
                "$return MUST equal the move-result-object destination register");
    }

    @Test
    void staticInvokeWithMoveResultWideCapturesLowRegisterOfPair() {
        // invoke-static {}, System.currentTimeMillis()J
        // move-result-wide v6   (pair v6+v7)
        CallPC cp = virtualPc("java.lang.System", "long",
                "currentTimeMillis", List.of());
        MethodReference mr = ref("Ljava/lang/System;", "currentTimeMillis",
                List.of(), "J");
        int[] regs = {};
        List<Instruction> insns = List.of(
                returnVoid(),
                moveResultWide(6));

        Match m = PointcutMatcher.buildCallMatch(cp, mr, regs,
                /*isStaticInvoke*/ true, insns, /*invokeIndex*/ 0);

        assertFalse(m.isConstructor);
        assertEquals(-1, m.targetRegister, "static invoke MUST have no receiver");
        assertEquals(6, m.argBindings.get("$return"),
                "$return for wide return MUST store the low register vN of the pair (vN, vN+1)");
    }

    // -------------------------------------------------------------------------
    // Negative cases (no $return)
    // -------------------------------------------------------------------------

    @Test
    void virtualInvokeWithoutMoveResultDoesNotPopulateDollarReturn() {
        // invoke-virtual {v2}, Cipher.doFinal()V (hypothetical void return)
        // followed by something that is NOT a move-result*.
        CallPC cp = virtualPc("javax.crypto.Cipher", "void",
                "init", List.of());
        MethodReference mr = ref("Ljavax/crypto/Cipher;", "init",
                List.of(), "V");
        int[] regs = {2};
        List<Instruction> insns = List.of(
                returnVoid(),
                nop12x());

        Match m = PointcutMatcher.buildCallMatch(cp, mr, regs,
                /*isStaticInvoke*/ false, insns, /*invokeIndex*/ 0);

        assertFalse(m.argBindings.containsKey("$return"),
                "no move-result* after the invoke → no $return key");
    }

    @Test
    void staticInvokeWithoutMoveResultLeavesNoDollarReturn() {
        CallPC cp = virtualPc("java.lang.System", "void", "exit",
                List.of("int"));
        MethodReference mr = ref("Ljava/lang/System;", "exit",
                List.of("I"), "V");
        int[] regs = {3};
        List<Instruction> insns = List.of(returnVoid(), nop12x());

        Match m = PointcutMatcher.buildCallMatch(cp, mr, regs,
                /*isStaticInvoke*/ true, insns, /*invokeIndex*/ 0);

        assertEquals(-1, m.targetRegister);
        assertEquals(3, m.argBindings.get("arg00"),
                "static invoke: first user param at regs[0]");
        assertFalse(m.argBindings.containsKey("$return"));
    }

    @Test
    void staticInvokeArgOffsetZero() {
        // invoke-static {v3, v0}, MessageDigest.update([B, int)V
        CallPC cp = virtualPc("java.security.MessageDigest", "void",
                "update", List.of("byte[]", "int"));
        MethodReference mr = ref("Ljava/security/MessageDigest;", "update",
                List.of("[B", "I"), "V");
        int[] regs = {3, 0};
        List<Instruction> insns = List.of(returnVoid(), nop12x());

        Match m = PointcutMatcher.buildCallMatch(cp, mr, regs,
                /*isStaticInvoke*/ true, insns, /*invokeIndex*/ 0);

        assertEquals(-1, m.targetRegister);
        assertEquals(3, m.argBindings.get("arg00"));
        assertEquals(0, m.argBindings.get("arg01"));
    }

    @Test
    void virtualInvokeArgOffsetOne() {
        // invoke-virtual {v2, v5, v6}, KeyGenerator.init(int, SecureRandom)V
        CallPC cp = virtualPc("javax.crypto.KeyGenerator", "void",
                "init", List.of("int", "SecureRandom"));
        MethodReference mr = ref("Ljavax/crypto/KeyGenerator;", "init",
                List.of("I", "Ljava/security/SecureRandom;"), "V");
        int[] regs = {2, 5, 6};
        List<Instruction> insns = List.of(returnVoid(), returnVoid());

        Match m = PointcutMatcher.buildCallMatch(cp, mr, regs,
                /*isStaticInvoke*/ false, insns, /*invokeIndex*/ 0);

        assertFalse(m.isConstructor);
        assertEquals(2, m.targetRegister);
        assertEquals(5, m.argBindings.get("arg00"));
        assertEquals(6, m.argBindings.get("arg01"));
    }

    // -------------------------------------------------------------------------
    // D3 two-predicate gate: defence in depth against private invoke-direct
    // and super.<init> chaining.
    // -------------------------------------------------------------------------

    @Test
    void privateInvokeDirectNonInitDoesNotTriggerConstructorSemantics() {
        // invoke-direct {v0, v1}, Foo.helper(int)V — private method (not <init>)
        // matched by a CallPC whose isConstructor==false → NOT a constructor.
        // Guards against the false-friend in proposed Fix #1.
        CallPC cp = virtualPc("Foo", "void", "helper", List.of("int"));
        MethodReference mr = ref(FOO_OWNER, "helper", List.of("I"), "V");
        int[] regs = {0, 1};
        List<Instruction> insns = List.of(returnVoid(), returnVoid());

        Match m = PointcutMatcher.buildCallMatch(cp, mr, regs,
                /*isStaticInvoke*/ false, insns, /*invokeIndex*/ 0);

        assertFalse(m.isConstructor,
                "cp.isConstructor==false → match.isConstructor=false (D3 guard)");
        assertEquals(0, m.targetRegister,
                "virtual fallback path: receiver still at regs[0]");
        assertEquals(1, m.argBindings.get("arg00"),
                "args at offset 1 (the virtual instance path)");
    }

    // Note: the `super.<init>` chain case is not unit-tested at the
    // buildCallMatch level because the defence sits one layer up in
    // matchCall (owner descriptor mismatch makes the matcher bail before
    // buildCallMatch is called). The D3 two-predicate gate documented here
    // is exercised by `descriptorDisagreeDoesNotEngageConstructorSemantics`
    // below; see the ADR for the full rationale.

    @Test
    void descriptorDisagreeDoesNotEngageConstructorSemantics() {
        // cp.isConstructor==true but MethodReference.name != "<init>"
        // (impossible in well-formed input, but defends against malformed
        // descriptors). match.isConstructor MUST be false; arguments take
        // the virtual fallback path with regs[0] still captured.
        CallPC cp = constructorPc("LFoo;", List.of("int"));
        MethodReference mr = ref(FOO_OWNER, "notInit", List.of("I"), "V");
        int[] regs = {2, 3};
        List<Instruction> insns = List.of(returnVoid(), returnVoid());

        Match m = PointcutMatcher.buildCallMatch(cp, mr, regs,
                /*isStaticInvoke*/ false, insns, /*invokeIndex*/ 0);

        assertFalse(m.isConstructor,
                "descriptor predicate alone is insufficient — method name must also be <init>");
        // The capture path is the virtual-instance fallback (still offset 1),
        // since isStaticInvoke=false.
        assertEquals(2, m.targetRegister);
        assertEquals(3, m.argBindings.get("arg00"));
    }

    // -------------------------------------------------------------------------
    // Edge: index at end of method (peek target absent) must not crash.
    // -------------------------------------------------------------------------

    // -------------------------------------------------------------------------
    // gh59 — wide-slot tracking in argBindings.
    //
    // When the callee constructor's parameter list contains a `long` or
    // `double` (J/D, two register slots), every subsequent arg binding MUST
    // shift by two register slots — not one. The previous implementation
    // indexed `regs[baseOffset + i]` and advanced by one per parameter,
    // producing bindings that pointed at the high-half of the wide (typed
    // `Long (Low Half)` by the verifier) or at the wrong downstream slot.
    //
    // Empirical evidence at the integration level:
    //   - com.github.soundpod_16.apk     -> yu5.<init>  (25 params, 6× J), v7 (Long Low Half)
    //   - com.grappim.taigamobile.fdroid -> ga.e.<init> (19 params, Z/refs), v3 (Boolean)
    // -------------------------------------------------------------------------

    @Test
    void constructorWidePrimitivesInterleavedBindArgumentsByRegisterSlot() {
        // Constructor descriptor (LFoo;JZLFoo;J)V — receiver + 5 user-visible
        // params with `long`s interleaved with refs/boolean. invoke-direct/range
        // emits contiguous registers v10..v17 (8 slots: 1 receiver + 1 ref +
        // 2 long-pair + 1 boolean + 1 ref + 2 long-pair).
        CallPC cp = constructorPc("Foo",
                List.of("Foo", "long", "boolean", "Foo", "long"));
        MethodReference mr = ref(FOO_OWNER, "<init>",
                List.of(FOO_OWNER, "J", "Z", FOO_OWNER, "J"), "V");
        int[] regs = {10, 11, 12, 13, 14, 15, 16, 17};
        List<Instruction> insns = List.of(returnVoid(), returnVoid());

        Match m = PointcutMatcher.buildCallMatch(cp, mr, regs,
                /*isStaticInvoke*/ false, insns, /*invokeIndex*/ 0);

        assertTrue(m.isConstructor);
        assertEquals(10, m.targetRegister,
                "constructor receiver MUST equal regs[0]");
        // baseOffset=1 (constructor). Cursor advances +1 for refs/booleans,
        // +2 for J/D. Expected mapping:
        //   arg00 (LFoo;) -> v11   (cursor 1, advance +1 -> 2)
        //   arg01 (J low) -> v12   (cursor 2, advance +2 -> 4)   // v13 = J high half (skipped)
        //   arg02 (Z)     -> v14   (cursor 4, advance +1 -> 5)
        //   arg03 (LFoo;) -> v15   (cursor 5, advance +1 -> 6)
        //   arg04 (J low) -> v16   (cursor 6, advance +2 -> 8)   // v17 = J high half
        assertEquals(11, m.argBindings.get("arg00"),
                "arg00 (ref) at v11");
        assertEquals(12, m.argBindings.get("arg01"),
                "arg01 (long low half) at v12");
        assertEquals(14, m.argBindings.get("arg02"),
                "arg02 (boolean) at v14 — wide-slot before MUST shift the cursor by 2");
        assertEquals(15, m.argBindings.get("arg03"),
                "arg03 (ref) at v15");
        assertEquals(16, m.argBindings.get("arg04"),
                "arg04 (long low half) at v16 — accumulated shift = 2");
    }

    @Test
    void peekAtEndOfMethodIsBoundsSafe() {
        // Single-instruction body — invokeIndex is the LAST instruction;
        // peeking idx+1 is out of bounds. Must NOT throw; just no $return.
        CallPC cp = virtualPc("Foo", "void", "noop", List.of());
        MethodReference mr = ref(FOO_OWNER, "noop", List.of(), "V");
        List<Instruction> insns = Collections.singletonList(returnVoid());

        Match m = PointcutMatcher.buildCallMatch(cp, mr, new int[]{1},
                /*isStaticInvoke*/ false, insns, /*invokeIndex*/ 0);

        assertNull(m.argBindings.get("$return"),
                "out-of-bounds peek must produce no $return (no exception thrown)");
    }
}
