package br.unb.cic.rv.pointcut;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Batch D — {@code call()} signature decomposition for {@link PointcutExpressionParser}.
 *
 * <p>Once {@code parseCallBody} has a balanced body it decomposes it with three
 * index-arithmetic helpers, each locked here around a boundary condition:
 * <ul>
 *   <li>{@code stripModifiers} — peels leading access/other modifiers but must not
 *       mistake a type/name that merely STARTS with a modifier spelling for one;</li>
 *   <li>{@code indexOfOwnerDotNew} — locates {@code <owner>.new(} for the constructor
 *       form and must not be fooled by a {@code ".new"} substring inside a name;</li>
 *   <li>{@code splitParams} — records a trailing {@code '+'} on a head param as the
 *       AspectJ subtype marker while dropping it from the descriptor.</li>
 * </ul>
 * Each test pairs the edge with a positive control that flips the decision.
 */
class PointcutExpressionParserCallSignatureTest {

    @Test
    void modifierStrippingHandlesPrefixCollisionsAndMultipleModifiers() {
        // stripModifiers only peels a modifier word when it is followed by
        // whitespace (L301-302), so a return type/name that merely STARTS with a
        // modifier spelling is left intact:
        //   "call(privateStuff a.b.C.m(int))" -> "privateStuff" starts with
        //       "private" but the next char 'S' is not whitespace, so it is NOT
        //       stripped and becomes the RETURN TYPE.
        //   "call(public static void a.b.C.m())" -> "public" then "static" peeled
        //       across two do-while passes, leaving "void a.b.C.m()".
        CallPC collide = assertInstanceOf(CallPC.class,
                PointcutExpressionParser.parse("call(privateStuff a.b.C.m(int))"));
        assertEquals("privateStuff", collide.returnType());
        assertEquals("a.b.C", collide.declaringType());
        assertEquals("m", collide.methodName());

        CallPC multi = assertInstanceOf(CallPC.class,
                PointcutExpressionParser.parse("call(public static void a.b.C.m())"));
        assertEquals("void", multi.returnType());
        assertEquals("a.b.C", multi.declaringType());
        assertEquals("m", multi.methodName());

        // A body that is EXACTLY a modifier with nothing after (length == modifier
        // length, L301) is not stripped and then fails as a malformed signature —
        // documents that a lone "public" is not a call() body.
        assertThrows(PointcutParseException.class,
                () -> PointcutExpressionParser.parse("call(public)"));
    }

    @Test
    void constructorNewDetectionDistinguishesRealCtorsFromNewSubstrings() {
        // indexOfOwnerDotNew locates "<owner>.new(" and must not be fooled by a
        // ".new" substring that is NOT a constructor call:
        //   "call(Foo.new(int))"           -> constructor: '(' immediately after .new;
        //   "call(Foo.new (int))"          -> constructor: whitespace between .new
        //                                     and '(' is skipped by the ws-scan loop (L320);
        //   "call(void a.newList.build())" -> NOT a constructor: the ".new" inside
        //                                     "newList" is followed by 'L' (not '('),
        //                                     so the search retries, finds no real
        //                                     ".new(", and falls to the method form.
        CallPC ctor = assertInstanceOf(CallPC.class,
                PointcutExpressionParser.parse("call(Foo.new(int))"));
        assertTrue(ctor.isConstructor());
        assertEquals("Foo", ctor.declaringType());
        assertEquals("<init>", ctor.methodName());
        assertEquals("int", ctor.paramSpecs().get(0).descriptor());

        CallPC ctorSpaced = assertInstanceOf(CallPC.class,
                PointcutExpressionParser.parse("call(Foo.new (int))"));
        assertTrue(ctorSpaced.isConstructor());
        assertEquals("Foo", ctorSpaced.declaringType());

        CallPC method = assertInstanceOf(CallPC.class,
                PointcutExpressionParser.parse("call(void a.newList.build())"));
        assertFalse(method.isConstructor());
        assertEquals("a.newList", method.declaringType());
        assertEquals("build", method.methodName());

        // ".new" at the very end of the body (nothing after) short-circuits the
        // paren-check (L321), the search returns -1, and it degrades to the method
        // form which fails as malformed (no return-type space).
        assertThrows(PointcutParseException.class,
                () -> PointcutExpressionParser.parse("call(Foo.new)"));
    }

    @Test
    void paramSubtypeMarkerCapturedInParamSpec() {
        // splitParams strips a trailing '+' from a head param and records it as the
        // AspectJ subtype marker in ParamSpec (L366-369); the stored descriptor drops
        // the '+'. "call(void T.m(Cipher+, int))" -> param0 "Cipher" isSubtype=true,
        // param1 "int" isSubtype=false. This is the '+' arm that array/plain params
        // (positive control) never trigger.
        CallPC c = assertInstanceOf(CallPC.class,
                PointcutExpressionParser.parse("call(void T.m(Cipher+, int))"));
        assertEquals(2, c.paramSpecs().size());
        assertEquals("Cipher", c.paramSpecs().get(0).descriptor());
        assertTrue(c.paramSpecs().get(0).isSubtype());
        assertEquals("int", c.paramSpecs().get(1).descriptor());
        assertFalse(c.paramSpecs().get(1).isSubtype());

        // Positive control: an array param keeps its literal descriptor and is NEVER
        // marked subtype (the '[]' is not a '+').
        CallPC arr = assertInstanceOf(CallPC.class,
                PointcutExpressionParser.parse("call(void T.m(byte[]))"));
        assertEquals("byte[]", arr.paramSpecs().get(0).descriptor());
        assertFalse(arr.paramSpecs().get(0).isSubtype());
    }
}
