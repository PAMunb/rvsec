package br.unb.cic.rv.grammar;

import br.unb.cic.rv.pointcut.AndroidClassIndex;
import br.unb.cic.rv.pointcut.CallPC;
import br.unb.cic.rv.pointcut.InheritanceResolver;
import br.unb.cic.rv.pointcut.Match;
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
 * Backs the matrix rows "T+ in call() owner" (§4.O) and method-name glob (§4.X — the matrix row
 * captured under the {@code *} / name-pattern surface). Real rv-monitor advice expressions always
 * spell a concrete return type (never {@code *}), so the fixtures mirror that form.
 */
class CallPointcutGrammarTest {

    private static final String CALLER = "LCaller;";

    /** §4.O: {@code call(... Cipher+.doFinal(..))} matches a call whose receiver is a subtype of
     *  Cipher (resolved through the APK dex superclass chain), and rejects an unrelated owner. */
    @Test
    void callTSubtypeInOwner() {
        CallPC pc = (CallPC) PointcutExpressionParser.parse(
                "call(byte[] javax.crypto.Cipher+.doFinal())");

        // AesCipher extends Cipher → owner Cipher+ matches it via InheritanceResolver.
        ClassDef aesCipher = bareClass("Lcom/example/AesCipher;", "Ljavax/crypto/Cipher;");
        MethodReference toAes = new ImmutableMethodReference(
                "Lcom/example/AesCipher;", "doFinal", List.of(), "[B");
        assertTrue(matchAgainstCall(pc, toAes, aesCipher).isPresent(),
                "Cipher+ owner must match a call to a Cipher subtype (AesCipher)");

        // String is not a Cipher subtype → no match (no Object fast-path for a non-Object owner).
        MethodReference toString = new ImmutableMethodReference(
                "Ljava/lang/String;", "doFinal", List.of(), "[B");
        assertTrue(matchAgainstCall(pc, toString).isEmpty(),
                "Cipher+ owner must NOT match an unrelated owner (String)");
    }

    /** §4.X: a trailing {@code *} in the method name is a prefix glob. */
    @Test
    void methodNamePrefixGlob() {
        CallPC pc = (CallPC) PointcutExpressionParser.parse(
                "call(boolean java.util.Collection.add*(..))");

        MethodReference addAll = new ImmutableMethodReference(
                "Ljava/util/Collection;", "addAll", List.of("Ljava/util/Collection;"), "Z");
        assertTrue(matchAgainstCall(pc, addAll).isPresent(),
                "add* must match addAll");

        MethodReference add = new ImmutableMethodReference(
                "Ljava/util/Collection;", "add", List.of("Ljava/lang/Object;"), "Z");
        assertTrue(matchAgainstCall(pc, add).isPresent(),
                "add* must match add");

        MethodReference remove = new ImmutableMethodReference(
                "Ljava/util/Collection;", "remove", List.of("Ljava/lang/Object;"), "Z");
        assertTrue(matchAgainstCall(pc, remove).isEmpty(),
                "add* must NOT match remove");
    }

    // --- fixture ---------------------------------------------------------------------------------

    private static Optional<Match> matchAgainstCall(CallPC pc, MethodReference callee,
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
                "javax.crypto.Cipher", "java.util.Collection", "java.lang.String"));
        InheritanceResolver ir = new InheritanceResolver(
                new AndroidClassIndex(Path.of("/tmp/nope.jar")), dex);
        PointcutMatcher pm = new PointcutMatcher(tr, ir);
        Method method = caller.getMethods().iterator().next();
        return pm.match(pc, caller, method, invoke, 0, 2, List.of(invoke,
                new ImmutableInstruction10x(Opcode.RETURN_VOID)));
    }

    private static ClassDef bareClass(String desc, String superDesc) {
        return new ImmutableClassDef(desc, AccessFlags.PUBLIC.getValue(), superDesc,
                null, null, null, null, Collections.emptyList());
    }
}
