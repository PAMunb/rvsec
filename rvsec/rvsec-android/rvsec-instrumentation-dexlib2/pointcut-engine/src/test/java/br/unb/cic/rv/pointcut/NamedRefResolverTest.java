package br.unb.cic.rv.pointcut;

import com.android.tools.smali.dexlib2.AccessFlags;
import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.Method;
import com.android.tools.smali.dexlib2.iface.instruction.Instruction;
import com.android.tools.smali.dexlib2.immutable.ImmutableClassDef;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethod;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethodImplementation;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction10x;

import org.junit.jupiter.api.Test;

import java.nio.file.Path;
import java.util.Collections;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * §4.D: {@code NamedRefPC} resolution. {@code BaseAspect.notwithin()} expands against the active
 * descriptor's {@code baseAspectExclusions} (the canonical twelve package patterns) and gates the
 * match by class FQN. Unrecognised names and empty exclusion lists fail closed (G-decision).
 */
class NamedRefResolverTest {

    private static final List<String> CANONICAL_TWELVE = List.of(
            "sun..*", "java..*", "javax..*", "com.sun..*", "org.dacapo.harness..*",
            "org.apache.commons..*", "org.apache.geronimo..*", "net.sf.cglib..*",
            "mop..*", "javamoprt..*", "rvmonitorrt..*", "com.runtimeverification..*");

    @Test
    void baseAspectNotwithinExpansion() {
        NamedRefPC notwithin = new NamedRefPC("BaseAspect.notwithin()");
        // A class OUTSIDE every excluded package matches (it is woven).
        Optional<Match> appMatch = match(notwithin, "Lcom/example/app/Foo;", CANONICAL_TWELVE);
        assertTrue(appMatch.isPresent(),
                "an application class outside all exclusions should match BaseAspect.notwithin()");
        // A class INSIDE an excluded package (sun..*) is filtered out.
        Optional<Match> platformMatch = match(notwithin, "Lsun/security/ssl/Foo;", CANONICAL_TWELVE);
        assertTrue(platformMatch.isEmpty(),
                "a class inside sun..* should be excluded by BaseAspect.notwithin()");
        // mop..* is one of the twelve — a monitor-runtime class is excluded too.
        assertTrue(match(notwithin, "Lmop/Coverage;", CANONICAL_TWELVE).isEmpty(),
                "a class inside mop..* should be excluded by BaseAspect.notwithin()");
    }

    @Test
    void unrecognisedNameFailsClosed() {
        NamedRefPC bogus = new NamedRefPC("FooBar.bar()");
        assertThrows(UnresolvedNamedRefException.class,
                () -> match(bogus, "Lcom/example/app/Foo;", CANONICAL_TWELVE),
                "an unrecognised named reference must fail closed, not silently match");
    }

    @Test
    void emptyExclusionsFailsClosed() {
        NamedRefPC notwithin = new NamedRefPC("BaseAspect.notwithin()");
        assertThrows(LegacyDescriptorException.class,
                () -> match(notwithin, "Lcom/example/app/Foo;", List.of()),
                "BaseAspect.notwithin() with an empty exclusions list must fail closed (legacy descriptor)");
    }

    // --- fixture ---------------------------------------------------------------------------------

    private static Optional<Match> match(PointcutExpression pe, String classDesc,
                                         List<String> exclusions) {
        PointcutMatcher pm = newMatcher();
        Instruction nop = new ImmutableInstruction10x(Opcode.NOP);
        ImmutableMethodImplementation impl = new ImmutableMethodImplementation(
                1, List.of(nop), Collections.emptyList(), Collections.emptyList());
        ImmutableMethod method = new ImmutableMethod(classDesc, "m", Collections.emptyList(), "V",
                AccessFlags.PUBLIC.getValue() | AccessFlags.STATIC.getValue(), null, null, impl);
        ClassDef classDef = new ImmutableClassDef(classDesc, AccessFlags.PUBLIC.getValue(),
                "Ljava/lang/Object;", null, null, null, null, List.of(method));
        return pm.match(pe, classDef, method, nop, 0, 1, List.of(nop), exclusions, "TestAspect");
    }

    private static PointcutMatcher newMatcher() {
        TypeResolver tr = new TypeResolver(List.of());
        InheritanceResolver ir = new InheritanceResolver(
                new AndroidClassIndex(Path.of("/tmp/nope.jar")), List.of());
        return new PointcutMatcher(tr, ir);
    }
}
