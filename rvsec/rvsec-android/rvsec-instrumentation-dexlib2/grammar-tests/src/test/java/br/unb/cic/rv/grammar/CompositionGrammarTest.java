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
 * Backs the matrix row "{@code !target(Type)} / {@code !args(Type)} parser
 * specialization" (§4.N). The parser wraps the type forms in a {@code NegationPC}
 * and the matcher inverts the inner {@code target(Type)} / {@code args(Type)}
 * verdict: a receiver/arg that IS the type (or a subtype) does NOT match the
 * negation, while an unrelated receiver/arg DOES. This mirrors the §4.TT/§4.AT
 * fixtures (declared-type subtype matching via the APK-dex superclass chain).
 */
class CompositionGrammarTest {

    private static final String CALLER = "LCaller;";

    /** §4.N: {@code !target(Cipher)} rejects a Cipher-subtype receiver and matches
     *  an unrelated receiver; symmetric {@code !args(CharSequence)} on the argument. */
    @Test
    void negativeTargetArgsParserSpecialization() {
        // --- !target(Type) -------------------------------------------------------
        PointcutExpression notTarget =
                PointcutExpressionParser.parse("!target(Cipher)");

        // AesCipher extends Cipher → receiver IS a Cipher subtype → negation must NOT match.
        ClassDef aesCipher = bareClass("Lcom/example/AesCipher;", "Ljavax/crypto/Cipher;");
        MethodReference toAes = new ImmutableMethodReference(
                "Lcom/example/AesCipher;", "doFinal", List.of(), "[B");
        assertTrue(matchAgainstReceiver(notTarget, toAes, aesCipher).isEmpty(),
                "!target(Cipher) must NOT match a receiver whose declared type is a Cipher subtype");

        // String is unrelated to Cipher → negation must match.
        MethodReference toString = new ImmutableMethodReference(
                "Ljava/lang/String;", "doFinal", List.of(), "[B");
        assertTrue(matchAgainstReceiver(notTarget, toString).isPresent(),
                "!target(Cipher) must match a call to an unrelated receiver (String)");

        // --- !args(Type) ---------------------------------------------------------
        PointcutExpression notArgs =
                PointcutExpressionParser.parse("!args(CharSequence)");

        // StringBuilder implements CharSequence → arg IS a subtype → negation must NOT match.
        ClassDef stringBuilder =
                bareClass("Ljava/lang/StringBuilder;", "Ljava/lang/CharSequence;");
        MethodReference acceptsCharSeq = new ImmutableMethodReference(
                "Lcom/example/Sink;", "accept",
                List.of("Ljava/lang/StringBuilder;"), "V");
        assertTrue(matchAgainstReceiver(notArgs, acceptsCharSeq, stringBuilder).isEmpty(),
                "!args(CharSequence) must NOT match an arg whose declared type is a CharSequence subtype");

        // Integer is unrelated to CharSequence → negation must match.
        ClassDef integer = bareClass("Ljava/lang/Integer;", "Ljava/lang/Object;");
        MethodReference acceptsInteger = new ImmutableMethodReference(
                "Lcom/example/Sink;", "accept",
                List.of("Ljava/lang/Integer;"), "V");
        assertTrue(matchAgainstReceiver(notArgs, acceptsInteger, integer).isPresent(),
                "!args(CharSequence) must match a call whose arg type is unrelated (Integer)");
    }

    // --- fixture ---------------------------------------------------------------------------------

    private static Optional<Match> matchAgainstReceiver(PointcutExpression pe, MethodReference callee,
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
                "javax.crypto.Cipher", "java.lang.String",
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
