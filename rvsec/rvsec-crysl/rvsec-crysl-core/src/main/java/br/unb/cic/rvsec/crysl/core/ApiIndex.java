package br.unb.cic.rvsec.crysl.core;

import br.unb.cic.rvsec.crysl.core.model.Signature;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.jar.JarEntry;
import java.util.jar.JarFile;
import java.util.stream.Collectors;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassVisitor;
import org.objectweb.asm.MethodVisitor;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.Type;

/**
 * An index of the Android platform's classes and methods, read once from {@code android.jar}.
 *
 * <p><strong>An index and nothing else.</strong> INV-CONF-17 forbids wiring this jar into the
 * CrySL parser's classpath, and the prohibition is about what is possible, not about what is
 * tidy. {@code CrySLModelReaderClassPath} offers to take a list of paths, which reads like an
 * offer to say "resolve names against Android rather than against this JVM" — and it is not one.
 * The virtual classpath is <em>strictly additive</em>: it appends to what the process already
 * resolves. {@code URLClassLoader} resolution is parent-first, so every name the host JDK has, the
 * host JDK wins. And {@code java.base} is loaded from the module layer rather than from
 * {@code java.class.path}, so it is not on any classpath to be removed — not even
 * {@code parent = null} takes it away. Measured: the resolved signature lines over the upstream
 * oracle are byte-for-byte identical with and without the jar on the virtual classpath.
 *
 * <p>So the platform enters the computation in exactly one place, and it enters it afterwards: a
 * signature the parser already resolved is looked up here, and its absence is a finding about the
 * pointcut ({@code Unknown{UnresolvedSignature}}), never an instruction to the parser. With a
 * single oracle this is the only place Android is consulted at all, which raises the standing of
 * the check rather than lowering it.
 *
 * <h2>Why it lives in the model module</h2>
 * <p>D-16 states the whole layering rule: the model module must not know about {@code javamop} or
 * {@code CrySLParser}. This class knows neither - it is an ASM reader over a jar - and
 * {@code M0Vitality} lives here and asks it the third of M0's three questions, so putting the index
 * on either lifter module would mean the metric could not reach its own input. Nothing else about
 * the check changes: it still runs after the parser has resolved a name, and it still answers a
 * question about the Android platform rather than instructing anybody's classpath.
 *
 * <h2>What the index does not do</h2>
 * <p>It records <em>declared</em> members, class by class, and does not follow inheritance.
 * {@code javax.crypto.SecretKey} declares no {@code destroy()}: it inherits one from
 * {@code javax.security.auth.Destroyable}, and a lookup of {@code SecretKey.destroy()} therefore
 * misses. This is a limitation of the checker, not an absence in the platform, and the two must be
 * reported as different things — six of the upstream signature lines fall into it. The limitation
 * is asserted by a test so that it stays declared rather than drifting into an unexamined
 * assumption.
 */
public final class ApiIndex {

    private final String source;
    private final Set<String> classes;
    private final Map<String, Set<String>> exactMembers;
    private final Map<String, Set<String>> memberArities;

    private ApiIndex(String source, Set<String> classes, Map<String, Set<String>> exactMembers,
                     Map<String, Set<String>> memberArities) {
        this.source = source;
        this.classes = Collections.unmodifiableSet(classes);
        this.exactMembers = Collections.unmodifiableMap(exactMembers);
        this.memberArities = Collections.unmodifiableMap(memberArities);
    }

    /**
     * Indexes one {@code android.jar}.
     *
     * <p>Read with {@code SKIP_CODE | SKIP_DEBUG | SKIP_FRAMES}: the index needs declarations, and
     * an {@code android.jar} is a stub jar whose method bodies throw anyway. Every {@code .class}
     * entry of the archive is one indexed class, nested classes included — that is the counting
     * rule the tests assert against, and API 30 gives 4750 under it.
     *
     * @param androidJar path to the platform jar
     * @return the index
     * @throws IOException if the jar cannot be read
     */
    public static ApiIndex index(Path androidJar) throws IOException {
        Objects.requireNonNull(androidJar, "androidJar is mandatory");
        if (!Files.isReadable(androidJar)) {
            throw new IOException("android.jar is not readable: " + androidJar.toAbsolutePath());
        }
        Set<String> classes = new HashSet<>();
        Map<String, Set<String>> exactMembers = new HashMap<>();
        Map<String, Set<String>> memberArities = new HashMap<>();

        try (JarFile jar = new JarFile(androidJar.toFile())) {
            for (JarEntry entry : Collections.list(jar.entries())) {
                if (entry.isDirectory() || !entry.getName().endsWith(".class")) {
                    continue;
                }
                try (InputStream in = jar.getInputStream(entry)) {
                    new ClassReader(in).accept(
                            new IndexingVisitor(classes, exactMembers, memberArities),
                            ClassReader.SKIP_CODE | ClassReader.SKIP_DEBUG | ClassReader.SKIP_FRAMES);
                }
            }
        }
        return new ApiIndex(androidJar.toAbsolutePath().toString(), classes, exactMembers, memberArities);
    }

    /** The jar this index was read from, for the report header. */
    public String source() {
        return source;
    }

    /** Number of indexed classes, nested classes counted separately. */
    public int classCount() {
        return classes.size();
    }

    /** Every indexed class, as a fully-qualified name with {@code $} between nesting levels. */
    public Set<String> classes() {
        return classes;
    }

    /**
     * @param fullyQualifiedName e.g. {@code javax.crypto.Cipher}
     * @return whether the platform declares that class
     */
    public boolean hasClass(String fullyQualifiedName) {
        return classes.contains(fullyQualifiedName);
    }

    /**
     * Exact match: the class declares a member of that name whose parameter types are these, in
     * this order. Inheritance is not followed — see the class comment.
     *
     * @param declaringType fully-qualified class
     * @param name          method name, or the class's simple name for a constructor
     * @param paramTypes    fully-qualified parameter types in declaration order
     */
    public boolean hasMethod(String declaringType, String name, List<String> paramTypes) {
        Set<String> members = exactMembers.get(declaringType);
        return members != null && members.contains(exactKey(name, paramTypes));
    }

    /**
     * Weaker match: the class declares a member of that name with that number of parameters.
     *
     * <p>Kept beside the exact match rather than folded into it, because the two answer different
     * questions and the report publishes them as different columns. A CrySL rule that writes a
     * parameter as {@code AnyType} cannot be matched exactly by construction, and counting it with
     * the genuine exact matches would overstate what was verified.
     */
    public boolean hasMethodWithArity(String declaringType, String name, int arity) {
        Set<String> members = memberArities.get(declaringType);
        return members != null && members.contains(arityKey(name, arity));
    }

    /** {@link #hasMethod} over a lifted signature. */
    public boolean hasSignature(Signature signature) {
        Objects.requireNonNull(signature, "signature is mandatory");
        return hasMethod(signature.declaringType(), signature.name(), signature.paramTypes());
    }

    /** {@link #hasMethodWithArity} over a lifted signature. */
    public boolean hasSignatureWithArity(Signature signature) {
        Objects.requireNonNull(signature, "signature is mandatory");
        return hasMethodWithArity(signature.declaringType(), signature.name(),
                signature.paramTypes().size());
    }

    private static String exactKey(String name, List<String> paramTypes) {
        return name + "(" + String.join(",", paramTypes) + ")";
    }

    private static String arityKey(String name, int arity) {
        return name + "/" + arity;
    }

    /** Collects one class and its declared members. */
    private static final class IndexingVisitor extends ClassVisitor {

        private final Set<String> classes;
        private final Map<String, Set<String>> exactMembers;
        private final Map<String, Set<String>> memberArities;
        private String className;
        private String simpleName;

        IndexingVisitor(Set<String> classes, Map<String, Set<String>> exactMembers,
                        Map<String, Set<String>> memberArities) {
            super(Opcodes.ASM9);
            this.classes = classes;
            this.exactMembers = exactMembers;
            this.memberArities = memberArities;
        }

        @Override
        public void visit(int version, int access, String name, String signature, String superName,
                          String[] interfaces) {
            this.className = name.replace('/', '.');
            int lastDot = className.lastIndexOf('.');
            int lastDollar = className.lastIndexOf('$');
            this.simpleName = className.substring(Math.max(lastDot, lastDollar) + 1);
            classes.add(className);
        }

        @Override
        public MethodVisitor visitMethod(int access, String name, String descriptor,
                                         String signature, String[] exceptions) {
            List<String> paramTypes = java.util.Arrays.stream(Type.getArgumentTypes(descriptor))
                    .map(Type::getClassName)
                    .collect(Collectors.toList());
            record(name, paramTypes);
            if ("<init>".equals(name)) {
                // Signature.name spells a constructor as the declaring type's simple name, which is
                // also how CrySL writes it. Indexing it under both spellings means a caller never
                // has to know which convention produced the name it is looking up.
                record(simpleName, paramTypes);
            }
            return null;
        }

        private void record(String name, List<String> paramTypes) {
            exactMembers.computeIfAbsent(className, key -> new HashSet<>())
                    .add(exactKey(name, paramTypes));
            memberArities.computeIfAbsent(className, key -> new HashSet<>())
                    .add(arityKey(name, paramTypes.size()));
        }
    }
}
