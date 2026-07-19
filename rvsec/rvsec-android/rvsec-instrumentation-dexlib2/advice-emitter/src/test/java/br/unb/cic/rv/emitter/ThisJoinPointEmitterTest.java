package br.unb.cic.rv.emitter;

import br.unb.cic.rv.descriptor.AdviceDescriptor;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Covers the whole {@link ThisJoinPointEmitter} helper — the stateless
 * signature/join-point probe used by the call-site emitters. The class was
 * previously untouched by any test (12.5% instruction coverage), so both
 * methods and every null/contains branch were dark.
 *
 * <p>Two decisions are locked here:
 * <ul>
 *   <li>{@link ThisJoinPointEmitter#signatureFor} is the deliberate Q5
 *       pass-through: it forwards the advice's raw pointcut expression
 *       verbatim and normalises a {@code null} expression to the empty
 *       string (never {@code null}), because a downstream emitter would
 *       NPE if it received {@code null} where a signature constant is
 *       expected.</li>
 *   <li>{@link ThisJoinPointEmitter#needsJoinPoint} is a pure substring
 *       probe on {@code "thisJoinPoint"} that must tolerate a {@code null}
 *       expression without throwing — a descriptor may legally omit the
 *       expression, and the caller only wants a yes/no on whether the
 *       join-point machinery has to be threaded through.</li>
 * </ul>
 *
 * <p>Each negative assertion carries a positive control in the same test so
 * a {@code false}/empty result cannot pass for the wrong reason (e.g. the
 * probe silently swallowing every input).
 */
class ThisJoinPointEmitterTest {

    private final ThisJoinPointEmitter emitter = new ThisJoinPointEmitter();

    private static AdviceDescriptor adviceWithExpression(String expression) {
        AdviceDescriptor advice = new AdviceDescriptor();
        advice.setExpression(expression);
        return advice;
    }

    @Test
    void signatureForForwardsExpressionVerbatim() {
        // A concrete pointcut expression must be returned unchanged — the helper
        // is a pass-through, not a formatter. If it ever rewrote the string the
        // constant threaded into the monitor invoke would drift from the source.
        String expression = "call(public static Cipher Cipher.getInstance(String)) && args(transformation)";
        AdviceDescriptor advice = adviceWithExpression(expression);

        assertEquals(expression, emitter.signatureFor(advice));
    }

    @Test
    void signatureForNormalisesNullExpressionToEmptyString() {
        // A descriptor with no expression must yield "" (never null): a downstream
        // emitter treats the result as a signature constant and would NPE on null.
        // Positive control: a non-null expression still round-trips, so the empty
        // result below is the null-branch, not a blanket "".
        AdviceDescriptor noExpression = adviceWithExpression(null);
        AdviceDescriptor withExpression = adviceWithExpression("call(void X.y())");

        assertEquals("", emitter.signatureFor(noExpression));
        assertEquals("call(void X.y())", emitter.signatureFor(withExpression));
    }

    @Test
    void needsJoinPointTrueOnlyWhenExpressionMentionsThisJoinPoint() {
        // The probe is a plain substring test. It must be true when the advice
        // references thisJoinPoint (the join-point signature has to be delivered)
        // and false for an ordinary expression that does not.
        AdviceDescriptor withToken =
                adviceWithExpression("call(void X.y()) && this(o) && thisJoinPoint");
        AdviceDescriptor withoutToken =
                adviceWithExpression("call(void X.y()) && args(a)");

        assertTrue(emitter.needsJoinPoint(withToken));
        assertFalse(emitter.needsJoinPoint(withoutToken));
    }

    @Test
    void needsJoinPointFalseOnNullExpressionWithoutThrowing() {
        // A null expression is legal and must short-circuit to false (the &&
        // guards the contains() call from an NPE). Positive control: an expression
        // that DOES contain the token still returns true, proving the false above
        // came from the null-guard and not from a broken substring check.
        AdviceDescriptor noExpression = adviceWithExpression(null);
        AdviceDescriptor withToken = adviceWithExpression("thisJoinPoint.getSignature()");

        assertFalse(emitter.needsJoinPoint(noExpression));
        assertTrue(emitter.needsJoinPoint(withToken));
    }
}
