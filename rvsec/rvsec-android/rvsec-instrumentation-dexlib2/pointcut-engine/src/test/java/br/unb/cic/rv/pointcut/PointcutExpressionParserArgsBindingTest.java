package br.unb.cic.rv.pointcut;

import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Batch C — args/target element classification for {@link PointcutExpressionParser}.
 *
 * <p>A single heuristic, {@code isBindingName}, decides whether an {@code args(...)}
 * or {@code target(...)} element is a captured BINDING (a lowercase simple identifier —
 * inert at match time) or a TYPE pattern (capitalized, qualified, or wildcarded —
 * drives subtype-aware matching, §4.TT/§4.AT). These tests exercise every arm of
 * that classification and the parallel {@code names}/{@code types} views {@code args}
 * builds, always paired with a positive control that flips the decision.
 */
class PointcutExpressionParserArgsBindingTest {

    @Test
    void argsElementsClassifiedByBindingTypeWildcardVarargs() {
        // parseArgsBody keeps names[] as the legacy binding collector (every
        // non-empty, non-".." element, INCLUDING "*") and builds a parallel types[]
        // for the matcher, classifying each comma element:
        //   "o"      lowercase ident  -> binding      -> types[0] == null
        //   "Cipher" capitalized      -> type pattern -> types[1] == "Cipher"
        //   "*"      wildcard         -> accept-any   -> types[2] == "*"
        //   ".."     varargs sentinel -> types[3] == ".." AND excluded from names[]
        // "args(o, Cipher, *, ..)" packs all four arms into one body.
        ArgsPC a = assertInstanceOf(ArgsPC.class,
                PointcutExpressionParser.parse("args(o, Cipher, *, ..)"));
        assertEquals(List.of("o", "Cipher", "*"), a.names(),
                "'..' is not a binding and must not appear in names()");
        assertEquals(Arrays.asList(null, "Cipher", "*", ".."), a.types());
        assertTrue(a.hasTypeConstraint(), "the 'Cipher' element is a real type");

        // Positive control: an all-binding args carries NO type constraint, so the
        // matcher stays the always-match collector (types are all null).
        ArgsPC bindings = assertInstanceOf(ArgsPC.class,
                PointcutExpressionParser.parse("args(x, y)"));
        assertEquals(List.of("x", "y"), bindings.names());
        assertEquals(Arrays.asList(null, null), bindings.types());
        assertFalse(bindings.hasTypeConstraint());
    }

    @Test
    void qualifiedLowercaseNameIsTypeNotBinding() {
        // isBindingName rejects any element whose first char is lowercase but which
        // contains a non-ident char: a fully-qualified type in a lowercase package
        // ("javax.crypto.Cipher") starts with 'j' (lowercase) yet the '.' in the
        // loop (isBindingName L279-283) disqualifies it as a binding -> it is a TYPE.
        // This is the arm that separates a package-qualified type from a bare binding.
        ArgsPC a = assertInstanceOf(ArgsPC.class,
                PointcutExpressionParser.parse("args(javax.crypto.Cipher)"));
        assertEquals(Arrays.asList("javax.crypto.Cipher"), a.types());
        assertTrue(a.hasTypeConstraint());

        // Positive control: the SAME leading-lowercase spelling WITHOUT a dot
        // ("cipher") IS a binding -> null type, no constraint.
        ArgsPC binding = assertInstanceOf(ArgsPC.class,
                PointcutExpressionParser.parse("args(cipher)"));
        assertEquals(Arrays.asList((String) null), binding.types());
        assertFalse(binding.hasTypeConstraint());
    }

    @Test
    void targetElementClassifiedByBindingNameHeuristic() {
        // parseTargetBody routes through isBindingName too:
        //   "target(iterator)"            -> binding: name="iterator", type=null
        //   "target(Cipher)"              -> type: name=null, type="Cipher"
        //                                    (first char uppercase -> not a binding)
        //   "target(javax.crypto.Cipher)" -> type: lowercase-first but '.' rejects it
        //   "target()"                    -> empty body -> isBindingName("")==false
        //                                    (isEmpty guard) -> type("") fallback
        TargetPC binding = assertInstanceOf(TargetPC.class,
                PointcutExpressionParser.parse("target(iterator)"));
        assertEquals("iterator", binding.name());
        assertNull(binding.type());

        TargetPC simpleType = assertInstanceOf(TargetPC.class,
                PointcutExpressionParser.parse("target(Cipher)"));
        assertNull(simpleType.name());
        assertEquals("Cipher", simpleType.type());

        TargetPC qualifiedType = assertInstanceOf(TargetPC.class,
                PointcutExpressionParser.parse("target(javax.crypto.Cipher)"));
        assertNull(qualifiedType.name());
        assertEquals("javax.crypto.Cipher", qualifiedType.type());

        // Empty target() body: isBindingName("") short-circuits false on the isEmpty
        // guard, so it is treated as a (degenerate) type pattern, never a binding.
        TargetPC empty = assertInstanceOf(TargetPC.class,
                PointcutExpressionParser.parse("target()"));
        assertNull(empty.name());
        assertEquals("", empty.type());
    }
}
