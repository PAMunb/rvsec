package br.unb.cic.rv.pointcut;

import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Predicate;

/**
 * Resolves a simple AspectJ type name (as it appears in a pointcut expression,
 * e.g. {@code "Iterator"}, {@code "byte[]"}, {@code "String"}) into the
 * fully-qualified DEX descriptor (e.g. {@code "Ljava/util/Iterator;"},
 * {@code "[B"}, {@code "Ljava/lang/String;"}).
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
 * <p>Nested types (INV-INS-162): a dotted name reached by any of these steps, or written
 * as {@code Outer.Inner} with {@code Outer} resolvable as a simple name, is first asked
 * of the {@code classExists} lookup as written; when no class of that name exists, its
 * dots are replaced by {@code $} from the right, one at a time, until the lookup answers
 * true. {@code java.security.KeyStore.ProtectionParameter} thus resolves to
 * {@code java.security.KeyStore$ProtectionParameter}. When no candidate exists, the name
 * the steps above produced is kept.
 *
 * <p>The descriptor's {@code imports} list and the {@code classExists} lookup are the
 * authority — the resolver never probes an external classpath itself (design D2: parsing
 * is driven by the emitted JSON, not by compile-time reflection).
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
    private final Predicate<String> classExists;

    /**
     * @param imports list as emitted by DescriptorWriter (e.g. {@code "java.util.Iterator"},
     *                {@code "java.util.*"}). Static imports are accepted with the
     *                {@code "static "} prefix — the resolver strips it during matching.
     */
    public TypeResolver(List<String> imports) {
        this(imports, s -> false);
    }

    /**
     * @param imports     as in {@link #TypeResolver(List)}
     * @param classExists answers whether a class with the given internal name
     *                    ({@code /}-separated, nested classes with {@code $}) exists in the
     *                    framework index or the APK; it lets a dotted name such as
     *                    {@code KeyStore.ProtectionParameter} resolve to a nested class
     */
    public TypeResolver(List<String> imports, Predicate<String> classExists) {
        this.imports = imports == null ? Collections.emptyList() : imports;
        this.classExists = classExists == null ? s -> false : classExists;
    }

    /**
     * @param simpleType e.g. {@code "Iterator"}, {@code "byte[]"},
     *                   {@code "java.lang.String"}, {@code "int"}, {@code "void"}.
     * @return DEX descriptor (e.g. {@code "Ljava/util/Iterator;"}, {@code "[B"},
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
        } else {
            String fqn = s.contains(".") ? resolveQualified(s, s) : resolveFqn(s);
            base = "L" + fqn.replace('.', '/') + ";";
        }
        StringBuilder prefix = new StringBuilder();
        for (int i = 0; i < arrayDepth; i++) prefix.append('[');
        return prefix + base;
    }

    /**
     * Simple-name → FQN. A nested class comes back as its binary name
     * ({@code java.security.KeyStore$ProtectionParameter}) when {@code classExists}
     * knows it.
     */
    public String resolveFqn(String simpleName) {
        String fqn = lookupFqn(simpleName);
        if (simpleName.contains(".")) {
            return resolveQualified(simpleName, fqn);
        }
        String binary = existingBinaryName(fqn);
        return binary != null ? binary : fqn;
    }

    /**
     * A dotted name as written, then with its first segment resolved as a simple name
     * ({@code KeyStore.Entry} under the import {@code java.security.KeyStore}); the first
     * candidate {@code classExists} knows, in binary form, or {@code fallback}.
     */
    private String resolveQualified(String dotted, String fallback) {
        String binary = existingBinaryName(dotted);
        if (binary != null) return binary;
        int dot = dotted.indexOf('.');
        binary = existingBinaryName(lookupFqn(dotted.substring(0, dot)) + dotted.substring(dot));
        return binary != null ? binary : fallback;
    }

    /**
     * The dotted {@code fqn} in binary form ({@code .} between packages and the class,
     * {@code $} before each nested class) for the first candidate {@code classExists}
     * knows: the name as written, then with its dots replaced by {@code $} from the
     * right, one at a time. {@code null} when no candidate exists.
     */
    private String existingBinaryName(String fqn) {
        char[] internal = fqn.replace('.', '/').toCharArray();
        for (int i = internal.length; i >= 0; i--) {
            if (i < internal.length) {
                if (internal[i] != '/') continue;
                internal[i] = '$';
            }
            String candidate = new String(internal);
            if (classExists.test(candidate)) return candidate.replace('/', '.');
        }
        return null;
    }

    private String lookupFqn(String simpleName) {
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
