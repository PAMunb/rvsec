package br.unb.cic.rv.emitter;

import br.unb.cic.rv.descriptor.AdviceDescriptor;
import br.unb.cic.rv.descriptor.MonitorCallDescriptor;
import br.unb.cic.rv.descriptor.ParameterDescriptor;
import br.unb.cic.rv.pointcut.Match;
import br.unb.cic.rv.pointcut.TypeResolver;

import com.android.tools.smali.dexlib2.builder.BuilderInstruction;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction35c;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction3rc;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.MethodSource;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * gh56 task 3.2: cross-product of {emitter} × {invoke kind} × {binding kind}
 * for the named-binding contract (INV-INS-71). Asserts register-to-type
 * correspondence at the funnel ({@link MonitorInvokeBuilder#buildInvoke}).
 *
 * <h2>Type-source independence (closes the gh52-smoke gap)</h2>
 *
 * <p>The original bug (constructor + returning → {@code VerifyError}) passed
 * the gh52 smoke because the existing {@code DexWeaverConstructorAdviceTest}
 * only checked instruction shape (opcode, register count) — it never verified
 * that each register held a value of the type the monitor signature
 * expected. Re-running the same logic on both sides of the assertion can
 * never detect the bug.
 *
 * <p>Therefore every scenario in this test declares its expected
 * register-to-type mapping as a hand-written {@code Map<Integer, String>}
 * fixture constant (e.g. {@code Map.of(3, "[B", 0, "Ljava/lang/String;",
 * 4, "Ljavax/crypto/spec/SecretKeySpec;")}). The expected types are NOT
 * derived from the monitor signature parser nor from the bytecode that the
 * builder under test emits — they are written by hand at fixture-definition
 * time, reflecting the semantics the bytecode is supposed to encode.
 *
 * <h2>Valid combinations only</h2>
 *
 * <p>The full cross-product {@code 5 × 3 × 4 = 60} contains semantically
 * invalid combinations that are enumerated up front and excluded a priori
 * (NOT via {@code assumeTrue}-skip, which would hide enumeration bugs):
 *
 * <ul>
 *   <li>{@code StaticInit × constructor} — static-initialization fires on
 *       {@code <clinit>}, not on instance constructors.
 *   <li>{@code StaticInit × *} — static-init advice has no args/target/
 *       returning/throwing binding semantics; it's pure method-entry trigger.
 *   <li>{@code Before × returning} — before-advice runs PRE-call; there is
 *       no return value at that program point.
 *   <li>{@code Before × throwing} — same reason.
 *   <li>{@code AfterReturning × throwing} — disjoint event sets.
 *   <li>{@code AfterThrowing × returning} — disjoint event sets.
 *   <li>{@code * × constructor + target} — constructor receiver is captured
 *       through {@code targetRegister} but the advice descriptor's
 *       {@code target(name)} binding semantics for constructors is "the
 *       freshly-constructed instance", which is the same value the
 *       {@code returning} binding resolves to (D2/D3). Tested under returning.
 *   <li>{@code static + target} — static invokes have no receiver; the only
 *       valid bindings are {@code args} and {@code returning}.
 * </ul>
 *
 * <p>After filtering, ~14 scenarios remain (full enumeration in
 * {@link #scenarios()}).
 */
class MonitorInvokeBindingTest {

    private static final String MONITOR_OWNER = "Lmop/MultiSpec_1RuntimeMonitor;";

    // -------------------------------------------------------------------------
    // Type-source-independent fixture: each scenario declares (a) the synthetic
    // Match the matcher would produce for the bytecode shape, (b) the advice
    // descriptor, and (c) the EXPECTED type per emitted register slot — drawn
    // from the bytecode (also hand-written), NOT from any helper that re-parses
    // the monitor signature using the same logic the builder uses.
    // -------------------------------------------------------------------------

    static final class Scenario {
        final String name;
        final AdviceDescriptor advice;
        final Match match;
        /** Expected types in monitor signature order (= monitorCall.args order). */
        final List<String> expectedTypeOrder;
        /** Expected registers in monitor signature order. */
        final int[] expectedRegisters;

        Scenario(String name, AdviceDescriptor advice, Match match,
                 List<String> expectedTypeOrder, int[] expectedRegisters) {
            this.name = name;
            this.advice = advice;
            this.match = match;
            this.expectedTypeOrder = expectedTypeOrder;
            this.expectedRegisters = expectedRegisters;
        }

        @Override public String toString() { return name; }
    }

    // -------------------------------------------------------------------------
    // Scenario builders. Each produces a Scenario tuple with hand-written
    // expected registers / types. No helper that derives types from the
    // monitor signature is used here — that would re-introduce the gh52
    // circularity.
    // -------------------------------------------------------------------------

    private static AdviceDescriptor advice(String name, String position, String expression,
                                           List<ParameterDescriptor> params,
                                           List<ParameterDescriptor> returning,
                                           List<ParameterDescriptor> throwing,
                                           String monitorEvent,
                                           List<String> monitorArgs) {
        AdviceDescriptor a = new AdviceDescriptor();
        a.setName(name);
        a.setSpecName("TestSpec");
        a.setPosition(position);
        a.setAround(false);
        a.setReturnType("void");
        a.setExpression(expression);
        a.setParameters(params);
        if (returning != null) a.setReturning(returning);
        if (throwing != null) a.setThrowing(throwing);
        MonitorCallDescriptor mc = new MonitorCallDescriptor();
        mc.setMethod("MultiSpec_1RuntimeMonitor." + monitorEvent);
        mc.setSpecName("TestSpec");
        mc.setEventId(monitorEvent);
        mc.setUniqueId(monitorEvent);
        mc.setArgs(monitorArgs);
        a.setMonitorCalls(List.of(mc));
        return a;
    }

    private static Match constructorMatch(int receiver, int arg0, int arg1) {
        Map<String, Integer> m = new LinkedHashMap<>();
        m.put("arg00", arg0);
        if (arg1 >= 0) m.put("arg01", arg1);
        return new Match(m, receiver, null, /*isConstructor*/ true);
    }

    private static Match virtualMatch(int receiver, int arg0, int dollarReturn) {
        Map<String, Integer> m = new LinkedHashMap<>();
        m.put("arg00", arg0);
        if (dollarReturn >= 0) m.put("$return", dollarReturn);
        return new Match(m, receiver, null, false);
    }

    private static Match staticMatch(int arg0, int dollarReturn) {
        Map<String, Integer> m = new LinkedHashMap<>();
        m.put("arg00", arg0);
        if (dollarReturn >= 0) m.put("$return", dollarReturn);
        return new Match(m, -1, null, false);
    }

    static Stream<Scenario> scenarios() {
        List<Scenario> list = new ArrayList<>();

        // ----- Before × virtual × args+target -----
        // call(public Iterator.hasNext()) && target(it)
        // No returning, no throwing, no $return.
        list.add(new Scenario(
                "Before-virtual-target",
                advice("b1", "before",
                        "call(public boolean Iterator.hasNext()) && target(it)",
                        List.of(new ParameterDescriptor("Iterator", "it")),
                        null, null, "hasNextEvent", List.of("it")),
                virtualMatch(/*receiver=*/ 3, /*arg0=*/ 3, /*$return=*/ -1),
                List.of("Ljava/util/Iterator;"),
                new int[]{3}
        ));

        // ----- Before × virtual × args(name) -----
        // call(public Map.put(Object, Object)) && args(k, v)
        list.add(new Scenario(
                "Before-virtual-args",
                advice("b2", "before",
                        "call(public Object Map.put(Object, Object)) && args(k, v)",
                        List.of(new ParameterDescriptor("Object", "k"),
                                new ParameterDescriptor("Object", "v")),
                        null, null, "putEvent", List.of("k", "v")),
                new Match(orderedMap("arg00", 5, "arg01", 6), /*receiver=*/ 2,
                        null, false),
                List.of("Ljava/lang/Object;", "Ljava/lang/Object;"),
                new int[]{5, 6}
        ));

        // ----- Before × static × args -----
        // call(public static String.valueOf(int))
        list.add(new Scenario(
                "Before-static-args",
                advice("b3", "before",
                        "call(public static String String.valueOf(int)) && args(i)",
                        List.of(new ParameterDescriptor("int", "i")),
                        null, null, "valueOfEvent", List.of("i")),
                staticMatch(/*arg0=*/ 4, /*$return=*/ -1),
                List.of("I"),
                new int[]{4}
        ));

        // ----- After × constructor × args + returning (THE CANONICAL BUG SHAPE) -----
        // call(public SecretKeySpec.new(byte[], String)) && args(keyMaterial, keyAlgorithm)
        // returning(secretKeySpec). Pre-gh56 the emitted regs were {4, 3, 0}
        // → VerifyError. Post-gh56 they MUST be {3, 0, 4}.
        list.add(new Scenario(
                "After-constructor-args-returning (canonical bug shape)",
                advice("c1", "after",
                        "call(public SecretKeySpec.new(byte[], String)) "
                                + "&& args(keyMaterial, keyAlgorithm)",
                        List.of(new ParameterDescriptor("byte[]", "keyMaterial"),
                                new ParameterDescriptor("String", "keyAlgorithm")),
                        List.of(new ParameterDescriptor("SecretKeySpec", "secretKeySpec")),
                        null, "c1Event",
                        List.of("keyMaterial", "keyAlgorithm", "secretKeySpec")),
                constructorMatch(/*receiver=*/ 4, /*arg0=*/ 3, /*arg1=*/ 0),
                List.of("[B", "Ljava/lang/String;", "Ljavax/crypto/spec/SecretKeySpec;"),
                new int[]{3, 0, 4}
        ));

        // ----- AfterReturning × virtual × returning(name) -----
        // call(public Iterator Collection.iterator()) && returning(it)
        list.add(new Scenario(
                "AfterReturning-virtual-returning",
                advice("ar1", "after",
                        "call(public Iterator Collection.iterator())",
                        java.util.Collections.emptyList(),
                        List.of(new ParameterDescriptor("Iterator", "result")),
                        null, "iteratorReturnedEvent", List.of("result")),
                virtualMatch(/*receiver=*/ 2, /*arg0=*/ -1, /*$return=*/ 5),
                List.of("Ljava/util/Iterator;"),
                new int[]{5}
        ));

        // ----- AfterReturning × static × returning(name) -----
        // call(public static MessageDigest.getInstance(String)) && args(algo)
        // returning(digest)
        list.add(new Scenario(
                "AfterReturning-static-args-returning",
                advice("ar2", "after",
                        "call(public static MessageDigest MessageDigest.getInstance(String)) "
                                + "&& args(algo)",
                        List.of(new ParameterDescriptor("String", "algo")),
                        List.of(new ParameterDescriptor("MessageDigest", "digest")),
                        null, "getInstanceEvent", List.of("algo", "digest")),
                staticMatch(/*arg0=*/ 3, /*$return=*/ 6),
                List.of("Ljava/lang/String;", "Ljava/security/MessageDigest;"),
                new int[]{3, 6}
        ));

        // ----- gh59: Before × static × args(long) — wide param FORWARDED to monitor.
        //
        // The first wide test below (AfterReturning-static-wide-return) exercises
        // `returning(long)` — the $return path, which stores only the LOW half.
        // No prior fixture covers a `long`/`double` in `monitorCall.args` being
        // passed forward into the invoke. That gap hid the 2nd-hunk bug of gh59:
        // `registersFor` produces one entry per arg name, and `buildInvokeStatic`
        // uses regs.length as the DEX register-count — so the emitted invoke
        // declares 1 slot for the long instead of 2, and the verifier rejects.
        //
        // The fix expands wide-typed advice args into (vN, vN+1) before reaching
        // buildInvokeStatic. This fixture asserts that expansion happens.
        list.add(new Scenario(
                "gh59-Before-static-args-long-wide-expansion",
                advice("b3", "before",
                        "call(public static void Thread.sleep(long)) && args(millis)",
                        List.of(new ParameterDescriptor("long", "millis")),
                        null, null, "sleepEvent", List.of("millis")),
                staticMatch(/*arg0=*/ 8, /*$return=*/ -1),
                List.of("J"),
                // arg00 binds to v8 (low half); the emitted invoke MUST place
                // the wide pair (v8, v9) in the operand list so the verifier
                // sees a contiguous 2-slot wide.
                new int[]{8, 9}
        ));

        // ----- AfterReturning × static × move-result-wide (long return) -----
        // call(public static long System.currentTimeMillis())
        // The synthetic key $return stores the LOW register of the wide pair.
        list.add(new Scenario(
                "AfterReturning-static-wide-return",
                advice("ar3", "after",
                        "call(public static long System.currentTimeMillis())",
                        java.util.Collections.emptyList(),
                        List.of(new ParameterDescriptor("long", "now")),
                        null, "currentTimeMillisEvent", List.of("now")),
                staticMatch(/*arg0=*/ -1, /*$return=*/ 6),
                List.of("J"),
                // gh59: $return stores the LOW register (v6) of the wide pair;
                // the emitted invoke MUST forward (v6, v7) — same wide-expansion
                // rule applied to `args` paths. Previous expectation [6] was
                // asserting malformed bytecode that the verifier would reject
                // (the slot count mismatch was just masked at runtime because
                // no APK in the gh52/gh56 datasets used a returning(long)
                // monitored event).
                new int[]{6, 7}
        ));

        // ----- AfterThrowing × virtual × throwing(name) -----
        // call(public Object Iterator.next()) && target(it). throwing(t)
        // is the catch-handler register (placeholder 0, rewritten by
        // RegisterShifter post-allocation — see resolveBindings comment).
        list.add(new Scenario(
                "AfterThrowing-virtual-throwing",
                advice("at1", "after",
                        "call(public Object Iterator.next()) && target(it)",
                        List.of(new ParameterDescriptor("Iterator", "it")),
                        null,
                        List.of(new ParameterDescriptor("Exception", "t")),
                        "nextThrewEvent", List.of("t")),
                virtualMatch(/*receiver=*/ 2, /*arg0=*/ 2, /*$return=*/ -1),
                List.of("Ljava/lang/Exception;"),
                new int[]{0}
        ));

        return list.stream();
    }

    private static Map<String, Integer> orderedMap(String k1, int v1, String k2, int v2) {
        Map<String, Integer> m = new LinkedHashMap<>();
        m.put(k1, v1);
        m.put(k2, v2);
        return m;
    }

    // -------------------------------------------------------------------------

    @ParameterizedTest(name = "{0}")
    @MethodSource("scenarios")
    void emittedInvokeMatchesExpectedRegistersInMonitorSignatureOrder(Scenario s) {
        TypeResolver resolver = new TypeResolver(List.of(
                "java.util.Iterator", "java.util.Collection", "java.util.Map",
                "java.security.MessageDigest", "javax.crypto.spec.SecretKeySpec"));
        EmitContext ctx = new EmitContext(s.advice, s.match, resolver, MONITOR_OWNER);

        List<BuilderInstruction> emit = MonitorInvokeBuilder.buildInvoke(ctx);
        assertNotNull(emit, "buildInvoke must succeed for the scenario fixture: " + s.name);
        assertEquals(1, emit.size(), "exactly one invoke-static instruction expected");
        BuilderInstruction insn = emit.get(0);

        // Extract emitted registers. The builder selects Format35c when all
        // regs <= v15 and count <= 5; Format3rc otherwise.
        int[] emittedRegs;
        MethodReference monitorRef;
        if (insn instanceof BuilderInstruction35c) {
            BuilderInstruction35c i35 = (BuilderInstruction35c) insn;
            int n = i35.getRegisterCount();
            emittedRegs = new int[n];
            if (n > 0) emittedRegs[0] = i35.getRegisterC();
            if (n > 1) emittedRegs[1] = i35.getRegisterD();
            if (n > 2) emittedRegs[2] = i35.getRegisterE();
            if (n > 3) emittedRegs[3] = i35.getRegisterF();
            if (n > 4) emittedRegs[4] = i35.getRegisterG();
            monitorRef = (MethodReference) i35.getReference();
        } else if (insn instanceof BuilderInstruction3rc) {
            BuilderInstruction3rc i3rc = (BuilderInstruction3rc) insn;
            int n = i3rc.getRegisterCount();
            emittedRegs = new int[n];
            for (int k = 0; k < n; k++) emittedRegs[k] = i3rc.getStartRegister() + k;
            monitorRef = (MethodReference) i3rc.getReference();
        } else {
            throw new AssertionError("unexpected instruction format: " + insn.getClass());
        }

        // (1) Register correspondence — the canonical anti-regression assertion.
        assertEquals(Arrays.toString(s.expectedRegisters),
                Arrays.toString(emittedRegs),
                "emitted register array MUST match monitorCall.args order "
                        + "(see INV-INS-71 + docs/20260514_erro.md). scenario=" + s.name);

        // (2) Type correspondence — independent of the builder's parser.
        List<? extends CharSequence> emittedParamTypes = monitorRef.getParameterTypes();
        assertEquals(s.expectedTypeOrder.size(), emittedParamTypes.size(),
                "monitor signature parameter count must match expected type order");
        for (int i = 0; i < s.expectedTypeOrder.size(); i++) {
            assertEquals(s.expectedTypeOrder.get(i),
                    emittedParamTypes.get(i).toString(),
                    "type at slot " + i + " (register v" + emittedRegs[i]
                            + ") must match the hand-written fixture type");
        }
    }

    // -------------------------------------------------------------------------
    // Task 3.4 extension: args(name) unresolved must trigger
    // UnresolvedBindingException (which DexWeaver translates to
    // plansSkippedUnresolvedBinding++ at the funnel).
    // -------------------------------------------------------------------------

    @Test
    void unresolvedArgsBindingTriggersUnresolvedBindingException() {
        AdviceDescriptor a = advice("u1", "before",
                "call(public SSLContext.init(KeyManager[], TrustManager[], SecureRandom)) "
                        + "&& args(km, tm, prng)",
                List.of(new ParameterDescriptor("KeyManager[]", "km"),
                        new ParameterDescriptor("TrustManager[]", "tm"),
                        new ParameterDescriptor("SecureRandom", "prng")),
                null, null, "initEvent", List.of("km", "tm", "prng"));
        // Matcher resolved arg00 and arg01 but NOT arg02 (e.g. obfuscator-
        // rewritten descriptor). The new contract forbids substituting v0
        // for prng — must throw UnresolvedBindingException.
        Map<String, Integer> partial = new LinkedHashMap<>();
        partial.put("arg00", 4);
        partial.put("arg01", 5);
        Match match = new Match(partial, /*receiver=*/ 3, null, false);
        TypeResolver resolver = new TypeResolver(List.of(
                "javax.net.ssl.SSLContext",
                "javax.net.ssl.KeyManager", "javax.net.ssl.TrustManager",
                "java.security.SecureRandom"));
        EmitContext ctx = new EmitContext(a, match, resolver, MONITOR_OWNER);

        MonitorInvokeBuilder.UnresolvedBindingException ex = assertThrows(
                MonitorInvokeBuilder.UnresolvedBindingException.class,
                () -> MonitorInvokeBuilder.buildInvoke(ctx));
        assertEquals("u1", ex.adviceName);
        assertEquals("prng", ex.bindingName,
                "the unresolved binding name surfaced for operator logging");
    }

    @Test
    void unresolvedReturningBindingTriggersUnresolvedBindingException() {
        // Non-constructor advice with returning(name), but Match has no
        // $return key (the original invoke discarded the return value, no
        // move-result*). Must throw, NOT substitute v0.
        AdviceDescriptor a = advice("u2", "after",
                "call(public void Cipher.init(int, Key)) && args(opmode, key)",
                List.of(new ParameterDescriptor("int", "opmode"),
                        new ParameterDescriptor("Key", "key")),
                List.of(new ParameterDescriptor("Object", "unused")),
                null, "initEvent",
                List.of("opmode", "key", "unused"));
        // No $return key in Match.argBindings.
        Map<String, Integer> partial = new LinkedHashMap<>();
        partial.put("arg00", 3);
        partial.put("arg01", 4);
        Match match = new Match(partial, /*receiver=*/ 2, null, /*isConstructor*/ false);
        TypeResolver resolver = new TypeResolver(List.of(
                "javax.crypto.Cipher", "java.security.Key"));
        EmitContext ctx = new EmitContext(a, match, resolver, MONITOR_OWNER);

        MonitorInvokeBuilder.UnresolvedBindingException ex = assertThrows(
                MonitorInvokeBuilder.UnresolvedBindingException.class,
                () -> MonitorInvokeBuilder.buildInvoke(ctx));
        assertEquals("unused", ex.bindingName);
    }

    // -------------------------------------------------------------------------
    // Task 3.4 extension: returning(name) with high registers (>v15) forces
    // Format35c → Format3rc escalation while preserving register identity.
    // -------------------------------------------------------------------------

    @Test
    void highRegisterReturningEscalatesToFormat3rcPreservingRegisterIdentity() {
        AdviceDescriptor a = advice("hr1", "after",
                "call(public KeyGenerator.generateKey())",
                java.util.Collections.emptyList(),
                List.of(new ParameterDescriptor("SecretKey", "key")),
                null, "generateKeyEvent", List.of("key"));
        // High register (v20) for the move-result destination. Single-arg
        // monitor → Format35c can encode (regs[0] <= v15 required), so v20
        // triggers escalation.
        Match match = virtualMatch(/*receiver=*/ 10, /*arg0=*/ -1, /*$return=*/ 20);
        TypeResolver resolver = new TypeResolver(List.of(
                "javax.crypto.KeyGenerator", "javax.crypto.SecretKey"));
        EmitContext ctx = new EmitContext(a, match, resolver, MONITOR_OWNER);

        List<BuilderInstruction> emit = MonitorInvokeBuilder.buildInvoke(ctx);
        assertNotNull(emit);
        BuilderInstruction insn = emit.get(0);
        assertTrue(insn instanceof BuilderInstruction3rc,
                "high register MUST escalate to Format3rc (single arg, contiguous trivially)");
        BuilderInstruction3rc i3rc = (BuilderInstruction3rc) insn;
        assertEquals(20, i3rc.getStartRegister(),
                "binding 'key' must resolve to v20 — register identity preserved across escalation");
        assertEquals(1, i3rc.getRegisterCount());
        assertFalse(insn instanceof BuilderInstruction35c,
                "Format35c cannot encode v20 (4-bit field); MUST be 3rc");
    }
}
