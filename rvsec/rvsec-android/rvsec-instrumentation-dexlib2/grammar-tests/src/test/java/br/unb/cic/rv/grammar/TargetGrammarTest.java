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
 * Backs the matrix row "{@code target(Type)} subtype match on receiver" (§4.TT). At a
 * {@code call()} join point {@code target(T)} constrains the receiver's declared type;
 * in the dexlib2 inline-call model that declared type is the invoke owner
 * ({@code MethodReference.getDefiningClass()}), so the pattern matches iff it is
 * assignable from the owner via the APK-dex superclass chain (declared-type, not a
 * runtime {@code instanceof} — the V-decision). The binding form ({@code target(o)})
 * stays an always-match collector.
 */
class TargetGrammarTest {

    private static final String CALLER = "LCaller;";

    /** §4.TT: {@code target(Cipher)} matches a call whose receiver is a Cipher subtype,
     *  and rejects a call to an unrelated receiver. */
    @Test
    void targetTypeMatchesByReceiverType() {
        PointcutExpression typePattern = PointcutExpressionParser.parse("target(Cipher)");

        // AesCipher extends Cipher → declared receiver type is a Cipher subtype.
        ClassDef aesCipher = bareClass("Lcom/example/AesCipher;", "Ljavax/crypto/Cipher;");
        MethodReference toAes = new ImmutableMethodReference(
                "Lcom/example/AesCipher;", "doFinal", List.of(), "[B");
        assertTrue(matchAgainstReceiver(typePattern, toAes, aesCipher).isPresent(),
                "target(Cipher) must match a receiver whose declared type is a Cipher subtype");

        // String is not a Cipher subtype → no match.
        MethodReference toString = new ImmutableMethodReference(
                "Ljava/lang/String;", "doFinal", List.of(), "[B");
        assertTrue(matchAgainstReceiver(typePattern, toString).isEmpty(),
                "target(Cipher) must NOT match an unrelated receiver (String)");
    }

    /** §4.TT: the binding form {@code target(o)} carries no type filter — it always matches. */
    @Test
    void targetBindingFormAlwaysMatches() {
        PointcutExpression binding = PointcutExpressionParser.parse("target(o)");

        MethodReference toString = new ImmutableMethodReference(
                "Ljava/lang/String;", "doFinal", List.of(), "[B");
        assertTrue(matchAgainstReceiver(binding, toString).isPresent(),
                "target(o) is a binding (no type filter) and must always match");
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

        TypeResolver tr = new TypeResolver(List.of("javax.crypto.Cipher", "java.lang.String"));
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
