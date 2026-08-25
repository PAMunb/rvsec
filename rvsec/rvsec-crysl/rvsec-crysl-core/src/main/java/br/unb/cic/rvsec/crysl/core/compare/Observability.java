package br.unb.cic.rvsec.crysl.core.compare;

import br.unb.cic.rvsec.crysl.core.model.Signature;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.LinkedHashSet;
import java.util.Objects;
import java.util.Set;
import java.util.jar.JarEntry;
import java.util.jar.JarFile;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassVisitor;
import org.objectweb.asm.MethodVisitor;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.Type;

/**
 * Which calls a client program can actually emit, read from the platform's declared access.
 *
 * <p>This is the whole substance of N2. A rule can order a symbol no program is able to produce -
 * the generated {@code SecureRandom} rule orders {@code next(int)}, which is {@code protected} - and
 * a comparison that leaves such a symbol in the rule's alphabet reports the specification as more
 * restrictive than the rule for a word no execution can ever contain. The projection onto the
 * observable alphabet is what removes that artefact, and it is a measurement rather than a list:
 * the answer comes from the access flags in {@code android.jar}.
 *
 * <p>Observable means <em>declared public</em>. A {@code protected} member is reachable from a
 * subclass and a package-private one from the same package, but neither is reachable from the
 * client code these specifications monitor, and the rules describe client protocols. The reading is
 * stated here rather than assumed, because the opposite reading (protected counts as observable)
 * changes which symbols survive the projection.
 *
 * <p>The lookup is by declaring type, method name and arity, never by exact parameter list: a rule
 * signature carries {@code AnyType} wherever the rule leaves an argument unbound, and an exact
 * lookup would miss every such symbol and then treat it as unknown.
 *
 * <p>A method the index does not know is <strong>observable</strong>. Absence from the index is the
 * reader's limitation - the platform declares members on supertypes the index does not follow - and
 * projecting a symbol away because this class could not find it would be an erasure nobody
 * declared, which is the failure INV-CONF-10 exists to prevent.
 */
public final class Observability {

    /**
     * The instance that projects nothing.
     *
     * <p>Used when no platform was supplied. N2 is then not applied and the report says so, which
     * is the honest output: with no platform there is no evidence that any symbol is unobservable,
     * and assuming the projection would be the same unreviewed decision by another route.
     */
    public static final Observability EVERYTHING =
            new Observability("(no platform supplied)", Set.of(), Set.of());

    /** The counting rule behind N2 (INV-CONF-02). */
    public static final String COUNTING_RULE =
            "R-N2: a symbol is observable when the platform declares no member of that declaring "
                    + "type, name and arity, or declares at least one of them public. A member "
                    + "declared only protected, package-private or private is not observable: the "
                    + "client code these specifications monitor cannot call it.";

    private final String source;
    private final Set<String> declared;
    private final Set<String> publicMembers;

    private Observability(String source, Set<String> declared, Set<String> publicMembers) {
        this.source = source;
        this.declared = Collections.unmodifiableSet(declared);
        this.publicMembers = Collections.unmodifiableSet(publicMembers);
    }

    /**
     * Reads the access flags of one platform jar.
     *
     * @param androidJar the platform jar, read and never written
     */
    public static Observability of(Path androidJar) throws IOException {
        Objects.requireNonNull(androidJar, "androidJar is mandatory");
        if (!Files.isReadable(androidJar)) {
            throw new IOException("android.jar is not readable: " + androidJar.toAbsolutePath());
        }
        Set<String> declared = new HashSet<>();
        Set<String> publicMembers = new HashSet<>();
        try (JarFile jar = new JarFile(androidJar.toFile())) {
            for (JarEntry entry : Collections.list(jar.entries())) {
                if (entry.isDirectory() || !entry.getName().endsWith(".class")) {
                    continue;
                }
                try (InputStream in = jar.getInputStream(entry)) {
                    new ClassReader(in).accept(new AccessVisitor(declared, publicMembers),
                            ClassReader.SKIP_CODE | ClassReader.SKIP_DEBUG
                                    | ClassReader.SKIP_FRAMES);
                }
            }
        }
        return new Observability(androidJar.toAbsolutePath().toString(), declared, publicMembers);
    }

    /** The jar the flags were read from, or the note that none was supplied. */
    public String source() {
        return source;
    }

    /** Whether this instance can answer anything at all; {@link #EVERYTHING} cannot. */
    public boolean populated() {
        return !declared.isEmpty();
    }

    /** Whether a client program can emit this call. */
    public boolean observable(Signature signature) {
        String key = key(signature.declaringType(), signature.name(),
                signature.paramTypes().size());
        return !declared.contains(key) || publicMembers.contains(key);
    }

    private static String key(String declaringType, String name, int arity) {
        return declaringType + "#" + name + "/" + arity;
    }

    /** Records every declared member and, separately, every public one. */
    private static final class AccessVisitor extends ClassVisitor {

        private final Set<String> declared;
        private final Set<String> publicMembers;
        private String className;
        private String simpleName;

        AccessVisitor(Set<String> declared, Set<String> publicMembers) {
            super(Opcodes.ASM9);
            this.declared = declared;
            this.publicMembers = publicMembers;
        }

        @Override
        public void visit(int version, int access, String name, String signature, String superName,
                          String[] interfaces) {
            this.className = name.replace('/', '.');
            int lastDot = className.lastIndexOf('.');
            int lastDollar = className.lastIndexOf('$');
            this.simpleName = className.substring(Math.max(lastDot, lastDollar) + 1);
        }

        @Override
        public MethodVisitor visitMethod(int access, String name, String descriptor,
                                         String signature, String[] exceptions) {
            int arity = Type.getArgumentTypes(descriptor).length;
            boolean isPublic = (access & Opcodes.ACC_PUBLIC) != 0;
            record(name, arity, isPublic);
            if ("<init>".equals(name)) {
                // Signature.name spells a constructor as the declaring type's simple name, which is
                // also how CrySL writes it, so both spellings are indexed and no caller has to know
                // which convention produced the name it is looking up.
                record(simpleName, arity, isPublic);
            }
            return null;
        }

        private void record(String name, int arity, boolean isPublic) {
            String key = key(className, name, arity);
            declared.add(key);
            if (isPublic) {
                publicMembers.add(key);
            }
        }
    }

    /** The alphabet letters of a language that no program can emit. */
    public Set<Signature> unobservable(Set<Signature> alphabet) {
        Set<Signature> refused = new LinkedHashSet<>();
        for (Signature signature : alphabet) {
            if (!observable(signature)) {
                refused.add(signature);
            }
        }
        return refused;
    }
}
