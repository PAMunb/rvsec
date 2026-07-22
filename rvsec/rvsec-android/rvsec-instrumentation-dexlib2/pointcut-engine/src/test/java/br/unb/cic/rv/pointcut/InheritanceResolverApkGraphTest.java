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

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * {@link InheritanceResolver} walking the APK class graph ({@code apkByDescriptor}) and
 * building it from dex inputs. These exercise the resolver's own dexlib2-backed walk with
 * an empty {@link AndroidClassIndex}, so no answer leaks in from android.jar — every
 * true/false is decided by the APK-declared superclass/interface edges.
 *
 * <p>Scenarios: a multi-hop superclass chain (grandparent reachable), a multi-hop interface
 * chain (a super-interface reachable through an implementing class), descriptor-form inputs
 * (accepted as-is), a superclass cycle (walk terminates, never loops), a root class with no
 * declared superclass (walk stops cleanly), and index construction via the varargs
 * constructor including the {@code null}-array and {@code null}-element degradations.
 */
class InheritanceResolverApkGraphTest {

    private static final AndroidClassIndex EMPTY_ANDROID =
            new AndroidClassIndex(Path.of("/tmp/nope.jar"));

    private static final String OBJECT = "Ljava/lang/Object;";

    private static ClassDef clazz(String type, String superclass, String... ifaces) {
        return new ImmutableClassDef(type, AccessFlags.PUBLIC.getValue(), superclass,
                List.of(ifaces), null, null,
                Collections.emptyList(), Collections.emptyList());
    }

    /** Interface {@code type} with the given super-interfaces (dexlib2: superclass Object). */
    private static ClassDef iface(String type, String... superIfaces) {
        return new ImmutableClassDef(type,
                AccessFlags.PUBLIC.getValue() | AccessFlags.INTERFACE.getValue()
                        | AccessFlags.ABSTRACT.getValue(),
                OBJECT, List.of(superIfaces), null, null,
                Collections.emptyList(), Collections.emptyList());
    }

    private static InheritanceResolver resolver(ClassDef... classes) {
        DexFile dex = new ImmutableDexFile(Opcodes.getDefault(), List.of(classes));
        return new InheritanceResolver(EMPTY_ANDROID, List.of(dex));
    }

    @Test
    void transitiveSuperclassChainIsAssignable() {
        // A extends B extends C — all APK-declared. C is reachable from A only by walking
        // two superclass hops, so isAssignableFrom(C, A) exercises the recursive super step
        // past the immediate parent. The relation is one-directional: A is not a supertype of C.
        InheritanceResolver ir = resolver(
                clazz("Lcom/example/A;", "Lcom/example/B;"),
                clazz("Lcom/example/B;", "Lcom/example/C;"),
                clazz("Lcom/example/C;", OBJECT));
        assertTrue(ir.isAssignableFrom("com.example.C", "com.example.A"),
                "grandparent C is a supertype of A (two superclass hops)");
        assertTrue(ir.isAssignableFrom("com.example.B", "com.example.A"),
                "direct parent B is a supertype of A");
        assertFalse(ir.isAssignableFrom("com.example.A", "com.example.C"),
                "subtype A is NOT a supertype of C");
    }

    @Test
    void transitiveInterfaceChainIsAssignable() {
        // Impl implements SubIface; SubIface extends Iface1. Iface1 is reachable from Impl
        // only through the interface edge of Impl AND then the interface edge of SubIface,
        // so isAssignableFrom(Iface1, Impl) drives the interface-recursion branch to depth 2.
        InheritanceResolver ir = resolver(
                clazz("Lcom/example/Impl;", OBJECT, "Lcom/example/SubIface;"),
                iface("Lcom/example/SubIface;", "Lcom/example/Iface1;"),
                iface("Lcom/example/Iface1;"));
        assertTrue(ir.isAssignableFrom("com.example.SubIface", "com.example.Impl"),
                "direct interface SubIface is a supertype of Impl");
        assertTrue(ir.isAssignableFrom("com.example.Iface1", "com.example.Impl"),
                "super-interface Iface1 is a supertype of Impl (transitive interface edge)");
    }

    @Test
    void descriptorFormInputsAreAccepted() {
        // Callers may pass either dotted FQNs or JVM descriptors. Descriptor-form arguments
        // (Lcom/example/..;) are recognised as already-in-form and used directly, so the
        // same A-extends-B relation resolves identically to the dotted form.
        InheritanceResolver ir = resolver(
                clazz("Lcom/example/A;", "Lcom/example/B;"),
                clazz("Lcom/example/B;", OBJECT));
        assertTrue(ir.isAssignableFrom("Lcom/example/B;", "Lcom/example/A;"),
                "descriptor-form supertype/subtype resolves the same as dotted FQNs");
    }

    @Test
    void superclassCycleTerminatesWithoutLooping() {
        // A pathological APK where A extends B and B extends A. The walk must break on the
        // visited-set guard rather than recurse forever; searching for an unrelated target
        // returns false (and, crucially, RETURNS at all).
        InheritanceResolver ir = resolver(
                clazz("Lcom/example/A;", "Lcom/example/B;"),
                clazz("Lcom/example/B;", "Lcom/example/A;"));
        assertFalse(ir.isAssignableFrom("com.example.Ghost", "com.example.A"),
                "a superclass cycle terminates and reports the unrelated target as false");
    }

    @Test
    void rootClassWithoutSuperclassTerminatesWalk() {
        // A class whose superclass is absent (the root of the APK graph, as java.lang.Object
        // would be) has no super/interface edge to follow: the walk stops at it and reports
        // an unrelated target as false rather than dereferencing a null superclass.
        InheritanceResolver ir = resolver(
                new ImmutableClassDef("Lcom/example/Root;", AccessFlags.PUBLIC.getValue(),
                        null, Collections.emptyList(), null, null,
                        Collections.emptyList(), Collections.emptyList()));
        assertFalse(ir.isAssignableFrom("com.example.Ghost", "com.example.Root"),
                "a superclass-less root terminates the walk cleanly");
    }

    @Test
    void varargsConstructorIndexesEveryDex() {
        // The DexFile... constructor must index all supplied dexes. Two single-class dexes
        // are passed positionally (not as a Collection); Base's subtype set must see Sub,
        // proving both dexes landed in apkByDescriptor.
        DexFile d1 = new ImmutableDexFile(Opcodes.getDefault(),
                List.of(clazz("Lcom/example/Base;", OBJECT)));
        DexFile d2 = new ImmutableDexFile(Opcodes.getDefault(),
                List.of(clazz("Lcom/example/Sub;", "Lcom/example/Base;")));
        InheritanceResolver ir = new InheritanceResolver(EMPTY_ANDROID, d1, d2);
        assertTrue(ir.subtypesOf("com.example.Base").contains("com.example.Sub"),
                "Sub (from the second dex) is a subtype of Base (from the first)");
    }

    @Test
    void nullDexArrayYieldsNoApkClasses() {
        // Passing a null dex array degrades to an empty index rather than throwing:
        // there are no APK classes, so any subtype query is empty.
        InheritanceResolver ir = new InheritanceResolver(EMPTY_ANDROID, (DexFile[]) null);
        assertTrue(ir.subtypesOf("com.example.Anything").isEmpty(),
                "a null dex array produces an empty APK index");
    }

    @Test
    void nullDexElementIsSkipped() {
        // A null element inside the dex array is skipped; the real dex alongside it is still
        // indexed, so its declared subtype is found.
        DexFile real = new ImmutableDexFile(Opcodes.getDefault(), List.of(
                clazz("Lcom/example/Base;", OBJECT),
                clazz("Lcom/example/Sub;", "Lcom/example/Base;")));
        InheritanceResolver ir = new InheritanceResolver(EMPTY_ANDROID, real, null);
        assertTrue(ir.subtypesOf("com.example.Base").contains("com.example.Sub"),
                "the real dex is indexed even when a null dex sits beside it");
    }
}
