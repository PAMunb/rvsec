package br.unb.cic.rvsec.crysl.mop;

import br.unb.cic.rvsec.crysl.core.model.Signature;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import javamop.parser.ast.ImportDeclaration;
import javamop.parser.ast.aspectj.CombinedPointCut;
import javamop.parser.ast.aspectj.IDPointCut;
import javamop.parser.ast.aspectj.MethodPattern;
import javamop.parser.ast.aspectj.MethodPointCut;
import javamop.parser.ast.aspectj.NotPointCut;
import javamop.parser.ast.aspectj.PointCut;
import javamop.parser.ast.aspectj.TypePattern;

/**
 * Expands an event's pointcut into the concrete signatures it names.
 *
 * <p>This expansion is what makes the non-disjoint alphabet visible downstream: two events whose
 * pointcuts expand to the same {@link Signature} are two labels on one letter, and G03's inverse
 * morphism and G10's order comparison both need to see that. Keeping the pointcut as text — which
 * the model also does, in {@code Event.pointcutText} — would leave the overlap invisible until
 * something tried to compare the two sides.
 *
 * <p>Resolution is lexical and deliberately partial. The simple names a pointcut writes are
 * resolved through the file's own {@code import} declarations, through the declared parameter types,
 * and through the {@code java.lang} import every compilation unit has whether it writes it or not;
 * a name none of the three covers is kept exactly as written. Inventing a package beyond that would
 * be worse than leaving the name short, because whether a signature exists on the platform is
 * decided later and elsewhere, against the {@code android.jar} index, where a miss is reported as
 * {@code Unknown{UnresolvedSignature}} rather than guessed (design D-09).
 *
 * <p>The implicit {@code java.lang} import is not a convenience. Without it,
 * {@code RandomStringPassword.mop} — which writes
 * {@code call(public static String String.valueOf(Object))} and imports no {@code java.lang} — lifted
 * to {@code declaringType = "String"}, missed the {@code android.jar} index, and was published as
 * {@code Unknown{UnresolvedSignature}}: a defect of this expander wearing the costume of an absence
 * in the Android platform. That is the worst shape of error the component can make, because it
 * inflates a published "unresolved" count with the instrument's own failure, and M0's whole reason
 * for existing is to keep the two apart.
 */
public final class PointcutExpander {

    /** Memo of the {@code java.lang} lookup, shared because the answer is the same for every file. */
    private static final Map<String, Boolean> JAVA_LANG = new ConcurrentHashMap<>();

    private final Map<String, String> simpleNameToFqn = new HashMap<>();

    /**
     * @param imports        the file's import declarations, used to resolve simple names
     * @param declaredTypes  the declared parameter types as written; a parameter declared with its
     *                       fully-qualified name teaches the resolver that name too, which is how
     *                       {@code java.security.Key} resolves in files that never import it
     */
    public PointcutExpander(List<ImportDeclaration> imports, List<String> declaredTypes) {
        if (imports != null) {
            for (ImportDeclaration decl : imports) {
                if (decl == null || decl.getName() == null || decl.isAsterisk()) {
                    continue;
                }
                String fqn = decl.getName().toString();
                int dot = fqn.lastIndexOf('.');
                if (dot >= 0 && dot + 1 < fqn.length()) {
                    simpleNameToFqn.putIfAbsent(fqn.substring(dot + 1), fqn);
                }
            }
        }
        for (String declared : declaredTypes) {
            int dot = declared.lastIndexOf('.');
            if (dot >= 0 && dot + 1 < declared.length()) {
                simpleNameToFqn.putIfAbsent(declared.substring(dot + 1), declared);
            }
        }
    }

    /**
     * Every signature the pointcut names, in the order the pointcut writes them.
     *
     * <p>A {@code LinkedHashSet} rather than a list because the model field is a {@code Set} and
     * the iteration order still has to be stable across runs for the report to be diffable.
     */
    public Set<Signature> expand(PointCut pointcut) {
        Set<Signature> signatures = new LinkedHashSet<>();
        collect(pointcut, signatures);
        return signatures;
    }

    /**
     * The types a pointcut names without naming a method.
     *
     * <p>Three specifications of {@code generic_new} — {@code Collection_HashCode},
     * {@code Serializable_NoArgConstructor} and {@code URLConnection_OverrideGetPermission} —
     * declare no parameter and observe {@code staticinitialization(Collection+)} rather than a
     * {@code call(...)}. They name a type and no method, so they contribute nothing to the alphabet
     * and are still <em>about</em> a type, which is the field pairing runs on. The trailing
     * {@code +} of a subtype pattern is dropped: the type the specification is about is
     * {@code Collection}, and "or any subtype of it" is a matching rule and not part of the name.
     */
    public List<String> namedTypes(PointCut pointcut) {
        List<String> types = new ArrayList<>();
        collectNamedTypes(pointcut, types);
        return types;
    }

    private void collectNamedTypes(PointCut pointcut, List<String> out) {
        if (pointcut == null) {
            return;
        }
        if (pointcut instanceof CombinedPointCut combined && combined.getPointcuts() != null) {
            combined.getPointcuts().forEach(child -> collectNamedTypes(child, out));
            return;
        }
        if (pointcut instanceof IDPointCut id && id.getArgs() != null) {
            for (TypePattern argument : id.getArgs()) {
                // The subtype marker is dropped by resolve(...), for every route and not only this
                // one; see the note on resolve(String).
                String named = resolve(op(argument));
                if (!"*".equals(named)) {
                    out.add(named);
                }
            }
        }
    }

    private void collect(PointCut pointcut, Set<Signature> out) {
        if (pointcut == null) {
            return;
        }
        if (pointcut instanceof CombinedPointCut combined) {
            // Both "&&" and "||" are walked. For "||" the union is the point; for "&&" the call
            // pattern is the only child that names a method at all, so the union is the call.
            if (combined.getPointcuts() != null) {
                for (PointCut child : combined.getPointcuts()) {
                    collect(child, out);
                }
            }
            return;
        }
        if (pointcut instanceof NotPointCut) {
            // A negated call pattern excludes matches; it names no signature the event observes,
            // so it contributes nothing to the alphabet.
            return;
        }
        if (pointcut instanceof MethodPointCut method) {
            Signature signature = toSignature(method.getSignature());
            if (signature != null) {
                out.add(signature);
            }
        }
    }

    private Signature toSignature(MethodPattern pattern) {
        if (pattern == null) {
            return null;
        }
        String declaringType = resolve(op(pattern.getOwner()));
        String member = pattern.getMemberName();
        // A constructor pointcut is written "Type.new(...)". Signature names a constructor by the
        // declaring type's simple name, so translate here rather than leaving "new" in the
        // alphabet, where it would collide across every type in the corpus.
        String name = "new".equals(member) ? simpleNameOf(declaringType) : member;
        List<String> parameterTypes = new ArrayList<>();
        if (pattern.getParameters() != null) {
            for (TypePattern parameter : pattern.getParameters()) {
                parameterTypes.add(resolve(op(parameter)));
            }
        }
        // Trap (g): EventDefinition.getRetType() is null for every event of all 215 files - the
        // field is only populated by a syntax the corpus does not use. The declared return type
        // lives in the method pattern, and reading it from there is the difference between an
        // alphabet that distinguishes Mac.doFinal():byte[] from Mac.doFinal(byte[],int):void and
        // one that does not.
        String returnType = resolve(op(pattern.getType()));
        return new Signature(declaringType, name == null ? "*" : name, parameterTypes, returnType);
    }

    private static String op(TypePattern type) {
        return type == null ? "*" : type.getOp();
    }

    private static String simpleNameOf(String type) {
        int dot = type.lastIndexOf('.');
        return dot >= 0 ? type.substring(dot + 1) : type;
    }

    /**
     * Resolves a simple name to the fully-qualified one the file imports it under, keeping array
     * suffixes and wildcards untouched.
     *
     * <p>A name no declaration covers is tried once against {@code java.lang}, which every
     * compilation unit imports implicitly. Primitives and wildcards fall out of that test on their
     * own — there is no {@code java.lang.int} — so nothing declares them a special case.
     *
     * <p><strong>The trailing {@code +} of AspectJ's subtype pattern is dropped here</strong>,
     * before anything else, and for the same reason the implicit {@code java.lang} import exists:
     * {@code CharSequence+} is not the name of a type. It is the name {@code CharSequence} plus the
     * matching rule "and any subtype of it", and the rule is not part of the name. Left on, the
     * name missed every lookup — the file's own imports, the {@code java.lang} probe, and finally
     * the {@code android.jar} index, where the miss was published as
     * {@code Unknown{UnresolvedSignature, mode: CLASSE-AUSENTE}}: this expander's defect wearing
     * the costume of an absence in the Android platform, which is the one shape of error M0 exists
     * to keep out. {@link #namedTypes(PointCut)} had the strip and this route did not, so the two
     * routes disagreed about the same written name; now there is one rule, in one place.
     */
    public String resolve(String name) {
        if (name == null || name.isEmpty()) {
            return "*";
        }
        String base = name;
        if (base.endsWith("+")) {
            base = base.substring(0, base.length() - 1);
        }
        StringBuilder suffix = new StringBuilder();
        while (base.endsWith("[]")) {
            base = base.substring(0, base.length() - 2);
            suffix.append("[]");
        }
        if (base.isEmpty()) {
            return "*";
        }
        String resolved = simpleNameToFqn.get(base);
        if (resolved == null) {
            resolved = base.indexOf('.') < 0 && isJavaLang(base) ? "java.lang." + base : base;
        }
        return resolved + suffix;
    }

    /**
     * Whether {@code java.lang} declares a type of this simple name.
     *
     * <p>Asked of the running JDK rather than of a hand-written list, because a list of
     * {@code java.lang} type names is a thing that goes stale silently and a name it forgot is
     * exactly the bare-name defect this method exists to remove. The platform class loader is used
     * so the answer is about {@code java.base} and not about whatever the test classpath carries,
     * and the class is never initialised.
     */
    private static boolean isJavaLang(String simpleName) {
        return JAVA_LANG.computeIfAbsent(simpleName, name -> {
            try {
                Class.forName("java.lang." + name, false, ClassLoader.getPlatformClassLoader());
                return Boolean.TRUE;
            } catch (ClassNotFoundException | LinkageError e) {
                return Boolean.FALSE;
            }
        });
    }
}
