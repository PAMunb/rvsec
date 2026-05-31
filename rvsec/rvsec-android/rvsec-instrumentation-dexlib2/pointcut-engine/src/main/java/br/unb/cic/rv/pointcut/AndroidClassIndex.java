package br.unb.cic.rv.pointcut;

import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassVisitor;
import org.objectweb.asm.MethodVisitor;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.Type;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

/**
 * Parses an {@code android.jar} with ASM to answer two questions:
 * <ol>
 *   <li>What methods of a given class are declared in the Android API?
 *       (Optionally filter to static methods only.)</li>
 *   <li>Is class {@code A} assignable from class {@code B} in the Android API
 *       (inheritance chain)?</li>
 * </ol>
 *
 * <p>Why ASM and not {@link Class#forName}: the JVM's bootstrap classloader always
 * wins for {@code java.*} packages, leaking host-JDK-specific overloads (e.g.
 * {@code SecureRandomParameters} added in JDK 9) even when we provide a custom
 * {@link java.net.URLClassLoader} scoped to android.jar. Parsing the .class bytes
 * directly bypasses that.
 *
 * <p>Thread-safety: lazy-loads class metadata on first query; all public methods
 * are synchronized on the instance.
 *
 * <p>§4.PERF.P1: the backing {@code android.jar} {@link ZipFile} is opened ONCE on the
 * first cache-missing {@link #load} and reused for every subsequent ancestor-walk step,
 * instead of being reopened per class. The instance is {@link AutoCloseable}; callers that
 * own its lifetime may close it to release the handle deterministically. In the short-lived
 * per-APK CLI process the handle is also released at process exit. Output is unchanged —
 * same archive bytes, same ASM parse (perf-only).
 */
public final class AndroidClassIndex implements AutoCloseable {

    public static final class MethodInfo {
        public final String name;
        /** DEX-style internal descriptor: {@code (Ljava/lang/String;)Ljava/lang/Object;}. */
        public final String descriptor;
        public final int access;
        /** Java FQN of each parameter (arrays use {@code T[]}); primitives as {@code int} etc. */
        public final List<String> paramFqns;
        public final String returnFqn;

        MethodInfo(String name, String descriptor, int access,
                   List<String> paramFqns, String returnFqn) {
            this.name = name;
            this.descriptor = descriptor;
            this.access = access;
            this.paramFqns = paramFqns;
            this.returnFqn = returnFqn;
        }

        public boolean isStatic() { return (access & Opcodes.ACC_STATIC) != 0; }
    }

    private static final class ClassInfo {
        final String internalName;           // e.g. "java/util/ArrayList"
        final String superInternal;          // null for java/lang/Object
        final List<String> interfaceInternals;
        final List<MethodInfo> methods;

        ClassInfo(String internal, String sup, List<String> ifaces, List<MethodInfo> methods) {
            this.internalName = internal;
            this.superInternal = sup;
            this.interfaceInternals = ifaces;
            this.methods = methods;
        }
    }

    private final Path androidJar;
    private final Map<String, ClassInfo> byInternal = new HashMap<>();
    /** Negative cache — classes we tried to load and failed. */
    private final Set<String> missing = new HashSet<>();
    /**
     * §4.PERF.P1: the opened archive, lazily initialised on first {@link #load} and reused for
     * every subsequent class load. {@code null} until first use, after {@link #close}, or when
     * {@code androidJar} is null / fails to open (in which case every framework lookup degrades
     * to "not found", identical to the prior per-call open-failure path).
     */
    private ZipFile archive;
    /** Guards against re-opening after a deliberate {@link #close} or a prior open failure. */
    private boolean archiveResolved;

    public AndroidClassIndex(Path androidJar) {
        this.androidJar = androidJar;
    }

    /**
     * All static methods of {@code classFqn} named {@code methodName}. Empty list
     * if class is not in android.jar or has no such static method.
     */
    public synchronized List<MethodInfo> staticMethods(String classFqn, String methodName) {
        return methods(classFqn, methodName, /*onlyStatic=*/ true);
    }

    /**
     * All declared methods of {@code classFqn} named {@code methodName}. When
     * {@code onlyStatic} is true, filters to static ones. Empty list if class not
     * in android.jar.
     */
    public synchronized List<MethodInfo> methods(String classFqn, String methodName,
                                                  boolean onlyStatic) {
        ClassInfo ci = load(toInternal(classFqn));
        if (ci == null) return Collections.emptyList();
        List<MethodInfo> out = new ArrayList<>();
        for (MethodInfo m : ci.methods) {
            if (!m.name.equals(methodName)) continue;
            if (onlyStatic && !m.isStatic()) continue;
            out.add(m);
        }
        return out;
    }

    /**
     * True if {@code superFqn} is the same as or a supertype of {@code subFqn}
     * in the Android API. Walks superclass and interface chains via cached metadata.
     */
    public synchronized boolean isAssignableFrom(String superFqn, String subFqn) {
        if (superFqn.equals(subFqn)) return true;
        // java.lang.Object is a supertype of every non-primitive.
        if ("java.lang.Object".equals(superFqn)) return !isPrimitiveFqn(subFqn);
        String superInt = toInternal(superFqn);
        String subInt = toInternal(subFqn);
        Set<String> visited = new HashSet<>();
        return walkAncestors(subInt, superInt, visited);
    }

    private boolean walkAncestors(String currentInt, String targetInt, Set<String> visited) {
        if (!visited.add(currentInt)) return false;
        if (currentInt.equals(targetInt)) return true;
        ClassInfo ci = load(currentInt);
        if (ci == null) return false;
        if (ci.superInternal != null && walkAncestors(ci.superInternal, targetInt, visited)) {
            return true;
        }
        for (String iface : ci.interfaceInternals) {
            if (walkAncestors(iface, targetInt, visited)) return true;
        }
        return false;
    }

    private ClassInfo load(String internal) {
        if (internal == null || internal.isEmpty()) return null;
        ClassInfo cached = byInternal.get(internal);
        if (cached != null) return cached;
        if (missing.contains(internal)) return null;

        // §4.PERF.P1: reuse the single opened archive instead of reopening per class.
        ZipFile zf = openArchive();
        if (zf == null) {
            missing.add(internal);
            return null;
        }
        try {
            ZipEntry e = zf.getEntry(internal + ".class");
            if (e == null) {
                missing.add(internal);
                return null;
            }
            try (InputStream is = zf.getInputStream(e)) {
                Collector c = new Collector();
                new ClassReader(is).accept(c,
                        ClassReader.SKIP_CODE | ClassReader.SKIP_DEBUG | ClassReader.SKIP_FRAMES);
                ClassInfo ci = new ClassInfo(
                        c.name, c.superName,
                        c.interfaces != null ? List.of(c.interfaces) : Collections.emptyList(),
                        c.methods);
                byInternal.put(internal, ci);
                return ci;
            }
        } catch (IOException ex) {
            missing.add(internal);
            return null;
        }
    }

    /**
     * §4.PERF.P1: open the {@code android.jar} archive once, lazily, and cache the handle.
     * Returns {@code null} when there is no jar, after {@link #close}, or when the open fails —
     * the same "framework lookups become not-found" degradation the per-call open had.
     */
    private ZipFile openArchive() {
        if (archive != null) return archive;
        if (archiveResolved) return null;       // already tried and failed, or closed
        archiveResolved = true;
        if (androidJar == null) return null;
        try {
            archive = new ZipFile(androidJar.toFile());
        } catch (IOException ex) {
            archive = null;
        }
        return archive;
    }

    /** §4.PERF.P1: close the cached archive handle. Idempotent; safe to call when never opened. */
    @Override
    public synchronized void close() {
        archiveResolved = true;
        if (archive != null) {
            try {
                archive.close();
            } catch (IOException ignored) {
                // best-effort release; nothing actionable on close failure
            }
            archive = null;
        }
    }

    private static String toInternal(String fqn) {
        return fqn == null ? null : fqn.replace('.', '/');
    }

    private static boolean isPrimitiveFqn(String fqn) {
        switch (fqn) {
            case "void": case "boolean": case "byte": case "short": case "char":
            case "int":  case "long":    case "float": case "double": return true;
            default: return false;
        }
    }

    /** Convert an ASM {@link Type} into a Java FQN (uses {@code T[]} for arrays). */
    static String typeToFqn(Type t) {
        switch (t.getSort()) {
            case Type.VOID:    return "void";
            case Type.BOOLEAN: return "boolean";
            case Type.BYTE:    return "byte";
            case Type.SHORT:   return "short";
            case Type.CHAR:    return "char";
            case Type.INT:     return "int";
            case Type.LONG:    return "long";
            case Type.FLOAT:   return "float";
            case Type.DOUBLE:  return "double";
            case Type.ARRAY:   return typeToFqn(t.getElementType())
                                       + "[]".repeat(t.getDimensions());
            case Type.OBJECT:  return t.getClassName(); // dotted FQN
            default: throw new IllegalStateException("unexpected Type sort: " + t.getSort());
        }
    }

    // --- ASM visitor ---------------------------------------------------------

    private static final class Collector extends ClassVisitor {
        String name;
        String superName;
        String[] interfaces;
        final List<MethodInfo> methods = new ArrayList<>();

        Collector() { super(Opcodes.ASM9); }

        @Override
        public void visit(int version, int access, String name, String signature,
                          String superName, String[] interfaces) {
            this.name = name;
            this.superName = superName;
            this.interfaces = interfaces;
        }

        @Override
        public MethodVisitor visitMethod(int access, String name, String descriptor,
                                         String signature, String[] exceptions) {
            Type mt = Type.getMethodType(descriptor);
            List<String> params = new ArrayList<>();
            for (Type p : mt.getArgumentTypes()) params.add(typeToFqn(p));
            String ret = typeToFqn(mt.getReturnType());
            methods.add(new MethodInfo(name, descriptor, access, params, ret));
            return null;
        }
    }
}
