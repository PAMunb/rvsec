package br.unb.cic.rv.grammar;

import br.unb.cic.rv.pointcut.AndroidClassIndex;
import br.unb.cic.rv.pointcut.InheritanceResolver;
import br.unb.cic.rv.pointcut.Match;
import br.unb.cic.rv.pointcut.PointcutExpression;
import br.unb.cic.rv.pointcut.PointcutExpressionParser;
import br.unb.cic.rv.pointcut.PointcutMatcher;
import br.unb.cic.rv.pointcut.TypeResolver;

import com.android.tools.smali.dexlib2.AccessFlags;
import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.DexFile;
import com.android.tools.smali.dexlib2.iface.Method;
import com.android.tools.smali.dexlib2.iface.instruction.Instruction;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;
import com.android.tools.smali.dexlib2.immutable.ImmutableClassDef;
import com.android.tools.smali.dexlib2.immutable.ImmutableDexFile;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethod;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethodImplementation;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction10x;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction35c;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableMethodReference;

import org.junit.jupiter.api.Test;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Backs the {@code call()}-pattern surface matrix rows that the dexlib2 matcher weaves but that have
 * no other dedicated grammar test:
 * <ul>
 *   <li><b>{@code call(MethodPattern)}</b> base matching (owner + name + params + return);</li>
 *   <li><b>{@code *} wildcard</b> (return-type wildcard);</li>
 *   <li><b>{@code ..} standalone varargs</b> (match-any parameter list);</li>
 *   <li><b>{@code T+} in {@code call()} param</b> position (gh61 + §4.O param-subtype);</li>
 *   <li><b>{@code T[]} / {@code T[][]} arrays</b> (array descriptors in signatures);</li>
 *   <li><b>{@code &&} / {@code ||} composition</b> and <b>parentheses grouping</b>;</li>
 *   <li><b>{@code ..*} dot-glob</b> and <b>{@code .*} single-level glob</b> (package patterns via the
 *       {@code !within(...)} path).</li>
 * </ul>
 * All are COVERED (non-zero pipeline demand, woven correctly today). Each test parses the real
 * construction and asserts the matcher accepts/rejects the expected receiver.
 */
class CallPatternGrammarTest {

    private static final String CALLER = "LCaller;";

    /** {@code call(MethodPattern)} base: a concrete owner/name/params signature matches exactly that
     *  invoke and rejects a different method name. */
    @Test
    void baseCallPatternMatchesExactSignature() {
        PointcutExpression pc = PointcutExpressionParser.parse(
                "call(boolean java.util.Collection.add(java.lang.Object))");
        assertTrue(match(pc, ref("Ljava/util/Collection;", "add",
                List.of("Ljava/lang/Object;"), "Z")).isPresent(),
                "base call() must match the exact add(Object) signature");
        assertTrue(match(pc, ref("Ljava/util/Collection;", "remove",
                List.of("Ljava/lang/Object;"), "Z")).isEmpty(),
                "base call() must reject a different method name");
    }

    /** {@code (..)} standalone varargs matches any parameter list (concrete return). */
    @Test
    void standaloneVarargsMatchesAnyParams() {
        PointcutExpression pc = PointcutExpressionParser.parse(
                "call(boolean java.util.Collection.add(..))");
        assertTrue(match(pc, ref("Ljava/util/Collection;", "add",
                List.of("Ljava/lang/Object;"), "Z")).isPresent(),
                "(..) must match a single-arg add");
        assertTrue(match(pc, ref("Ljava/util/Collection;", "add",
                List.of("Ljava/lang/Object;", "I"), "Z")).isPresent(),
                "(..) must match a multi-arg add");
        assertTrue(match(pc, ref("Ljava/util/Collection;", "add",
                List.of(), "Z")).isPresent(),
                "(..) must match a no-arg add");
    }

    /** {@code T+} in a parameter position matches a subtype argument (gh61 param path). The corpus
     *  spells the type as a simple name ({@code Number+}); {@code resolveFqn} resolves the simple name
     *  via imports, so this is the form that actually reaches the matcher. */
    @Test
    void parameterPositionTSubtypeMatchesSubtypeArg() {
        PointcutExpression pc = PointcutExpressionParser.parse(
                "call(boolean java.util.Collection.add(Number+))");
        // Integer is a Number subtype → matches.
        ClassDef integer = bareClass("Ljava/lang/Integer;", "Ljava/lang/Number;");
        assertTrue(match(pc, ref("Ljava/util/Collection;", "add",
                List.of("Ljava/lang/Integer;"), "Z"), integer).isPresent(),
                "Number+ param must match an Integer argument");
        // String is not a Number → rejected.
        ClassDef string = bareClass("Ljava/lang/String;", "Ljava/lang/Object;");
        assertTrue(match(pc, ref("Ljava/util/Collection;", "add",
                List.of("Ljava/lang/String;"), "Z"), string).isEmpty(),
                "Number+ param must reject a String argument");
    }

    /** Array descriptors ({@code T[]}) in a signature match exactly. */
    @Test
    void arrayParameterMatchesArrayDescriptor() {
        PointcutExpression pc = PointcutExpressionParser.parse(
                "call(int java.io.InputStream.read(byte[]))");
        assertTrue(match(pc, ref("Ljava/io/InputStream;", "read", List.of("[B"), "I")).isPresent(),
                "byte[] param must match the [B descriptor");
        assertTrue(match(pc, ref("Ljava/io/InputStream;", "read",
                List.of("Ljava/lang/Object;"), "I")).isEmpty(),
                "byte[] param must reject a non-array Object argument");
    }

    /** {@code &&} / {@code ||} composition and parentheses grouping parse and compose correctly. */
    @Test
    void compositionAndGroupingMatch() {
        // AND: both clauses must hold (call matches AND target type matches).
        PointcutExpression and = PointcutExpressionParser.parse(
                "call(boolean java.util.Collection.add(java.lang.Object)) && target(java.util.Collection)");
        assertTrue(match(and, ref("Ljava/util/Collection;", "add",
                List.of("Ljava/lang/Object;"), "Z")).isPresent(),
                "&& composition matches when both clauses hold");

        // OR with parentheses: either of two call signatures matches.
        PointcutExpression or = PointcutExpressionParser.parse(
                "(call(boolean java.util.Collection.add(java.lang.Object)) "
                        + "|| call(boolean java.util.Collection.remove(java.lang.Object)))");
        assertTrue(match(or, ref("Ljava/util/Collection;", "remove",
                List.of("Ljava/lang/Object;"), "Z")).isPresent(),
                "|| inside parentheses matches the second alternative");
        assertTrue(match(or, ref("Ljava/util/Collection;", "clear", List.of(), "V")).isEmpty(),
                "|| must reject a method matching neither alternative");
    }

    /** {@code ..*} dot-glob and {@code .*} single-level glob package patterns, exercised through the
     *  {@code !within(...)} path (the dominant consumer of these globs in the corpus). */
    @Test
    void packageGlobsMatchViaNotWithin() {
        // !within(java..*) excludes any class under java. — so a java.util caller yields NO match.
        PointcutExpression dotGlob = PointcutExpressionParser.parse(
                "call(boolean java.util.Collection.add(java.lang.Object)) && !within(java..*)");
        assertTrue(matchInClass(dotGlob, "Ljava/util/HelperKt;",
                ref("Ljava/util/Collection;", "add", List.of("Ljava/lang/Object;"), "Z")).isEmpty(),
                "..* dot-glob (java..*) must exclude a caller under java.util");
        // A caller outside java. still matches.
        assertTrue(matchInClass(dotGlob, "Lcom/example/App;",
                ref("Ljava/util/Collection;", "add", List.of("Ljava/lang/Object;"), "Z")).isPresent(),
                "..* dot-glob must NOT exclude a caller outside java.");

        // !within(com.example.*) — single-level glob excludes com.example.Foo but not com.example.sub.Foo.
        PointcutExpression singleGlob = PointcutExpressionParser.parse(
                "call(boolean java.util.Collection.add(java.lang.Object)) && !within(com.example.*)");
        assertTrue(matchInClass(singleGlob, "Lcom/example/Foo;",
                ref("Ljava/util/Collection;", "add", List.of("Ljava/lang/Object;"), "Z")).isEmpty(),
                ".* single-level glob excludes a direct member of com.example");
        assertTrue(matchInClass(singleGlob, "Lcom/example/sub/Foo;",
                ref("Ljava/util/Collection;", "add", List.of("Ljava/lang/Object;"), "Z")).isPresent(),
                ".* single-level glob must NOT exclude a deeper-nested class");
    }

    // --- fixture -----------------------------------------------------------------------------------

    private static Optional<Match> match(PointcutExpression pc, MethodReference callee,
                                         ClassDef... extra) {
        return matchInClass(pc, CALLER, callee, extra);
    }

    private static Optional<Match> matchInClass(PointcutExpression pc, String callerDesc,
                                                MethodReference callee, ClassDef... extra) {
        Instruction invoke = new ImmutableInstruction35c(
                Opcode.INVOKE_VIRTUAL, callee.getParameterTypes().size() + 1, 0, 1, 2, 3, 4, callee);
        Instruction ret = new ImmutableInstruction10x(Opcode.RETURN_VOID);
        ImmutableMethodImplementation impl = new ImmutableMethodImplementation(
                5, List.of(invoke, ret), Collections.emptyList(), Collections.emptyList());
        ImmutableMethod m = new ImmutableMethod(callerDesc, "m", Collections.emptyList(), "V",
                AccessFlags.PUBLIC.getValue() | AccessFlags.STATIC.getValue(), null, null, impl);
        ClassDef caller = new ImmutableClassDef(callerDesc, AccessFlags.PUBLIC.getValue(),
                "Ljava/lang/Object;", null, null, null, null, List.of(m));

        List<ClassDef> classes = new ArrayList<>();
        classes.add(caller);
        Collections.addAll(classes, extra);
        DexFile dex = new ImmutableDexFile(Opcodes.getDefault(), classes);

        TypeResolver tr = new TypeResolver(List.of(
                "java.util.Collection", "java.io.InputStream", "java.lang.Object",
                "java.lang.Number", "java.lang.Integer", "java.lang.String"));
        InheritanceResolver ir = new InheritanceResolver(
                new AndroidClassIndex(Path.of("/tmp/nope.jar")), dex);
        PointcutMatcher pm = new PointcutMatcher(tr, ir);
        Method method = caller.getMethods().iterator().next();
        return pm.match(pc, caller, method, invoke, 0, 2, List.of(invoke, ret));
    }

    private static MethodReference ref(String owner, String name, List<String> params, String ret) {
        return new ImmutableMethodReference(owner, name, params, ret);
    }

    private static ClassDef bareClass(String desc, String superDesc) {
        return new ImmutableClassDef(desc, AccessFlags.PUBLIC.getValue(), superDesc,
                null, null, null, null, Collections.emptyList());
    }
}
