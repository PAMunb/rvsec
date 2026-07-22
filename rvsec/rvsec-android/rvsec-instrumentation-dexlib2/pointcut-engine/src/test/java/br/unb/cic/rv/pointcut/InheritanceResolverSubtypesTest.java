package br.unb.cic.rv.pointcut;

import com.android.tools.smali.dexlib2.AccessFlags;
import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.DexFile;
import com.android.tools.smali.dexlib2.immutable.ImmutableClassDef;
import com.android.tools.smali.dexlib2.immutable.ImmutableDexFile;

import org.junit.jupiter.api.Test;

import java.nio.file.Path;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * {@link InheritanceResolver#subtypesOf(String)} — the enumeration half of {@code T+}
 * semantics. A pattern like {@code staticinitialization(com.example.Animal+)} must expand
 * to every concrete subtype the APK declares, reached through the superclass AND interface
 * chains, transitively (a grandchild counts), while leaving unrelated classes out.
 *
 * <p>The fixture is a single synthetic APK dex declaring one class hierarchy plus one
 * interface hierarchy, so the whole reachable-subtype closure is exercised by one
 * {@code subtypesOf} call each — no android.jar, no real APK. The {@link AndroidClassIndex}
 * points at a non-existent path, so every framework lookup degrades to "not found" and the
 * assertions isolate the APK-graph walk.
 */
class InheritanceResolverSubtypesTest {

    // --- class hierarchy: Animal <- Dog <- Puppy, Animal <- Cat, Object <- Rock ----------
    private static final String ANIMAL = "Lcom/example/Animal;";
    private static final String DOG    = "Lcom/example/Dog;";
    private static final String PUPPY  = "Lcom/example/Puppy;";
    private static final String CAT    = "Lcom/example/Cat;";
    private static final String ROCK   = "Lcom/example/Rock;";
    // --- interface hierarchy: Swimmer (iface) <- Fish (implements) -----------------------
    private static final String SWIMMER = "Lcom/example/Swimmer;";
    private static final String FISH    = "Lcom/example/Fish;";

    private static final String OBJECT = "Ljava/lang/Object;";

    /** Concrete class {@code type extends superclass}, no interfaces, no members. */
    private static ClassDef clazz(String type, String superclass) {
        return new ImmutableClassDef(type, AccessFlags.PUBLIC.getValue(), superclass,
                Collections.emptyList(), null, null,
                Collections.emptyList(), Collections.emptyList());
    }

    /** Interface {@code type}; dexlib2 models an interface's superclass as Object. */
    private static ClassDef iface(String type) {
        return new ImmutableClassDef(type,
                AccessFlags.PUBLIC.getValue() | AccessFlags.INTERFACE.getValue()
                        | AccessFlags.ABSTRACT.getValue(),
                OBJECT, Collections.emptyList(), null, null,
                Collections.emptyList(), Collections.emptyList());
    }

    /** Concrete class {@code type extends Object implements ifaces}. */
    private static ClassDef implementor(String type, String... ifaces) {
        return new ImmutableClassDef(type, AccessFlags.PUBLIC.getValue(), OBJECT,
                List.of(ifaces), null, null,
                Collections.emptyList(), Collections.emptyList());
    }

    private static InheritanceResolver resolver() {
        DexFile dex = new ImmutableDexFile(Opcodes.getDefault(), List.of(
                clazz(ANIMAL, OBJECT),
                clazz(DOG, ANIMAL),
                clazz(PUPPY, DOG),
                clazz(CAT, ANIMAL),
                clazz(ROCK, OBJECT),
                iface(SWIMMER),
                implementor(FISH, SWIMMER)));
        return new InheritanceResolver(
                new AndroidClassIndex(Path.of("/tmp/nope.jar")), List.of(dex));
    }

    @Test
    void subtypesOfEnumeratesTransitiveClassDescendantsAndTheParentItself() {
        // Animal+ reaches Animal (the parent is present in the APK, so it is part of its
        // own T+ set), Dog (direct subclass), Puppy (grandchild — reached through Dog),
        // and Cat (sibling of Dog). Rock extends Object only, so it is NOT in the closure.
        List<String> subs = resolver().subtypesOf("com.example.Animal");
        assertTrue(subs.contains("com.example.Animal"), "parent itself is part of Animal+");
        assertTrue(subs.contains("com.example.Dog"),    "direct subclass Dog");
        assertTrue(subs.contains("com.example.Puppy"),  "grandchild Puppy (transitive)");
        assertTrue(subs.contains("com.example.Cat"),    "sibling subclass Cat");
        assertFalse(subs.contains("com.example.Rock"),  "Rock is unrelated (extends Object)");
        // Exactly those four, no duplicates (subtypesOf collapses via a seen-set).
        assertEquals(4, subs.size(),
                "Animal+ must contain precisely {Animal, Dog, Puppy, Cat}, got " + subs);
    }

    @Test
    void subtypesOfEnumeratesInterfaceImplementors() {
        // Swimmer+ reaches the interface itself plus Fish, whose interface list names
        // Swimmer directly — proving the enumeration follows interface edges, not only
        // the superclass chain (Fish extends Object, so a superclass-only walk would miss it).
        List<String> subs = resolver().subtypesOf("com.example.Swimmer");
        assertTrue(subs.contains("com.example.Swimmer"), "the interface itself is part of Swimmer+");
        assertTrue(subs.contains("com.example.Fish"),    "Fish implements Swimmer");
        assertFalse(subs.contains("com.example.Dog"),    "Dog does not implement Swimmer");
        assertEquals(2, subs.size(),
                "Swimmer+ must contain precisely {Swimmer, Fish}, got " + subs);
    }

    @Test
    void subtypesOfUnknownParentIsEmpty() {
        // A parent absent from the APK with no declared descendants yields the empty list:
        // no APK class is assignable to it and the parent-self branch does not fire
        // (containsKey is false), so nothing is added. Negative control for the two above.
        assertTrue(resolver().subtypesOf("com.example.Ghost").isEmpty(),
                "an unknown parent with no APK descendants has an empty T+ set");
    }
}
