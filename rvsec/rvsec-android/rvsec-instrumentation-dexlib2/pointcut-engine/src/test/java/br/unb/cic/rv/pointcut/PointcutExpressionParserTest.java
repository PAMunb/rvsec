package br.unb.cic.rv.pointcut;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class PointcutExpressionParserTest {

    // --- call(...) ----------------------------------------------------------

    @Test
    void parsesCallWithSimpleMethod() {
        PointcutExpression e = PointcutExpressionParser.parse(
                "call(public static Cipher Cipher.getInstance(String))");
        CallPC c = assertInstanceOf(CallPC.class, e);
        assertFalse(c.isConstructor());
        assertEquals("Cipher", c.returnType());
        assertEquals("Cipher", c.declaringType());
        assertEquals("getInstance", c.methodName());
        assertEquals(1, c.paramTypes().size());
        assertEquals("String", c.paramTypes().get(0));
        assertFalse(c.varargs());
    }

    @Test
    void parsesCallWithConstructor() {
        PointcutExpression e = PointcutExpressionParser.parse(
                "call(public CipherInputStream.new(InputStream, Cipher))");
        CallPC c = assertInstanceOf(CallPC.class, e);
        assertTrue(c.isConstructor());
        assertEquals("<init>", c.methodName());
        assertEquals("CipherInputStream", c.declaringType());
        assertEquals(2, c.paramTypes().size());
        assertEquals("InputStream", c.paramTypes().get(0));
        assertEquals("Cipher", c.paramTypes().get(1));
    }

    @Test
    void parsesCallWithNoArgs() {
        PointcutExpression e = PointcutExpressionParser.parse(
                "call(public int CipherInputStream.read())");
        CallPC c = assertInstanceOf(CallPC.class, e);
        assertEquals("read", c.methodName());
        assertEquals("int", c.returnType());
        assertEquals(0, c.paramTypes().size());
    }

    @Test
    void parsesCallWithArrayParam() {
        PointcutExpression e = PointcutExpressionParser.parse(
                "call(public int CipherInputStream.read(byte[], int, int))");
        CallPC c = assertInstanceOf(CallPC.class, e);
        assertEquals(3, c.paramTypes().size());
        assertEquals("byte[]", c.paramTypes().get(0));
    }

    @Test
    void parsesCallWithVarargs() {
        PointcutExpression e = PointcutExpressionParser.parse(
                "call(public void T.m(..))");
        CallPC c = assertInstanceOf(CallPC.class, e);
        assertTrue(c.varargs());
        assertEquals(0, c.paramTypes().size());
    }

    // --- execution(...) -----------------------------------------------------

    @Test
    void parsesExecutionCatchAll() {
        PointcutExpression e = PointcutExpressionParser.parse("execution(* *.*(..))");
        ExecutionPC ex = assertInstanceOf(ExecutionPC.class, e);
        assertEquals("* *.*(..)", ex.signaturePattern());
    }

    // --- args / target ------------------------------------------------------

    @Test
    void parsesArgs() {
        PointcutExpression e = PointcutExpressionParser.parse("args(arr, offset, len)");
        ArgsPC a = assertInstanceOf(ArgsPC.class, e);
        assertEquals(3, a.names().size());
        assertEquals("arr", a.names().get(0));
    }

    @Test
    void parsesArgsWithLeadingEllipsisDropped() {
        // JavaMOP sometimes emits "args(.., x, y)"; the ellipsis is not a binding.
        PointcutExpression e = PointcutExpressionParser.parse("args(.., x, y)");
        ArgsPC a = assertInstanceOf(ArgsPC.class, e);
        assertEquals(2, a.names().size());
    }

    @Test
    void parsesTarget() {
        PointcutExpression e = PointcutExpressionParser.parse("target(t)");
        TargetPC t = assertInstanceOf(TargetPC.class, e);
        assertEquals("t", t.name());
    }

    // --- within / !within ---------------------------------------------------

    @Test
    void parsesNotWithin() {
        PointcutExpression e = PointcutExpressionParser.parse("!within(sun..*)");
        NotWithinPC nw = assertInstanceOf(NotWithinPC.class, e);
        assertEquals("sun..*", nw.typePattern());
    }

    @Test
    void parsesPlainWithin() {
        PointcutExpression e = PointcutExpressionParser.parse("within(com.example..*)");
        WithinPC w = assertInstanceOf(WithinPC.class, e);
        assertEquals("com.example..*", w.typePattern());
    }

    // --- staticinitialization / if -----------------------------------------

    @Test
    void parsesStaticInitialization() {
        PointcutExpression e = PointcutExpressionParser.parse(
                "staticinitialization(javax.crypto.Cipher+)");
        StaticInitPC s = assertInstanceOf(StaticInitPC.class, e);
        assertEquals("javax.crypto.Cipher+", s.typePattern());
    }

    @Test
    void parsesIfGuard() {
        PointcutExpression e = PointcutExpressionParser.parse("if(x > 0)");
        IfPC i = assertInstanceOf(IfPC.class, e);
        assertEquals("x > 0", i.javaExpression());
    }

    // --- combinators -------------------------------------------------------

    @Test
    void parsesAnd() {
        PointcutExpression e = PointcutExpressionParser.parse(
                "call(public int T.m()) && args()");
        CombinedPC c = assertInstanceOf(CombinedPC.class, e);
        assertEquals(CombinedPC.Op.AND, c.op());
        assertInstanceOf(CallPC.class, c.left());
        assertInstanceOf(ArgsPC.class, c.right());
    }

    @Test
    void parsesOr() {
        PointcutExpression e = PointcutExpressionParser.parse(
                "call(public int T.a()) || call(public int T.b(int))");
        CombinedPC c = assertInstanceOf(CombinedPC.class, e);
        assertEquals(CombinedPC.Op.OR, c.op());
    }

    @Test
    void andBindsTighterThanOr() {
        // call(a) && target(t) || call(b)
        //   should parse as (call(a) && target(t)) || call(b)
        PointcutExpression e = PointcutExpressionParser.parse(
                "call(public int T.a()) && target(t) || call(public int T.b())");
        CombinedPC root = assertInstanceOf(CombinedPC.class, e);
        assertEquals(CombinedPC.Op.OR, root.op());
        CombinedPC leftAnd = assertInstanceOf(CombinedPC.class, root.left());
        assertEquals(CombinedPC.Op.AND, leftAnd.op());
    }

    @Test
    void parsesParenthesizedGroup() {
        PointcutExpression e = PointcutExpressionParser.parse(
                "(call(public int T.a()) || call(public int T.b())) && args()");
        CombinedPC root = assertInstanceOf(CombinedPC.class, e);
        assertEquals(CombinedPC.Op.AND, root.op());
        assertInstanceOf(CombinedPC.class, root.left());
    }

    // --- unknown / named references -----------------------------------------

    @Test
    void adviceExecutionBecomesNamedRef() {
        PointcutExpression e = PointcutExpressionParser.parse("adviceexecution()");
        NamedRefPC n = assertInstanceOf(NamedRefPC.class, e);
        assertEquals("adviceexecution()", n.name());
    }

    @Test
    void unknownKeywordFallsThroughToNamedRef() {
        PointcutExpression e = PointcutExpressionParser.parse("BaseAspect.notwithin()");
        NamedRefPC n = assertInstanceOf(NamedRefPC.class, e);
        assertTrue(n.name().contains("BaseAspect.notwithin"));
    }

    // --- real-world shape from the fixture ---------------------------------

    @Test
    void parsesRealFixtureExpressionShape() {
        // Shape drawn directly from the JCA descriptor fixture (CipherSpec_g1).
        String expr = "call(public static Cipher Cipher.getInstance(String)) && args(transformation)";
        PointcutExpression e = PointcutExpressionParser.parse(expr);
        CombinedPC root = assertInstanceOf(CombinedPC.class, e);
        assertEquals(CombinedPC.Op.AND, root.op());
        CallPC leftCall = assertInstanceOf(CallPC.class, root.left());
        assertEquals("getInstance", leftCall.methodName());
        ArgsPC rightArgs = assertInstanceOf(ArgsPC.class, root.right());
        assertEquals(1, rightArgs.names().size());
        assertEquals("transformation", rightArgs.names().get(0));
    }

    // --- error handling ----------------------------------------------------

    @Test
    void emptyExpressionFails() {
        assertThrows(PointcutParseException.class,
                () -> PointcutExpressionParser.parse(""));
    }

    @Test
    void unterminatedParenFails() {
        assertThrows(PointcutParseException.class,
                () -> PointcutExpressionParser.parse("call(public int T.m("));
    }
}
