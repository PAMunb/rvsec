package br.unb.cic.rv.pointcut;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Batch E — keyword-boundary integrity for {@link PointcutExpressionParser}.
 *
 * <p>{@code peekKeyword} matches a keyword ONLY when the character immediately
 * after it is not an identifier part (L393-398): {@code within}/{@code target}/
 * {@code args} must not be recognized inside a longer identifier that merely
 * starts with the same letters. This protects the {@code '!'}-negation dispatch
 * in {@code parseUnary} from mis-tokenizing e.g. {@code withinScope} as {@code within}.
 */
class PointcutExpressionParserKeywordBoundaryTest {

    @Test
    void keywordPrefixOfLongerIdentifierIsNotTheKeyword() {
        // peekKeyword enforces a token boundary: after matching the keyword letters
        // it checks the NEXT char is not an identifier part. So under '!':
        //   "!withinX(x)"    -> peekKeyword("within") is FALSE because the next char
        //                       'X' is an ident part, so this is NOT a NotWithinPC;
        //                       parseUnary falls to the generic fallback -> NamedRefPC("!...").
        //   "!targetType(x)" -> peekKeyword("target") is FALSE ('T' is an ident part),
        //                       so this is NOT a NegationPC over a TargetPC -> NamedRefPC.
        // This is the isIdentPart-true arm of peekKeyword's final guard — the branch
        // that keeps keyword recognition from bleeding into longer identifiers.
        assertInstanceOf(NamedRefPC.class,
                PointcutExpressionParser.parse("!withinX(x)"));
        assertInstanceOf(NamedRefPC.class,
                PointcutExpressionParser.parse("!targetType(x)"));

        // Positive controls: the EXACT keywords (boundary is a non-ident '(') are
        // recognized as their specialized nodes.
        assertInstanceOf(NotWithinPC.class,
                PointcutExpressionParser.parse("!within(x)"));
        assertInstanceOf(NegationPC.class,
                PointcutExpressionParser.parse("!target(x)"));
    }
}
