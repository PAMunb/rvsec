package br.unb.cic.rv.pointcut;

import org.junit.jupiter.api.Test;

import java.util.Collections;
import java.util.List;

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
}
