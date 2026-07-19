package br.unb.cic.rv.pointcut;

import com.android.tools.smali.dexlib2.AccessFlags;
import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.DexFile;
import com.android.tools.smali.dexlib2.immutable.ImmutableClassDef;
import com.android.tools.smali.dexlib2.immutable.ImmutableDexFile;

import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIf;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Collections;
import java.util.List;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * {@link InheritanceResolver} crossing from an APK leaf into the Android framework chain
 * mid-hierarchy. This is the case a purely-APK walk cannot answer: an APK class whose
 * super/interface is a framework type, queried against a framework type further UP that
 * chain. The APK graph dead-ends at the framework boundary, so {@code walkApkAncestors}
 * must hand off to {@link AndroidClassIndex} — the two arms exercised here.
 *
 * <p>Requires a real {@code android.jar} (resolved via {@code ANDROID_HOME}); with an empty
 * index the transitive framework edge is unknowable, so these are gated and skip silently
 * when no jar is present, mirroring {@link AndroidClassIndexTest}. A direct APK-super query
 * (which the walk answers without the framework) is NOT enough — the target here is a
 * framework ANCESTOR of the immediate framework parent, which only android.jar knows.
 */
class InheritanceResolverAndroidFallbackTest {

    private static Path androidJar;

    @BeforeAll
    static void resolveAndroidJar() {
        String home = System.getenv("ANDROID_HOME");
        if (home == null || home.isEmpty()) return;
        Path platforms = Path.of(home, "platforms");
        if (!Files.isDirectory(platforms)) return;
        try (Stream<Path> levels = Files.list(platforms)) {
            androidJar = levels
                    .filter(Files::isDirectory)
                    .map(p -> p.resolve("android.jar"))
                    .filter(Files::isRegularFile)
                    .max((a, b) -> a.getParent().getFileName().toString()
                            .compareTo(b.getParent().getFileName().toString()))
                    .orElse(null);
        } catch (IOException ex) {
            androidJar = null;
        }
    }

    static boolean hasAndroidJar() {
        return androidJar != null;
    }

    private static final String OBJECT = "Ljava/lang/Object;";

    private static ClassDef clazz(String type, String superclass, String... ifaces) {
        return new ImmutableClassDef(type, AccessFlags.PUBLIC.getValue(), superclass,
                List.of(ifaces), null, null,
                Collections.emptyList(), Collections.emptyList());
    }

    private static InheritanceResolver resolver(ClassDef apkClass) {
        DexFile dex = new ImmutableDexFile(Opcodes.getDefault(), List.of(apkClass));
        return new InheritanceResolver(new AndroidClassIndex(androidJar), List.of(dex));
    }

    @Test
    @EnabledIf("hasAndroidJar")
    void superclassFallbackReachesTransitiveFrameworkAncestor() {
        // APK: MyArrayList extends java.util.ArrayList (a framework class NOT in the APK).
        // Query the framework ancestor java.util.AbstractList (ArrayList's superclass).
        // The APK walk reaches ArrayList, finds no ClassDef, and hands off: android.jar
        // confirms ArrayList extends AbstractList, so MyArrayList IS an AbstractList.
        InheritanceResolver ir = resolver(
                clazz("Lcom/example/MyArrayList;", "Ljava/util/ArrayList;"));
        assertTrue(ir.isAssignableFrom("java.util.AbstractList", "com.example.MyArrayList"),
                "MyArrayList extends ArrayList extends AbstractList — reachable via android.jar");
        // Sanity: an unrelated framework type is NOT an ancestor.
        assertFalse(ir.isAssignableFrom("java.lang.Runnable", "com.example.MyArrayList"),
                "MyArrayList does not derive from Runnable");
    }

    @Test
    @EnabledIf("hasAndroidJar")
    void interfaceFallbackReachesSuperInterface() {
        // APK: MyList implements java.util.List (a framework interface NOT in the APK).
        // Query the super-interface java.util.Collection (List extends Collection).
        // The APK walk reaches List via the interface edge, finds no ClassDef, and hands
        // off: android.jar confirms List extends Collection, so MyList IS a Collection.
        InheritanceResolver ir = resolver(
                clazz("Lcom/example/MyList;", OBJECT, "Ljava/util/List;"));
        assertTrue(ir.isAssignableFrom("java.util.Collection", "com.example.MyList"),
                "MyList implements List, and List extends Collection — reachable via android.jar");
    }

    @Test
    @EnabledIf("hasAndroidJar")
    void emptyIndexCannotReachTransitiveFrameworkAncestor() {
        // Positive control for the two above: with an EMPTY android index the same
        // MyArrayList → AbstractList query is false, proving the true answers above come
        // from the framework hand-off, not from the APK graph or a short-circuit.
        DexFile dex = new ImmutableDexFile(Opcodes.getDefault(),
                List.of(clazz("Lcom/example/MyArrayList;", "Ljava/util/ArrayList;")));
        InheritanceResolver blind = new InheritanceResolver(
                new AndroidClassIndex(Path.of("/tmp/nope.jar")), List.of(dex));
        assertFalse(blind.isAssignableFrom("java.util.AbstractList", "com.example.MyArrayList"),
                "without android.jar the transitive framework ancestor is unknowable");
    }
}
