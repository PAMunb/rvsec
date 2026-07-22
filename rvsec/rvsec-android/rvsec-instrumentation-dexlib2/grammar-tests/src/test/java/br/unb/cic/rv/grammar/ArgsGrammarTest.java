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
import java.util.Collections;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Backs the matrix row "{@code args(Type)} positional declared-type match" (§4.AT) —
 * the argument-list analogue of {@code target(Type)} (§4.TT). At a {@code call()} join
 * point {@code args(T, ...)} constrains the actual argument descriptors positionally;
 * the matcher walks {@code MethodReference.getParameterTypes()} and accepts iff each
 * concrete-Type position is assignable from the actual arg type via the APK-dex
 * superclass chain (declared-type, not a runtime {@code instanceof} — the V-decision).
 * A binding-name / {@code *} position accepts any single arg; a trailing {@code ..}
 * accepts any remaining args. The pure-binding form ({@code args(o)}) stays an
 * always-match collector.
 */
class ArgsGrammarTest {

    private static final String CALLER = "LCaller;";

    /** §4.AT: {@code args(CharSequence)} matches a single-arg call whose declared arg
     *  type is a CharSequence subtype, and rejects an unrelated arg type. */
    @Test
    void argsTypeMatchesByArgumentType() {
        PointcutExpression typePattern = PointcutExpressionParser.parse("args(CharSequence)");

        // StringBuilder implements CharSequence → the declared arg type is a subtype.
        ClassDef stringBuilder =
                bareClass("Ljava/lang/StringBuilder;", "Ljava/lang/CharSequence;");
        MethodReference acceptsCharSeq = new ImmutableMethodReference(
                "Lcom/example/Sink;", "accept",
                List.of("Ljava/lang/StringBuilder;"), "V");
        assertTrue(matchAgainstArgs(typePattern, acceptsCharSeq, stringBuilder).isPresent(),
                "args(CharSequence) must match an arg whose declared type is a CharSequence subtype");

        // Integer is not a CharSequence → no match.
        ClassDef integer = bareClass("Ljava/lang/Integer;", "Ljava/lang/Object;");
        MethodReference acceptsInteger = new ImmutableMethodReference(
                "Lcom/example/Sink;", "accept",
                List.of("Ljava/lang/Integer;"), "V");
        assertTrue(matchAgainstArgs(typePattern, acceptsInteger, integer).isEmpty(),
                "args(CharSequence) must NOT match an unrelated arg type (Integer)");
    }

    /** §4.AT: a leading {@code *} accepts any single arg, a Type pins the next position,
     *  and a trailing {@code ..} accepts the remaining args ({@code args(*, name, ..)}
     *  mixed shape — the §4.V trailing-mixed row). Here the second position pins a Type. */
    @Test
    void argsLeadingWildcardTypeAndTrailingRest() {
        // args(*, CharSequence, ..) : position 0 = any, position 1 = CharSequence, then any tail.
        PointcutExpression mixed =
                PointcutExpressionParser.parse("args(*, CharSequence, ..)");

        ClassDef stringBuilder =
                bareClass("Ljava/lang/StringBuilder;", "Ljava/lang/CharSequence;");
        ClassDef integer = bareClass("Ljava/lang/Integer;", "Ljava/lang/Object;");
        // (Integer, StringBuilder, Integer): pos0 any (Integer ok), pos1 CharSequence
        // (StringBuilder ok), trailing Integer accepted by "..".
        MethodReference three = new ImmutableMethodReference(
                "Lcom/example/Sink;", "accept3",
                List.of("Ljava/lang/Integer;", "Ljava/lang/StringBuilder;", "Ljava/lang/Integer;"),
                "V");
        assertTrue(matchAgainstArgs(mixed, three, stringBuilder, integer).isPresent(),
                "args(*, CharSequence, ..) must match when position 1 is a CharSequence subtype");

        // pos1 = Integer (not CharSequence) → no match.
        MethodReference badPos1 = new ImmutableMethodReference(
                "Lcom/example/Sink;", "accept2",
                List.of("Ljava/lang/Integer;", "Ljava/lang/Integer;"), "V");
        assertTrue(matchAgainstArgs(mixed, badPos1, integer).isEmpty(),
                "args(*, CharSequence, ..) must NOT match when position 1 is not a CharSequence");
    }

    /** §4.AT: the pure-binding form {@code args(o)} carries no type filter — always matches. */
    @Test
    void argsBindingFormAlwaysMatches() {
        PointcutExpression binding = PointcutExpressionParser.parse("args(o)");

        MethodReference acceptsInteger = new ImmutableMethodReference(
                "Lcom/example/Sink;", "accept", List.of("Ljava/lang/Integer;"), "V");
        ClassDef integer = bareClass("Ljava/lang/Integer;", "Ljava/lang/Object;");
        assertTrue(matchAgainstArgs(binding, acceptsInteger, integer).isPresent(),
                "args(o) is a binding (no type filter) and must always match");
    }

    // --- fixture ---------------------------------------------------------------------------------

    private static Optional<Match> matchAgainstArgs(PointcutExpression pe, MethodReference callee,
                                                    ClassDef... extraDexClasses) {
        Instruction invoke = new ImmutableInstruction35c(
                Opcode.INVOKE_VIRTUAL, 1, 0, 0, 0, 0, 0, callee);
        ImmutableMethodImplementation impl = new ImmutableMethodImplementation(
                1, List.of(invoke, new ImmutableInstruction10x(Opcode.RETURN_VOID)),
                Collections.emptyList(), Collections.emptyList());
        ImmutableMethod m = new ImmutableMethod(CALLER, "m", Collections.emptyList(), "V",
                AccessFlags.PUBLIC.getValue() | AccessFlags.STATIC.getValue(), null, null, impl);
        ClassDef caller = new ImmutableClassDef(CALLER, AccessFlags.PUBLIC.getValue(),
                "Ljava/lang/Object;", null, null, null, null, List.of(m));

        java.util.List<ClassDef> classes = new java.util.ArrayList<>();
        classes.add(caller);
        Collections.addAll(classes, extraDexClasses);
        DexFile dex = new ImmutableDexFile(Opcodes.getDefault(), classes);

        TypeResolver tr = new TypeResolver(List.of(
                "java.lang.CharSequence", "java.lang.Integer", "java.lang.StringBuilder"));
        InheritanceResolver ir = new InheritanceResolver(
                new AndroidClassIndex(Path.of("/tmp/nope.jar")), dex);
        PointcutMatcher pm = new PointcutMatcher(tr, ir);
        Method method = caller.getMethods().iterator().next();
        return pm.match(pe, caller, method, invoke, 0, 2, List.of(invoke,
                new ImmutableInstruction10x(Opcode.RETURN_VOID)));
    }

    private static ClassDef bareClass(String desc, String superDesc) {
        return new ImmutableClassDef(desc, AccessFlags.PUBLIC.getValue(), superDesc,
                null, null, null, null, Collections.emptyList());
    }
}
