package br.unb.cic.rv.pointcut;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Batch A — malformed-input rejection scenarios for {@link PointcutExpressionParser}.
 *
 * <p>The parser is fail-closed: a structurally illegal pointcut string must raise
 * {@link PointcutParseException} with a message that names the defect, rather than
 * silently producing a partial/wrong AST that would corrupt weaving downstream.
 * Every rejection here is paired with a POSITIVE CONTROL — the same-shape VALID
 * expression that DOES parse — so each test documents the boundary, not just the
 * failure. This locks the exact throw sites of {@code parse}, {@code parsePrimary},
 * {@code parseCallBody}, {@code expectChar} and {@code readParenBody}.
 *
 * <p>Not exercised here (deliberately, per the confidence-not-coverage rule): the
 * defensive throws in {@code matchingClose} (L338), {@code consume} (L403) and
 * {@code consumeKeyword} (L411). They are unreachable through the public
 * {@link PointcutExpressionParser#parse} entry point — {@code readParenBody}
 * pre-balances every keyword body before {@code matchingClose} ever runs, and
 * {@code consume}/{@code consumeKeyword} are only invoked immediately after a
 * matching {@code peekOp}/{@code peekKeyword} has already confirmed the token.
 */
class PointcutExpressionParserRejectionTest {

    @Test
    void emptyBlankAndNullExpressionsRejected() {
        // parse() fails closed BEFORE any grammar work on a non-substantive input:
        // null, "" and whitespace-only strings all hit the same guard
        // (expression == null || expression.isBlank(), L38-39) and must yield the
        // literal "empty pointcut expression". Covers both arms of that guard
        // (the null arm and the isBlank arm on a non-empty whitespace string).
        // Positive control: the minimal valid "within(x)" parses to a WithinPC.
        for (String bad : new String[]{null, "", "   ", "\t\n"}) {
            PointcutParseException ex = assertThrows(PointcutParseException.class,
                    () -> PointcutExpressionParser.parse(bad),
                    "expected rejection for [" + bad + "]");
            assertTrue(ex.getMessage().contains("empty pointcut expression"),
                    "message must name the defect, was: " + ex.getMessage());
        }
        assertInstanceOf(WithinPC.class, PointcutExpressionParser.parse("within(x)"));
    }

    @Test
    void trailingCharactersAfterCompleteExpressionRejected() {
        // A fully-formed pointcut followed by leftover tokens is rejected: parseOr
        // consumes "within(x)", then parse() sees pos < length and throws
        // "trailing characters at offset 10" (L44-46). The "garbage" token at
        // offset 10 is never consumed by the grammar.
        // Positive control: the same "within(x)" WITHOUT the trailing token parses.
        PointcutParseException ex = assertThrows(PointcutParseException.class,
                () -> PointcutExpressionParser.parse("within(x) garbage"));
        assertTrue(ex.getMessage().contains("trailing characters"),
                "message must name the defect, was: " + ex.getMessage());
        assertInstanceOf(WithinPC.class, PointcutExpressionParser.parse("within(x)"));
    }

    @Test
    void danglingOperatorAndBareBangRejected() {
        // parsePrimary hits pos >= length with nothing left to parse (L108-109) and
        // throws "unexpected end of expression". Two entry points:
        //   "!"            -> parseUnary consumes '!', matches no within/target/args
        //                     specialization, then parsePrimary finds end-of-input;
        //   "within(x) &&" -> parseAnd consumes "&&", then parseUnary -> parsePrimary
        //                     finds end-of-input (no right operand).
        // Positive control: "!within(x)" (a COMPLETE negation) parses to NotWithinPC.
        for (String bad : new String[]{"!", "within(x) &&"}) {
            PointcutParseException ex = assertThrows(PointcutParseException.class,
                    () -> PointcutExpressionParser.parse(bad),
                    "expected rejection for [" + bad + "]");
            assertTrue(ex.getMessage().contains("unexpected end of expression"),
                    "message must name the defect, was: " + ex.getMessage());
        }
        assertInstanceOf(NotWithinPC.class, PointcutExpressionParser.parse("!within(x)"));
    }

    @Test
    void nonKeywordLeadingTokenRejected() {
        // A leading char that is neither '(' nor an identifier part makes
        // readKeyword() return "", so parsePrimary throws "expected pointcut keyword
        // at offset" (L118-121). "%", "-nope" and "?x" all open on a non-ident
        // symbol. (isIdentPart accepts letters/digits/_/$/. — so these symbols do
        // not start a keyword.)
        // Positive control: "within(x)" opens on a real keyword and parses.
        for (String bad : new String[]{"%", "-nope", "?x"}) {
            PointcutParseException ex = assertThrows(PointcutParseException.class,
                    () -> PointcutExpressionParser.parse(bad),
                    "expected rejection for [" + bad + "]");
            assertTrue(ex.getMessage().contains("expected pointcut keyword"),
                    "message must name the defect, was: " + ex.getMessage());
        }
        assertInstanceOf(WithinPC.class, PointcutExpressionParser.parse("within(x)"));
    }

    @Test
    void malformedCallBodiesRejected() {
        // parseCallBody rejects three distinct structural defects in the call()
        // signature, each with its own diagnostic but all in the "not a legal
        // call() signature" family (all contain "malformed call() body"):
        //   "call(foo)"           -> no space and no ".new(" -> nothing to split a
        //                            return type from an owner.method (L189-190);
        //   "call(void foo.bar)"  -> a return type is present but the remainder has
        //                            no '(' to open a parameter list (L195-196);
        //   "call(void foo(int))" -> a '(' is present but the member "foo" carries
        //                            no owner '.' before it (L203-204).
        // Positive control: "call(void a.b.C.m(int))" — return type + qualified
        // owner + method + params — parses to a method CallPC (NOT constructor),
        // splitting on the LAST '.' so declaringType is "a.b.C" and method is "m".
        PointcutParseException noSpace = assertThrows(PointcutParseException.class,
                () -> PointcutExpressionParser.parse("call(foo)"));
        assertTrue(noSpace.getMessage().contains("malformed call() body"),
                noSpace.getMessage());

        PointcutParseException noParen = assertThrows(PointcutParseException.class,
                () -> PointcutExpressionParser.parse("call(void foo.bar)"));
        assertTrue(noParen.getMessage().contains("malformed call() body")
                        && noParen.getMessage().contains("no '('"),
                noParen.getMessage());

        PointcutParseException noOwner = assertThrows(PointcutParseException.class,
                () -> PointcutExpressionParser.parse("call(void foo(int))"));
        assertTrue(noOwner.getMessage().contains("malformed call() body")
                        && noOwner.getMessage().contains("no owner.method"),
                noOwner.getMessage());

        CallPC ok = assertInstanceOf(CallPC.class,
                PointcutExpressionParser.parse("call(void a.b.C.m(int))"));
        assertFalse(ok.isConstructor());
        assertEquals("a.b.C", ok.declaringType());
        assertEquals("m", ok.methodName());
        assertEquals("void", ok.returnType());
    }

    @Test
    void unclosedGroupAndParenlessWithinRejected() {
        // expectChar fails closed at two structural spots (both L416-419):
        //   "(within(x)"  -> parsePrimary opens a '(' group, parses within(x), then
        //                    expectChar(')') finds end-of-input -> "expected ')'";
        //   "!within foo" -> the !within specialization calls readParenBody, whose
        //                    expectChar('(') finds 'f' (no opening paren) -> "expected '('".
        // These hit the two distinct branches of expectChar's guard (pos >= length
        // vs. char mismatch) at its two distinct call sites (group close vs. body open).
        // Positive controls: "(within(x))" (balanced group) -> WithinPC;
        // "!within(foo)" (parenthesized negation) -> NotWithinPC.
        PointcutParseException unclosed = assertThrows(PointcutParseException.class,
                () -> PointcutExpressionParser.parse("(within(x)"));
        assertTrue(unclosed.getMessage().contains("expected ')'"), unclosed.getMessage());

        PointcutParseException parenless = assertThrows(PointcutParseException.class,
                () -> PointcutExpressionParser.parse("!within foo"));
        assertTrue(parenless.getMessage().contains("expected '('"), parenless.getMessage());

        assertInstanceOf(WithinPC.class, PointcutExpressionParser.parse("(within(x))"));
        assertInstanceOf(NotWithinPC.class, PointcutExpressionParser.parse("!within(foo)"));
    }

    @Test
    void unterminatedParenthesizedBodiesRejected() {
        // readParenBody scans for the balancing ')' and fails closed at end-of-input
        // with "unterminated parenthesized body at offset" (L452-453). Two entry
        // points reach it: a keyword body via dispatch ("call(void T.m(int" — the
        // inner '(' of the param list is never balanced) and the !within
        // specialization ("!within(sun..*" — the within body is never closed).
        // Positive controls: both closed forms parse (CallPC / NotWithinPC).
        for (String bad : new String[]{"call(void T.m(int", "!within(sun..*"}) {
            PointcutParseException ex = assertThrows(PointcutParseException.class,
                    () -> PointcutExpressionParser.parse(bad),
                    "expected rejection for [" + bad + "]");
            assertTrue(ex.getMessage().contains("unterminated parenthesized body"),
                    "message must name the defect, was: " + ex.getMessage());
        }
        assertInstanceOf(CallPC.class, PointcutExpressionParser.parse("call(void T.m(int))"));
        assertInstanceOf(NotWithinPC.class, PointcutExpressionParser.parse("!within(sun..*)"));
    }
}
