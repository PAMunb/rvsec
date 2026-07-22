package br.unb.cic.rv.pointcut;

import com.android.tools.smali.dexlib2.AccessFlags;
import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.DexFile;
import com.android.tools.smali.dexlib2.iface.Method;
import com.android.tools.smali.dexlib2.iface.instruction.Instruction;
import com.android.tools.smali.dexlib2.immutable.ImmutableClassDef;
import com.android.tools.smali.dexlib2.immutable.ImmutableDexFile;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethod;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethodImplementation;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction10x;

import org.junit.jupiter.api.Test;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * {@code staticinitialization(<typePattern>)} matching at
 * {@link PointcutMatcher#matchStaticInit}. The matcher fires only at the FIRST
 * instruction of a {@code <clinit>} method whose declaring class matches the
 * pattern — exact / package-wildcard for a bare pattern, subtype-aware
 * ({@link InheritanceResolver}) for a trailing {@code T+}.
 *
 * <p>Coverage gap this closes: {@code matchStaticInit:517-529} was dark — no test
 * exercised the {@code <clinit>} name gate, the method-entry index gate, the exact
 * pattern branch, or the {@code T+} subtype branch. The negatives (non-clinit,
 * non-zero index, unrelated pattern) are the regression guards: a broken gate
 * would fire staticinit advice on ordinary methods or mid-method.
 */
class PointcutMatcherStaticInitTest {

    private static final String FOO = "Lcom/example/app/Foo;";
    private static final String SUBFOO = "Lcom/example/app/SubFoo;";
    private static final String OTHER = "Lcom/example/other/Bar;";

    // ------------------------------------------------------------------
    // Fixtures — a class carrying a <clinit> (or a named method) with a single
    // return-void body. matchStaticInit reads only the class type, the method
    // name, and the instruction index; the instruction itself is opaque.
    // ------------------------------------------------------------------

    private static ClassDef classWith(String classDesc, String superDesc, String methodName) {
        List<com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction> body =
                new ArrayList<>();
        body.add(new ImmutableInstruction10x(Opcode.RETURN_VOID));
        ImmutableMethodImplementation impl = new ImmutableMethodImplementation(
                /*registerCount=*/ 1, body, Collections.emptyList(), Collections.emptyList());
        int flags = AccessFlags.STATIC.getValue()
                | ("<clinit>".equals(methodName) ? AccessFlags.CONSTRUCTOR.getValue() : 0);
        ImmutableMethod m = new ImmutableMethod(
                classDesc, methodName, Collections.emptyList(), "V", flags, null, null, impl);
        return new ImmutableClassDef(
                classDesc, AccessFlags.PUBLIC.getValue(), superDesc,
                Collections.emptyList(), null, null, Collections.emptyList(), List.of(m));
    }

    private static Instruction firstInstruction(ClassDef cd) {
        Method m = cd.getMethods().iterator().next();
        return m.getImplementation().getInstructions().iterator().next();
    }

    private static Method methodOf(ClassDef cd) {
        return cd.getMethods().iterator().next();
    }

    /** Matcher whose inheritance index optionally carries an APK subtype edge. */
    private static PointcutMatcher matcher(ClassDef... apkClasses) {
        TypeResolver tr = new TypeResolver(List.of());
        DexFile dex = new ImmutableDexFile(Opcodes.getDefault(), List.of(apkClasses));
        InheritanceResolver ir = new InheritanceResolver(
                new AndroidClassIndex(Path.of("/tmp/nope.jar")), List.of(dex));
        return new PointcutMatcher(tr, ir);
    }

    private static Optional<Match> matchAt(PointcutMatcher pm, StaticInitPC si,
                                           ClassDef cd, int instructionIndex) {
        return pm.match(si, cd, methodOf(cd), firstInstruction(cd),
                instructionIndex, /*totalInstructions*/ 1, List.of(firstInstruction(cd)));
    }

    // ------------------------------------------------------------------
    // Positive: exact pattern at <clinit> entry.
    // ------------------------------------------------------------------

    @Test
    void staticInitMatchesClinitOfExactPatternClass() {
        ClassDef foo = classWith(FOO, "Ljava/lang/Object;", "<clinit>");
        PointcutMatcher pm = matcher();
        StaticInitPC si = new StaticInitPC("com.example.app.Foo");
        assertTrue(matchAt(pm, si, foo, 0).isPresent(),
                "staticinitialization(Foo) MUST match the <clinit> of class Foo at index 0");
    }

    @Test
    void staticInitMatchesPackageWildcard() {
        ClassDef foo = classWith(FOO, "Ljava/lang/Object;", "<clinit>");
        PointcutMatcher pm = matcher();
        StaticInitPC si = new StaticInitPC("com.example.app..*");
        assertTrue(matchAt(pm, si, foo, 0).isPresent(),
                "staticinitialization(com.example.app..*) MUST match a <clinit> under that package");
    }

    // ------------------------------------------------------------------
    // Positive: T+ subtype pattern.
    // ------------------------------------------------------------------

    @Test
    void staticInitPlusMatchesSubtypeClinit() {
        // staticinitialization(Foo+) at SubFoo's <clinit>, where SubFoo extends Foo.
        ClassDef subFoo = classWith(SUBFOO, FOO, "<clinit>");
        PointcutMatcher pm = matcher(subFoo);   // seed the APK subtype edge
        StaticInitPC si = new StaticInitPC("com.example.app.Foo+");
        assertTrue(matchAt(pm, si, subFoo, 0).isPresent(),
                "staticinitialization(Foo+) MUST match the <clinit> of a Foo subtype");
    }

    @Test
    void staticInitPlusRejectsUnrelatedClinit() {
        // staticinitialization(Foo+) at an unrelated class's <clinit> → no edge.
        ClassDef other = classWith(OTHER, "Ljava/lang/Object;", "<clinit>");
        PointcutMatcher pm = matcher(other);
        StaticInitPC si = new StaticInitPC("com.example.app.Foo+");
        assertTrue(matchAt(pm, si, other, 0).isEmpty(),
                "staticinitialization(Foo+) MUST NOT match a class outside the Foo hierarchy");
    }

    // ------------------------------------------------------------------
    // Negatives: name gate, index gate, pattern gate.
    // ------------------------------------------------------------------

    @Test
    void staticInitRejectsNonClinitMethod() {
        // Same class/pattern but the method is an ordinary <init>, not <clinit>:
        // staticinitialization advice MUST NOT fire on it.
        ClassDef foo = classWith(FOO, "Ljava/lang/Object;", "<init>");
        PointcutMatcher pm = matcher();
        StaticInitPC si = new StaticInitPC("com.example.app.Foo");
        assertTrue(matchAt(pm, si, foo, 0).isEmpty(),
                "staticinitialization(Foo) MUST NOT match a non-<clinit> method");
    }

    @Test
    void staticInitRejectsNonEntryInstruction() {
        // <clinit> matches only at method entry (index 0); an interior index MUST
        // NOT match (the advice is injected once, at the top of the initializer).
        ClassDef foo = classWith(FOO, "Ljava/lang/Object;", "<clinit>");
        PointcutMatcher pm = matcher();
        StaticInitPC si = new StaticInitPC("com.example.app.Foo");
        assertTrue(matchAt(pm, si, foo, /*instructionIndex*/ 1).isEmpty(),
                "staticinitialization MUST match only at <clinit> entry (index 0), not mid-method");
    }

    @Test
    void staticInitRejectsMismatchedExactPattern() {
        // staticinitialization(Bar) at Foo's <clinit>: exact-pattern mismatch.
        ClassDef foo = classWith(FOO, "Ljava/lang/Object;", "<clinit>");
        PointcutMatcher pm = matcher();
        StaticInitPC si = new StaticInitPC("com.example.other.Bar");
        assertTrue(matchAt(pm, si, foo, 0).isEmpty(),
                "staticinitialization(Bar) MUST NOT match the <clinit> of an unrelated class Foo");
    }
}
