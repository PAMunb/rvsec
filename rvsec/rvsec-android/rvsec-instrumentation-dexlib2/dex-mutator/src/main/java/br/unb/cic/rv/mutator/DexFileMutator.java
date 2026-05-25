package br.unb.cic.rv.mutator;

import com.android.tools.smali.dexlib2.builder.MutableMethodImplementation;
import com.android.tools.smali.dexlib2.iface.DexFile;
import com.android.tools.smali.dexlib2.iface.Method;
import com.android.tools.smali.dexlib2.iface.MethodImplementation;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethod;
import com.android.tools.smali.dexlib2.rewriter.DexRewriter;
import com.android.tools.smali.dexlib2.rewriter.MethodRewriter;
import com.android.tools.smali.dexlib2.rewriter.Rewriter;
import com.android.tools.smali.dexlib2.rewriter.RewriterModule;
import com.android.tools.smali.dexlib2.rewriter.Rewriters;

import java.util.HashMap;
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
 */
public final class DexFileMutator {

    private final DexFile original;
    private final Map<String, MutableMethodImplementation> mutations = new HashMap<>();

    public DexFileMutator(DexFile original) {
        this.original = Objects.requireNonNull(original, "original");
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
        return !mutations.isEmpty();
    }

    public int mutationCount() {
        return mutations.size();
    }

    /**
     * Produce a {@link DexFile} that, when serialized, embeds every tracked
     * mutation. Returns the original file unchanged when no mutations are
     * pending.
     */
    public DexFile toDexFile() {
        if (mutations.isEmpty()) return original;
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
