package br.unb.cic.rv.mutator;

import com.android.tools.smali.dexlib2.builder.MutableMethodImplementation;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.DexFile;
import com.android.tools.smali.dexlib2.iface.Method;
import com.android.tools.smali.dexlib2.iface.MethodImplementation;
import com.android.tools.smali.dexlib2.immutable.ImmutableClassDef;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethod;
import com.android.tools.smali.dexlib2.rewriter.ClassDefRewriter;
import com.android.tools.smali.dexlib2.rewriter.DexRewriter;
import com.android.tools.smali.dexlib2.rewriter.MethodRewriter;
import com.android.tools.smali.dexlib2.rewriter.Rewriter;
import com.android.tools.smali.dexlib2.rewriter.RewriterModule;
import com.android.tools.smali.dexlib2.rewriter.Rewriters;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * Bridges {@link MutableMethodImplementation} mutations produced by
 * {@link DexWeaver} (and {@code coverage-weaver}'s {@code CoverageWeaver})
 * into a {@link DexFile} that {@code DexPool.writeTo} can serialize.
 *
 * <p>Why this class exists: dexlib2 separates the read-only DexFile model from
 * the mutable builder model. Weavers operate on {@link MutableMethodImplementation}
 * for individual methods; serializers traverse the immutable model. This class
 * holds the table of {@code (method) → mutable impl} mappings and produces a
 * fresh {@link DexFile} via {@link DexRewriter} where each mutated method is
 * substituted by an {@link ImmutableMethod} carrying the new implementation.
 *
 * <h2>Lifecycle</h2>
 * <pre>
 *   DexFile original = ...; // read via DexBackedDexFile.fromInputStream
 *   DexFileMutator m = new DexFileMutator(original);
 *   new DexWeaver().weave(original, descriptor, typeResolver, inheritance,
 *                          m::forMethod);
 *   // optional: coverage
 *   new CoverageWeaver().weave(original, m::forMethod);
 *   DexPool.writeTo(outputPath.toString(), m.toDexFile());
 * </pre>
 *
 * <p>The Method-reference adapter ({@code m::forMethod}) lets this class avoid a
 * compile-time dependency on either weaver's {@code MutableImplSupplier}
 * interface — useful because {@code coverage-weaver} already depends on
 * {@code dex-mutator}, and the reverse edge would close a Maven cycle.
 *
 * <h2>Identity vs. content keying</h2>
 * Dex-backed Method instances are not stable across iterations of
 * {@code DexFile.getClasses()} — a fresh wrapper may be created per
 * traversal. We key the mutation table by the method's full descriptor
 * ({@code Lcls;->name(Largs)Lret;}) so that {@link DexRewriter}'s subsequent
 * traversal finds the mutation regardless of which Method instance it sees.
 *
 * <h2>Two mutation paths</h2>
 * This class serialises two kinds of change:
 * <ul>
 *   <li><b>Method-body substitution</b> ({@link #mutations}): an existing
 *       method's implementation is replaced by a {@link MutableMethodImplementation}.
 *       Realised through the {@link MethodRewriter}.</li>
 *   <li><b>Class-level method addition</b> ({@link #synthesizedMethods}): a
 *       brand-new {@link Method} is appended to a class's method set. The
 *       canonical use is {@code staticinitialization(T+)} synthesis (§4.Y) —
 *       a class with no {@code <clinit>} needs one created so the static-init
 *       monitor event fires. Realised through a {@link ClassDefRewriter} that
 *       rebuilds the {@link ClassDef} with its rewritten existing methods PLUS
 *       any synthesized methods registered for that class descriptor. A pure
 *       {@link MethodRewriter} cannot add a method, so without this path a
 *       synthesized {@code <clinit>} would be dropped at serialization.</li>
 * </ul>
 */
public final class DexFileMutator {

    private final DexFile original;
    private final Map<String, MutableMethodImplementation> mutations = new HashMap<>();
    /**
     * Defining-class descriptor ({@code Lcls;}) → methods synthesized for that
     * class and not present in the original {@link ClassDef}. Each entry is an
     * {@link ImmutableMethod} carrying its own {@link MethodImplementation}
     * (a {@link MutableMethodImplementation} at registration time, copied
     * defensively by {@link ImmutableMethod}). Appended to the class's method
     * set by the {@link ClassDefRewriter} in {@link #toDexFile()}.
     */
    private final Map<String, List<Method>> synthesizedMethods = new HashMap<>();

    public DexFileMutator(DexFile original) {
        this.original = Objects.requireNonNull(original, "original");
    }

    /**
     * Register a brand-new {@code method} to be appended to the method set of
     * the class identified by {@code definingClassDescriptor} ({@code Lcls;})
     * during {@link #toDexFile()}. Used for {@code <clinit>} synthesis (§4.Y):
     * a class with no class initializer is never visited by the per-method
     * weave loop, so the synthesized {@code <clinit>} cannot go through
     * {@link #forMethod(Method)} (which returns {@code null} for a method with
     * no original implementation anyway) — it is added at the class level here.
     *
     * <p>The {@code method}'s {@code getDefiningClass()} MUST equal
     * {@code definingClassDescriptor}; the descriptor is taken as the map key
     * so the {@link ClassDefRewriter} can match it against
     * {@link ClassDef#getType()} without re-deriving it.
     */
    public void addSynthesizedMethod(String definingClassDescriptor, Method method) {
        Objects.requireNonNull(definingClassDescriptor, "definingClassDescriptor");
        Objects.requireNonNull(method, "method");
        synthesizedMethods
                .computeIfAbsent(definingClassDescriptor, k -> new ArrayList<>())
                .add(method);
    }

    /**
     * Get-or-create the mutable view of {@code method}'s implementation. The
     * returned {@link MutableMethodImplementation} is shared across callers
     * for the same method, so successive weaver passes (e.g., advice weaver
     * then coverage weaver) compose into a single mutation.
     *
     * @return a mutable view, or {@code null} for abstract / native methods
     *         (no implementation to mutate).
     */
    public MutableMethodImplementation forMethod(Method method) {
        if (method.getImplementation() == null) return null;
        String k = key(method);
        MutableMethodImplementation existing = mutations.get(k);
        if (existing != null) return existing;
        MutableMethodImplementation mut =
                new MutableMethodImplementation(method.getImplementation());
        mutations.put(k, mut);
        return mut;
    }

    /**
     * Replace the cached {@link MutableMethodImplementation} for {@code method}
     * with {@code newImpl}. After this call, every subsequent
     * {@link #forMethod(Method)} lookup for the same descriptor key returns
     * {@code newImpl} (object identity), and {@link #toDexFile()} serialises
     * {@code newImpl} rather than the pre-replacement MMI.
     *
     * <p>Required by callers of {@code RegisterShifter.bumpRegisterCount} /
     * {@code spillLowRegisters}: those operations allocate a fresh MMI to
     * grow the register frame (the {@code registerCount} field of the source
     * MMI cannot be mutated through dexlib2's public API). Without this
     * notification the cache would still point at the pre-spill MMI and the
     * dex writer would drop both the frame growth and any instructions
     * injected onto the new MMI — surfacing as install-time {@code VerifyError}
     * on the device (gh59 5-APK residual). See design.md D5.
     *
     * <p>Idempotent — calling {@code replaceImpl} twice with the same arguments
     * is a no-op after the first call.
     */
    public void replaceImpl(Method method, MutableMethodImplementation newImpl) {
        if (method == null || newImpl == null) return;
        mutations.put(key(method), newImpl);
    }

    public boolean hasAnyMutations() {
        return !mutations.isEmpty() || !synthesizedMethods.isEmpty();
    }

    public int mutationCount() {
        return mutations.size();
    }

    /**
     * Produce a {@link DexFile} that, when serialized, embeds every tracked
     * mutation — both method-body substitutions and class-level method
     * additions. Returns the original file unchanged when nothing is pending.
     *
     * <p>The {@link MethodRewriter} handles body substitution; the
     * {@link ClassDefRewriter} appends synthesized methods. The two cooperate:
     * the class rewriter delegates each existing method through the rewriter
     * chain (so substitutions still apply), then adds the synthesized methods
     * for that class descriptor after the rewritten existing set.
     */
    public DexFile toDexFile() {
        if (mutations.isEmpty() && synthesizedMethods.isEmpty()) return original;
        DexRewriter rewriter = new DexRewriter(new RewriterModule() {
            @Override
            public Rewriter<Method> getMethodRewriter(Rewriters rewriters) {
                return new MethodRewriter(rewriters) {
                    @Override
                    public Method rewrite(Method method) {
                        MutableMethodImplementation mut = mutations.get(key(method));
                        if (mut == null) return super.rewrite(method);
                        // Substitute the implementation; keep all other fields
                        // verbatim from the original. ImmutableMethod copies
                        // collections defensively, so the rest of the rewriter
                        // chain still sees correctly-rewritten parameters /
                        // annotations downstream.
                        return new ImmutableMethod(
                                method.getDefiningClass(),
                                method.getName(),
                                method.getParameters(),
                                method.getReturnType(),
                                method.getAccessFlags(),
                                method.getAnnotations(),
                                method.getHiddenApiRestrictions(),
                                mut);
                    }
                };
            }

            @Override
            public Rewriter<ClassDef> getClassDefRewriter(Rewriters rewriters) {
                return new ClassDefRewriter(rewriters) {
                    @Override
                    public ClassDef rewrite(ClassDef classDef) {
                        List<Method> extra = synthesizedMethods.get(classDef.getType());
                        // No synthesized methods for this class — defer to the
                        // default rewrite (which still applies method-body
                        // substitutions via the MethodRewriter above).
                        if (extra == null || extra.isEmpty()) return super.rewrite(classDef);

                        // Rebuild the method set = rewritten existing methods
                        // (so body substitutions are preserved) + the
                        // synthesized methods for this class. The synthesized
                        // methods are already self-consistent ImmutableMethods,
                        // but route them through the method rewriter too so any
                        // type references inside them are remapped consistently
                        // with the rest of the dex.
                        Rewriter<Method> methodRw = rewriters.getMethodRewriter();
                        List<Method> methods = new ArrayList<>();
                        for (Method m : classDef.getMethods()) methods.add(methodRw.rewrite(m));
                        for (Method m : extra) methods.add(methodRw.rewrite(m));

                        return new ImmutableClassDef(
                                classDef.getType(),
                                classDef.getAccessFlags(),
                                classDef.getSuperclass(),
                                classDef.getInterfaces(),
                                classDef.getSourceFile(),
                                classDef.getAnnotations(),
                                classDef.getFields(),
                                methods);
                    }
                };
            }
        });
        return rewriter.getDexFileRewriter().rewrite(original);
    }

    private static String key(Method m) {
        StringBuilder sb = new StringBuilder(64);
        sb.append(m.getDefiningClass()).append("->")
          .append(m.getName()).append('(');
        for (CharSequence p : m.getParameterTypes()) sb.append(p);
        sb.append(')').append(m.getReturnType());
        return sb.toString();
    }

    /** Convenience supplier for serializer paths that prefer raw access. */
    public Map<String, MutableMethodImplementation> mutationsView() {
        return java.util.Collections.unmodifiableMap(mutations);
    }
}
