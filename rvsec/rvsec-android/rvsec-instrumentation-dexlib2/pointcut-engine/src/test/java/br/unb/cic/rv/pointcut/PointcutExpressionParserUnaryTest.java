package br.unb.cic.rv.pointcut;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Batch B — unary negation &amp; grouping scenarios for {@link PointcutExpressionParser}.
 *
 * <p>{@code parseUnary} handles the leading {@code '!'} with three distinct
 * outcomes, each locked here:
 * <ul>
 *   <li>{@code !target(Type)} / {@code !args(Type)} — the inner primary is parsed
 *       so it carries its resolved type, then wrapped in a {@link NegationPC} the
 *       matcher inverts (L90-93);</li>
 *   <li>a {@code '!'} before a {@code target}/{@code args} keyword that is NOT a
 *       proper {@code target(...)}/{@code args(...)} primary falls back to a
 *       lossy {@link NamedRefPC} preserving the {@code "!"} prefix (L92-false → L95);</li>
 *   <li>a {@code '!'} over any OTHER primary (execution/call/group) keeps the same
 *       {@code NamedRefPC("!" + text)} fallback (L100-101).</li>
 * </ul>
 * Plus the grouping/precedence guarantee that {@code '!'} binds tighter than
 * {@code &&} and {@code ||}. Each negative/edge assertion is paired with the
 * un-negated positive control so the boundary is documented, not just the branch lit.
 */
class PointcutExpressionParserUnaryTest {

    @Test
    void negatedTargetAndArgsTypeBecomeNegationPC() {
        // "!target(Cipher)": parseUnary sees '!', peekKeyword("target"), parses the
        // inner primary (a type-form TargetPC because "Cipher" is capitalized), and
        // wraps it in NegationPC (L90-93). Same for "!args(Cipher)" -> Negation(ArgsPC).
        // The NegationPC preserves the inner node verbatim so §4.N can invert the
        // subtype-aware receiver/arg test.
        NegationPC negTarget = assertInstanceOf(NegationPC.class,
                PointcutExpressionParser.parse("!target(Cipher)"));
        TargetPC innerTarget = assertInstanceOf(TargetPC.class, negTarget.inner());
        assertEquals("Cipher", innerTarget.type());

        NegationPC negArgs = assertInstanceOf(NegationPC.class,
                PointcutExpressionParser.parse("!args(Cipher)"));
        assertInstanceOf(ArgsPC.class, negArgs.inner());

        // Positive control: without '!', the same bodies are the bare Target/Args
        // nodes — no NegationPC wrapper.
        assertInstanceOf(TargetPC.class, PointcutExpressionParser.parse("target(Cipher)"));
        assertInstanceOf(ArgsPC.class, PointcutExpressionParser.parse("args(Cipher)"));
    }

    @Test
    void negatedBareTargetArgsKeywordFallsBackToNamedRef() {
        // A '!' before a target/args keyword that is NOT followed by '(' cannot
        // produce a TargetPC/ArgsPC: parsePrimary returns a bare NamedRefPC for a
        // paren-less keyword, so parseUnary's inner-instanceof check fails and it
        // falls back to NamedRefPC("!" + text) (L92-false → L95). This documents
        // that a truncated "!target"/"!args" degrades gracefully rather than throwing.
        NamedRefPC t = assertInstanceOf(NamedRefPC.class,
                PointcutExpressionParser.parse("!target"));
        assertTrue(t.name().startsWith("!"), t.name());
        NamedRefPC a = assertInstanceOf(NamedRefPC.class,
                PointcutExpressionParser.parse("!args"));
        assertTrue(a.name().startsWith("!"), a.name());

        // Positive control: WITH parens, "!target(x)" is a NegationPC over a
        // binding-form TargetPC ("x" is a lowercase binding name).
        assertInstanceOf(NegationPC.class, PointcutExpressionParser.parse("!target(x)"));
    }

    @Test
    void negatedNonTargetPrimariesWrapInNamedRef() {
        // '!' over any primary that is not within/target/args keeps the lossy
        // NamedRef fallback preserving the inner text (L100-101): "!execution(...)",
        // "!call(...)" and a negated group "!(within(x))" all become NamedRefPC
        // whose name starts with '!'. rv-monitor-generated expressions rarely hit
        // this arm, but it must never abort parsing.
        for (String neg : new String[]{"!execution(* *.*(..))", "!call(void T.m())", "!(within(x))"}) {
            NamedRefPC n = assertInstanceOf(NamedRefPC.class,
                    PointcutExpressionParser.parse(neg), "for [" + neg + "]");
            assertTrue(n.name().startsWith("!"), n.name());
        }

        // Positive control: the un-negated forms are their own node types.
        assertInstanceOf(ExecutionPC.class,
                PointcutExpressionParser.parse("execution(* *.*(..))"));
        assertInstanceOf(WithinPC.class, PointcutExpressionParser.parse("(within(x))"));
    }

    @Test
    void negationBindsTighterThanConjunctionAndDisjunction() {
        // '!' is a unary that binds tighter than '&&'/'||' because parseAnd/parseOr
        // invoke parseUnary for EACH operand. "!within(a) && target(t)" parses as
        // (NotWithinPC a) && (TargetPC t) — the '!' scopes only within(a), NOT the
        // whole conjunction.
        CombinedPC and = assertInstanceOf(CombinedPC.class,
                PointcutExpressionParser.parse("!within(a) && target(t)"));
        assertEquals(CombinedPC.Op.AND, and.op());
        assertInstanceOf(NotWithinPC.class, and.left());
        assertInstanceOf(TargetPC.class, and.right());

        // Both operands negated, then '||' at the top: "!target(A) && !args(B) || within(c)"
        // parses as ((¬Target A) && (¬Args B)) || within(c) — '&&' groups tighter
        // than '||', and each negation stays scoped to its single primary.
        CombinedPC or = assertInstanceOf(CombinedPC.class,
                PointcutExpressionParser.parse("!target(A) && !args(B) || within(c)"));
        assertEquals(CombinedPC.Op.OR, or.op());
        CombinedPC leftAnd = assertInstanceOf(CombinedPC.class, or.left());
        assertEquals(CombinedPC.Op.AND, leftAnd.op());
        assertInstanceOf(NegationPC.class, leftAnd.left());
        assertInstanceOf(NegationPC.class, leftAnd.right());
        assertInstanceOf(WithinPC.class, or.right());
    }
}
