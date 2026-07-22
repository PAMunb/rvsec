package br.unb.cic.rv.pointcut;

import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.DexFile;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Answers "is {@code A} a supertype of {@code B}" across both the Android API
 * ({@link AndroidClassIndex}) and the APK's own classes (dexlib2 {@link ClassDef}).
 *
 * <p>Required for {@code T+} semantics in AspectJ pointcuts: a pattern like
 * {@code staticinitialization(java.util.Iterator+)} matches not only
 * {@code java.util.Iterator} but also every subtype — subclasses the APK
 * declares, framework classes implementing the interface (e.g.
 * {@code java.util.ArrayList$Itr}), and anything else reachable via the
 * superclass / interface chain. The same applies to any base type the
 * specifications reference (JCA types like {@code javax.crypto.Cipher},
 * generic-spec types like {@code java.io.InputStream}, etc.).
 *
 * <p>Strategy: look up the class among APK classes first (dexlib2 index), then
 * delegate to AndroidClassIndex for framework-only chains.
 */
public final class InheritanceResolver {

    private final AndroidClassIndex android;
    /** Type descriptor (e.g. {@code "Lcom/example/Foo;"}) → APK {@code ClassDef}. */
    private final Map<String, ClassDef> apkByDescriptor;

    public InheritanceResolver(AndroidClassIndex android, DexFile... apkDexes) {
        this.android = android;
        this.apkByDescriptor = indexApk(apkDexes);
    }

    public InheritanceResolver(AndroidClassIndex android, Collection<? extends DexFile> apkDexes) {
        this.android = android;
        this.apkByDescriptor = indexApk(apkDexes.toArray(new DexFile[0]));
    }

    private static Map<String, ClassDef> indexApk(DexFile[] dexes) {
        if (dexes == null) return Collections.emptyMap();
        Map<String, ClassDef> out = new HashMap<>();
        for (DexFile dx : dexes) {
            if (dx == null) continue;
            for (ClassDef cd : dx.getClasses()) {
                out.put(cd.getType(), cd);
            }
        }
        return out;
    }

    /**
     * @return true when {@code subFqn} equals {@code superFqn} or descends from it
     *         through the APK class chain or the Android API chain.
     */
    public boolean isAssignableFrom(String superFqn, String subFqn) {
        if (superFqn == null || subFqn == null) return false;
        if (superFqn.equals(subFqn)) return true;
        if ("java.lang.Object".equals(superFqn)) return !isPrimitive(subFqn);

        String superDesc = toDescriptor(superFqn);
        String subDesc = toDescriptor(subFqn);
        Set<String> visited = new HashSet<>();
        return walkApkAncestors(subDesc, superDesc, visited)
                || android.isAssignableFrom(superFqn, subFqn);
    }

    /**
     * All concrete subtypes of {@code parentFqn} reachable via APK classes or
     * the Android API. Order is not guaranteed; duplicates are collapsed.
     */
    public List<String> subtypesOf(String parentFqn) {
        String parentDesc = toDescriptor(parentFqn);
        List<String> out = new ArrayList<>();
        Set<String> seen = new HashSet<>();
        for (ClassDef cd : apkByDescriptor.values()) {
            String child = fromDescriptor(cd.getType());
            if (!seen.add(child)) continue;
            if (isAssignableFrom(parentFqn, child)) {
                out.add(child);
            }
        }
        // Also include the parent itself when present in the APK (common case
        // for local subclasses of framework types).
        if (apkByDescriptor.containsKey(parentDesc) && seen.add(parentFqn)) {
            out.add(parentFqn);
        }
        return out;
    }

    /**
     * Walks the superclass/interface chain starting at {@code currentDesc}, staying
     * within APK-declared classes ({@link #apkByDescriptor}) for as long as possible
     * and falling back to {@link AndroidClassIndex} the moment the chain leaves the
     * APK — the two are separate graphs (dexlib2 {@link ClassDef} vs. the framework
     * class index) with no single lookup spanning both, so the walk must switch
     * resolution source mid-hierarchy rather than at the top.
     *
     * @param currentDesc type descriptor of the node being visited
     * @param targetDesc type descriptor being searched for (the candidate supertype)
     * @param visited descriptors already visited, to break cycles/re-visits
     * @return true if {@code targetDesc} is reachable from {@code currentDesc}
     */
    private boolean walkApkAncestors(String currentDesc, String targetDesc, Set<String> visited) {
        if (!visited.add(currentDesc)) return false;
        if (currentDesc.equals(targetDesc)) return true;

        ClassDef cd = apkByDescriptor.get(currentDesc);
        if (cd == null) {
            // currentDesc has no APK ClassDef, so this recursive branch cannot go
            // any further within the APK graph. It is not a failure: it means an
            // ancestor further up already crossed into android.jar (handled below,
            // at the level that still had a ClassDef to read super/interfaces from)
            // or targetDesc was never reachable at all.
            return false;
        }
        if (cd.getSuperclass() != null
                && walkApkAncestors(cd.getSuperclass(), targetDesc, visited)) {
            return true;
        }
        for (String iface : cd.getInterfaces()) {
            if (walkApkAncestors(iface, targetDesc, visited)) return true;
        }
        // Cross into android.jar from this APK leaf: cd's superclass/interfaces are
        // descriptors, not framework metadata, so once one of them is absent from
        // apkByDescriptor the only remaining chain lives in AndroidClassIndex. This
        // check happens here (not by recursing into walkApkAncestors again) because
        // that recursive call would hit the cd == null branch above and dead-end
        // without ever asking AndroidClassIndex.
        if (cd.getSuperclass() != null && !apkByDescriptor.containsKey(cd.getSuperclass())) {
            if (android.isAssignableFrom(fromDescriptor(targetDesc),
                    fromDescriptor(cd.getSuperclass()))) {
                return true;
            }
        }
        for (String iface : cd.getInterfaces()) {
            if (!apkByDescriptor.containsKey(iface)
                    && android.isAssignableFrom(fromDescriptor(targetDesc),
                            fromDescriptor(iface))) {
                return true;
            }
        }
        return false;
    }

    private static String toDescriptor(String fqn) {
        if (fqn.startsWith("L") && fqn.endsWith(";")) return fqn;
        return "L" + fqn.replace('.', '/') + ";";
    }

    private static String fromDescriptor(String desc) {
        if (desc.startsWith("L") && desc.endsWith(";")) {
            return desc.substring(1, desc.length() - 1).replace('/', '.');
        }
        return desc;
    }

    private static boolean isPrimitive(String fqn) {
        switch (fqn) {
            case "void": case "boolean": case "byte": case "short": case "char":
            case "int":  case "long":    case "float": case "double": return true;
            default: return false;
        }
    }
}
