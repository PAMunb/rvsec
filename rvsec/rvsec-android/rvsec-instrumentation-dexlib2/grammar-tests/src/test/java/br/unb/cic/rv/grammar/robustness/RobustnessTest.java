package br.unb.cic.rv.grammar.robustness;

import br.unb.cic.rv.pointcut.PointcutExpressionParser;
import br.unb.cic.rv.pointcut.PointcutParseException;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Robustness scenarios for the dexlib2 pointcut parser: malformed / degenerate pointcut expressions
 * must fail loud with {@link PointcutParseException}, never silently produce a vacuous always-match
 * node. The fail-loud contract is what keeps the matrix honest — a construction the parser cannot
 * handle surfaces as an exception at instrumentation time, not as a silently-dropped match.
 *
 * <p>This class lives in the {@code br.unb.cic.rv.grammar.robustness} subpackage and is
 * <b>structurally excluded</b> from the INV-INS-92 matrix↔test bijection (§6.5): its tests assert
 * parser hygiene, not individual matrix rows, so they have no matrix-row counterpart by design.
 */
class RobustnessTest {

    @Test
    void emptyExpressionFailsLoud() {
        assertThrows(PointcutParseException.class, () -> PointcutExpressionParser.parse(""),
                "an empty pointcut expression must fail loud");
        assertThrows(PointcutParseException.class, () -> PointcutExpressionParser.parse("   "),
                "a blank pointcut expression must fail loud");
    }

    @Test
    void unbalancedParenthesesFailLoud() {
        assertThrows(PointcutParseException.class,
                () -> PointcutExpressionParser.parse("call(* Foo.bar(..)"),
                "a call() with an unbalanced paren must fail loud");
        assertThrows(PointcutParseException.class,
                () -> PointcutExpressionParser.parse("(call(* Foo.bar()) && target(x)"),
                "an unbalanced grouping paren must fail loud");
    }

    @Test
    void malformedCallBodyFailsLoud() {
        // A call() body with no method paren is structurally malformed.
        assertThrows(PointcutParseException.class,
                () -> PointcutExpressionParser.parse("call(java.lang.String foo)"),
                "a call() body with no method '(' must fail loud");
    }

    @Test
    void danglingCompositionOperatorFailsLoud() {
        assertThrows(PointcutParseException.class,
                () -> PointcutExpressionParser.parse("call(* Foo.bar()) &&"),
                "a trailing && with no right operand must fail loud");
    }

    @Test
    void wellFormedExpressionStillParses() {
        // The robustness guards must not over-reject: a canonical well-formed expression parses.
        var pc = PointcutExpressionParser.parse(
                "call(public boolean java.util.Iterator.hasNext()) && target(it)");
        assertTrue(pc != null, "a well-formed pointcut expression parses to a non-null node");
    }
}
