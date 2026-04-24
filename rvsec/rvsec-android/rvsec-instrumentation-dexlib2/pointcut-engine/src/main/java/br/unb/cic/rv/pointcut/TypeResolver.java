package br.unb.cic.rv.pointcut;

import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Resolves a simple AspectJ type name (as it appears in a pointcut expression,
 * e.g. {@code "Cipher"}, {@code "byte[]"}, {@code "String"}) into the fully-qualified
 * DEX descriptor (e.g. {@code "Ljavax/crypto/Cipher;"}, {@code "[B"},
 * {@code "Ljava/lang/String;"}).
 *
 * <p>Resolution strategy, in order:
 * <ol>
 *   <li>Primitive/void — direct table lookup.</li>
 *   <li>Already-qualified (contains a {@code .}) — split into package + class verbatim.</li>
 *   <li>Exact-match import: {@code some.pkg.Cipher} ending in the simple name.</li>
 *   <li>Built-in fallback: {@link #BUILTIN} table for common java.* types.</li>
 *   <li>Wildcard import: first {@code some.pkg.*} in the list wins.</li>
 *   <li>Last resort: {@code java.lang.<name>}.</li>
 * </ol>
 *
 * <p>The descriptor's {@code imports} list is the authority — the resolver never
 * probes an external classpath (design D2: parsing is driven by the emitted JSON,
 * not by compile-time reflection).
 */
public final class TypeResolver {

    private static final Map<String, String> PRIMITIVES = new HashMap<>();
    static {
        PRIMITIVES.put("void",    "V");
        PRIMITIVES.put("boolean", "Z");
        PRIMITIVES.put("byte",    "B");
        PRIMITIVES.put("short",   "S");
        PRIMITIVES.put("char",    "C");
        PRIMITIVES.put("int",     "I");
        PRIMITIVES.put("long",    "J");
        PRIMITIVES.put("float",   "F");
        PRIMITIVES.put("double",  "D");
    }

    /** Common simple-name → FQN fallback when imports don't cover it. */
    private static final Map<String, String> BUILTIN = new HashMap<>();
    static {
        BUILTIN.put("Object",       "java.lang.Object");
        BUILTIN.put("String",       "java.lang.String");
        BUILTIN.put("CharSequence", "java.lang.CharSequence");
        BUILTIN.put("Integer",      "java.lang.Integer");
        BUILTIN.put("Long",         "java.lang.Long");
        BUILTIN.put("Boolean",      "java.lang.Boolean");
        BUILTIN.put("Throwable",    "java.lang.Throwable");
        BUILTIN.put("Exception",    "java.lang.Exception");
        BUILTIN.put("Thread",       "java.lang.Thread");
        BUILTIN.put("Class",        "java.lang.Class");
        BUILTIN.put("List",         "java.util.List");
        BUILTIN.put("Map",          "java.util.Map");
        BUILTIN.put("Set",          "java.util.Set");
        BUILTIN.put("Collection",   "java.util.Collection");
        BUILTIN.put("Comparable",   "java.lang.Comparable");
        BUILTIN.put("Iterator",     "java.util.Iterator");
        BUILTIN.put("InputStream",  "java.io.InputStream");
        BUILTIN.put("OutputStream", "java.io.OutputStream");
        BUILTIN.put("Reader",       "java.io.Reader");
        BUILTIN.put("Writer",       "java.io.Writer");
        BUILTIN.put("File",         "java.io.File");
        BUILTIN.put("Serializable", "java.io.Serializable");
    }

    private final List<String> imports;

    /**
     * @param imports list as emitted by DescriptorWriter (e.g. {@code "javax.crypto.Cipher"},
     *                {@code "java.util.*"}). Static imports are accepted with the
     *                {@code "static "} prefix — the resolver strips it during matching.
     */
    public TypeResolver(List<String> imports) {
        this.imports = imports == null ? Collections.emptyList() : imports;
    }

    /**
     * @param simpleType e.g. {@code "Cipher"}, {@code "byte[]"},
     *                   {@code "java.lang.String"}, {@code "int"}, {@code "void"}.
     * @return DEX descriptor (e.g. {@code "Ljavax/crypto/Cipher;"}, {@code "[B"},
     *         {@code "I"}).
     */
    public String toDescriptor(String simpleType) {
        String s = simpleType.trim();
        int arrayDepth = 0;
        while (s.endsWith("[]")) {
            arrayDepth++;
            s = s.substring(0, s.length() - 2).trim();
        }
        String base;
        String prim = PRIMITIVES.get(s);
        if (prim != null) {
            base = prim;
        } else if (s.contains(".")) {
            base = "L" + s.replace('.', '/') + ";";
        } else {
            String fqn = resolveFqn(s);
            base = "L" + fqn.replace('.', '/') + ";";
        }
        StringBuilder prefix = new StringBuilder();
        for (int i = 0; i < arrayDepth; i++) prefix.append('[');
        return prefix + base;
    }

    /** Simple-name → FQN. */
    public String resolveFqn(String simpleName) {
        // Exact import: "foo.bar.Cipher" ending in "Cipher".
        for (String imp : imports) {
            String i = imp.startsWith("static ") ? imp.substring("static ".length()) : imp;
            if (i.endsWith("." + simpleName)) return i;
        }
        // Built-in fallback comes BEFORE wildcards so that, e.g., "String" always
        // resolves to java.lang.String even if a wildcard import matches first
        // alphabetically.
        String builtin = BUILTIN.get(simpleName);
        if (builtin != null) return builtin;
        // Wildcard import: first "foo.bar.*" wins. We cannot verify the class
        // exists in any jar without a classpath, so this is heuristic.
        for (String imp : imports) {
            if (imp.endsWith(".*")) {
                return imp.substring(0, imp.length() - 2) + "." + simpleName;
            }
        }
        // Last resort.
        return "java.lang." + simpleName;
    }
}
