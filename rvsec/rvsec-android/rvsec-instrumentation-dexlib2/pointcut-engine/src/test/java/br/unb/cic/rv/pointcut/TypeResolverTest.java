package br.unb.cic.rv.pointcut;

import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIf;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Collections;
import java.util.List;
import java.util.Set;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.assertEquals;

class TypeResolverTest {

    private static final List<String> IMPORTS = List.of(
            "javax.crypto.Cipher",
            "javax.crypto.spec.SecretKeySpec",
            "java.security.KeyPairGenerator",
            "java.util.*",
            "static br.unb.cic.mop.jca.util.CipherTransformationUtil.*"
    );

    private final TypeResolver resolver = new TypeResolver(IMPORTS);

    // --- primitives ---------------------------------------------------------

    @Test
    void primitivesMapToSingleLetterDescriptors() {
        assertEquals("V", resolver.toDescriptor("void"));
        assertEquals("Z", resolver.toDescriptor("boolean"));
        assertEquals("B", resolver.toDescriptor("byte"));
        assertEquals("S", resolver.toDescriptor("short"));
        assertEquals("C", resolver.toDescriptor("char"));
        assertEquals("I", resolver.toDescriptor("int"));
        assertEquals("J", resolver.toDescriptor("long"));
        assertEquals("F", resolver.toDescriptor("float"));
        assertEquals("D", resolver.toDescriptor("double"));
    }

    @Test
    void primitiveArraysGetLeadingBrackets() {
        assertEquals("[B", resolver.toDescriptor("byte[]"));
        assertEquals("[[I", resolver.toDescriptor("int[][]"));
    }

    // --- exact imports -----------------------------------------------------

    @Test
    void exactImportWinsOverBuiltin() {
        assertEquals("Ljavax/crypto/Cipher;", resolver.toDescriptor("Cipher"));
        assertEquals("Ljava/security/KeyPairGenerator;",
                resolver.toDescriptor("KeyPairGenerator"));
    }

    // --- builtin fallback --------------------------------------------------

    @Test
    void builtinResolvesWithoutImport() {
        // String is in java.lang — no import needed; builtin table wins.
        TypeResolver r = new TypeResolver(Collections.emptyList());
        assertEquals("Ljava/lang/String;", r.toDescriptor("String"));
        assertEquals("Ljava/lang/Object;", r.toDescriptor("Object"));
    }

    @Test
    void builtinWinsOverWildcardImport() {
        // java.util.* could otherwise match String, but builtin table is checked first.
        assertEquals("Ljava/lang/String;", resolver.toDescriptor("String"));
    }

    // --- wildcard imports --------------------------------------------------

    @Test
    void wildcardImportResolvesUnknownSimpleName() {
        // HashMap is in java.util.*; no exact import, no builtin → wildcard.
        assertEquals("Ljava/util/HashMap;", resolver.toDescriptor("HashMap"));
    }

    // --- already qualified --------------------------------------------------

    @Test
    void fullyQualifiedTypePassesThrough() {
        assertEquals("Ljava/security/SecureRandom;",
                resolver.toDescriptor("java.security.SecureRandom"));
    }

    @Test
    void fullyQualifiedArrayPassesThrough() {
        assertEquals("[Ljava/security/Key;",
                resolver.toDescriptor("java.security.Key[]"));
    }

    // --- last resort --------------------------------------------------------

    @Test
    void fallsBackToJavaLang() {
        // Completely unknown simple name with no imports → java.lang heuristic.
        TypeResolver r = new TypeResolver(Collections.emptyList());
        assertEquals("Ljava/lang/Something;", r.toDescriptor("Something"));
    }

    // --- static import prefix is tolerated ---------------------------------

    @Test
    void staticImportPrefixStrippedWhenMatching() {
        // "static br.unb.cic.mop.jca.util.CipherTransformationUtil.*" declares a
        // wildcard of a static helper. Its class name doesn't end in a dot + simple
        // name, so exact-import match fails and we fall through — the test just
        // asserts the resolver doesn't crash on the static prefix.
        assertEquals("Ljavax/crypto/Cipher;", resolver.toDescriptor("Cipher"));
    }

    // --- resolveFqn direct --------------------------------------------------

    @Test
    void resolveFqnDirect() {
        assertEquals("javax.crypto.Cipher", resolver.resolveFqn("Cipher"));
        assertEquals("java.lang.String", resolver.resolveFqn("String"));
        assertEquals("java.util.HashMap", resolver.resolveFqn("HashMap"));
    }

    // --- nested types (INV-INS-162) ----------------------------------------

    /** Internal names a small framework would carry. */
    private static final Set<String> KNOWN_CLASSES = Set.of(
            "java/security/KeyStore",
            "java/security/KeyStore$Entry",
            "java/security/KeyStore$ProtectionParameter",
            "java/lang/String");

    private static TypeResolver nestedResolver(List<String> imports) {
        return new TypeResolver(imports, KNOWN_CLASSES::contains);
    }

    @Test
    void nestedImportedType() {
        TypeResolver r = nestedResolver(List.of(
                "java.security.KeyStore", "java.security.KeyStore.ProtectionParameter"));
        assertEquals("Ljava/security/KeyStore$ProtectionParameter;",
                r.toDescriptor("ProtectionParameter"));
        assertEquals("Ljava/security/KeyStore$Entry;", r.toDescriptor("KeyStore.Entry"));
        assertEquals("java.security.KeyStore$ProtectionParameter",
                r.resolveFqn("ProtectionParameter"));
        assertEquals("java.security.KeyStore$Entry", r.resolveFqn("KeyStore.Entry"));
    }

    @Test
    void nestedQualifiedType() {
        TypeResolver r = nestedResolver(Collections.emptyList());
        assertEquals("Ljava/security/KeyStore$ProtectionParameter;",
                r.toDescriptor("java.security.KeyStore.ProtectionParameter"));
        assertEquals("[Ljava/security/KeyStore$Entry;",
                r.toDescriptor("java.security.KeyStore.Entry[]"));
    }

    @Test
    void topLevelUnchanged() {
        TypeResolver r = nestedResolver(List.of("java.security.KeyStore"));
        assertEquals("Ljava/security/KeyStore;", r.toDescriptor("java.security.KeyStore"));
        assertEquals("Ljava/security/KeyStore;", r.toDescriptor("KeyStore"));
        assertEquals("Ljava/lang/String;", r.toDescriptor("String"));
    }

    @Test
    void unknownNestedKeepsCurrentDescriptor() {
        TypeResolver r = nestedResolver(List.of("java.security.KeyStore"));
        assertEquals("Ljava/security/KeyStore/Missing;",
                r.toDescriptor("java.security.KeyStore.Missing"));
        assertEquals("LKeyStore/Missing;", r.toDescriptor("KeyStore.Missing"));
        assertEquals("Lcom/example/Unknown;", r.toDescriptor("com.example.Unknown"));
        // Without a lookup, a nested spelling keeps the dotted descriptor.
        TypeResolver noLookup = new TypeResolver(List.of("java.security.KeyStore"));
        assertEquals("Ljava/security/KeyStore/ProtectionParameter;",
                noLookup.toDescriptor("java.security.KeyStore.ProtectionParameter"));
        assertEquals("LKeyStore/Entry;", noLookup.toDescriptor("KeyStore.Entry"));
    }

    // --- nested types against android.jar ----------------------------------

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

    @Test
    @EnabledIf("hasAndroidJar")
    void nestedTypeResolvesAgainstTheFrameworkIndex() {
        try (AndroidClassIndex index = new AndroidClassIndex(androidJar)) {
            TypeResolver r = new TypeResolver(
                    List.of("java.security.KeyStore", "java.security.KeyStore.ProtectionParameter"),
                    index::exists);
            assertEquals("Ljava/security/KeyStore$ProtectionParameter;",
                    r.toDescriptor("ProtectionParameter"));
            assertEquals("Ljava/security/KeyStore$Entry;", r.toDescriptor("KeyStore.Entry"));
            assertEquals("Ljava/security/KeyStore;", r.toDescriptor("java.security.KeyStore"));
            assertEquals("Ljavax/crypto/Cipher;", r.toDescriptor("javax.crypto.Cipher"));
        }
    }
}
