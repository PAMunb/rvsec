package br.unb.cic.rv.pointcut;

import org.junit.jupiter.api.Test;

import java.nio.file.Path;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * {@link InheritanceResolver#isAssignableFrom(String, String)} short-circuit rules — the
 * decisions taken BEFORE any graph walk. These need neither an APK dex nor an android.jar:
 * the resolver is built empty and each answer comes straight from the guard clauses.
 *
 * <p>Covered guards, in the order the method checks them:
 * <ol>
 *   <li>either operand {@code null} → {@code false} (fail closed, never NPE);</li>
 *   <li>identical FQNs → {@code true} (a type is assignable from itself);</li>
 *   <li>{@code java.lang.Object} as the supertype → {@code true} for every reference type,
 *       {@code false} for the eight primitives and {@code void} (primitives are not
 *       {@code Object} subtypes — the {@code T+} closure must not sweep them in).</li>
 * </ol>
 */
class InheritanceResolverFastPathTest {

    private static InheritanceResolver empty() {
        // No APK dexes: every non-short-circuit query would fall through to the empty
        // AndroidClassIndex, so any true/false asserted here is decided by the guards alone.
        return new InheritanceResolver(
                new AndroidClassIndex(Path.of("/tmp/nope.jar")), List.of());
    }

    @Test
    void nullOperandsFailClosed() {
        InheritanceResolver ir = empty();
        assertFalse(ir.isAssignableFrom(null, "com.example.Foo"), "null supertype → false");
        assertFalse(ir.isAssignableFrom("com.example.Foo", null), "null subtype → false");
        assertFalse(ir.isAssignableFrom(null, null), "both null → false");
    }

    @Test
    void identicalTypeIsAssignableFromItself() {
        // Reached before any descriptor conversion or walk — a pure String equality.
        assertTrue(empty().isAssignableFrom("com.example.Foo", "com.example.Foo"),
                "a type is assignable from itself");
    }

    @Test
    void objectIsSupertypeOfEveryReferenceType() {
        InheritanceResolver ir = empty();
        // No APK/framework metadata is consulted: the Object arm answers true for any
        // non-primitive FQN, including one the resolver has never heard of.
        assertTrue(ir.isAssignableFrom("java.lang.Object", "java.lang.String"),
                "Object is a supertype of String");
        assertTrue(ir.isAssignableFrom("java.lang.Object", "com.example.Whatever"),
                "Object is a supertype of an arbitrary reference type");
    }

    @Test
    void objectIsNotSupertypeOfPrimitives() {
        InheritanceResolver ir = empty();
        // isPrimitive must recognise all nine tokens so the Object arm returns false for
        // each — otherwise staticinitialization(Object+) would absurdly match int, void, ...
        for (String prim : List.of("void", "boolean", "byte", "short", "char",
                "int", "long", "float", "double")) {
            assertFalse(ir.isAssignableFrom("java.lang.Object", prim),
                    "Object is NOT assignable from primitive " + prim);
        }
    }
}
