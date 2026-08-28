package presto.android.gui.clients.target;

import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Set;

import soot.FastHierarchy;
import soot.RefType;
import soot.Scene;
import soot.SootClass;
import soot.Type;

/**
 * The single place where a call site is tested against a declared target.
 *
 * <p>Two axes decide a match, and their order is not cosmetic:
 * <ol>
 *   <li><b>Name first.</b> {@link #nameMatches} is a string comparison; the hierarchy query
 *       behind it is not. Widening the owner predicate removes the {@code equals(fqn)}
 *       fast-reject that {@code TargetResolver.resolveInScene} used to rely on — it iterates
 *       {@code Scene.getClasses()} × methods × targets — so the name short-circuit is what
 *       replaces it (NFR04 cost bound).</li>
 *   <li><b>Then the owner.</b> Exact FQN equality when {@code includeSubtypes} is off (the JCA
 *       path, byte-for-byte unchanged); {@link FastHierarchy#canStoreType} against the declared
 *       super-type when it is on. {@code canStoreType} is asked at the call site rather than
 *       pre-expanding the super-type to its implementers, because
 *       {@code getImplementersOf(Iterable)} omits sub-interfaces — an interface-typed call site
 *       like {@code java.util.List.iterator()} against {@code Iterable+.iterator} would be
 *       missed (decision A2 over the rejected A1).</li>
 * </ol>
 *
 * <p><b>The phantom flag is not the question; hierarchy content is.</b> GATOR runs Soot with
 * {@code allow_phantom_refs=true}, and an unresolvable type becomes a phantom {@link SootClass}
 * that satisfies {@code Scene.containsClass} and passes {@code checkLevel(HIERARCHY)} — so
 * {@code canStoreType} returns a <i>definite, wrong</i> {@code false} rather than throwing, and a
 * try/catch would be dead code. But {@code isPhantom()} alone is the wrong guard, because in the
 * GATOR Scene it is not a proxy for "unresolvable": under {@code -force-android-jar} the
 * {@code java.*}/{@code javax.*} owners of both spec sets are read out of the platform
 * {@code android.jar} with a complete and correct hierarchy — real superclass, real interface
 * list, real {@code ACC_INTERFACE} modifier — and are flagged phantom all the same. Measured on
 * {@code cryptoapp.apk} (API 33): 522 of the 575 JDK classes in the Scene are phantom, and
 * {@code canStoreType} answers correctly over every one of them, interface-to-interface included
 * ({@code java.util.List <: java.lang.Iterable}), which is the case decision A2 exists for.
 * Guarding on the flag alone therefore degraded <i>every</i> declared owner of both spec sets.
 *
 * <p>What actually breaks {@code canStoreType} is a class Soot <i>invented</i> because it found no
 * source at all. Such a class carries nothing: no superclass, no interfaces, no methods, and
 * {@code getModifiers() == 0}. That is the guard — see {@link #carriesHierarchy}. An owner failing
 * it degrades to exact {@code equals} with a warning logged once, a reported false-negative
 * instead of a silent one (INV-ANA-43).
 *
 * <p>Instances are per-run and hold the resolved super-type of each declared owner, so a
 * {@code RefType} is looked up once per target rather than once per invoke.
 */
public final class TargetMatching {

	/** Declared owner FQN → its resolved super-type, or absent when the owner degraded. */
	private final Map<String, RefType> resolvedOwners = new HashMap<>();
	/** Owners already reported as degraded; keeps the warning to one line per owner. */
	private final Set<String> degradedOwners = new LinkedHashSet<>();

	/**
	 * Force-resolve every declared owner of {@code targets} into the Scene and remember the
	 * ones that came back usable.
	 *
	 * <p>Resolution is requested at {@code SIGNATURES}, not at {@code HIERARCHY}, even though
	 * {@code canStoreType} only needs the latter. Resolving <i>at</i> HIERARCHY can introduce a
	 * class into the Scene below SIGNATURES, and {@code TargetResolver.resolveInScene} then
	 * iterates {@code Scene.v().getClasses()} calling {@code cls.getMethods()}, which opens with
	 * {@code checkLevel(SIGNATURES)} — with {@code Scene.doneResolving()} true during the wjtp
	 * pack and {@code ignore_resolving_levels} never set in this build, that throws. The
	 * realistic trigger is an owner absent from the APK's Scene, e.g. {@code java.net.ServerSocket}
	 * in an app that opens no sockets. SIGNATURES satisfies HIERARCHY and costs nothing here.
	 *
	 * <p>Ordering: the {@code FastHierarchy} used to answer {@code canStoreType} MUST be obtained
	 * <i>after</i> this call and never cached across it. {@code Scene.addClass} invalidates the
	 * cached hierarchy via {@code modifyHierarchy()}, which covers a newly introduced owner; an
	 * owner already present as a phantom is the one case it does not, so the hierarchy is
	 * released explicitly when that happens.
	 *
	 * @return the owners that resolved to a usable, non-phantom type.
	 */
	public Set<RefType> forceResolveTargets(Set<TargetMethod> targets) {
		Set<RefType> loaded = new HashSet<>();
		boolean releasedStalePhantom = false;
		for (TargetMethod t : targets) {
			String fqn = t.getClassName();
			if (resolvedOwners.containsKey(fqn) || degradedOwners.contains(fqn)) {
				continue;
			}
			SootClass existing = Scene.v().containsClass(fqn) ? Scene.v().getSootClass(fqn) : null;
			boolean wasPhantom = existing != null && existing.isPhantom();

			SootClass cls;
			try {
				cls = Scene.v().forceResolve(fqn, SootClass.SIGNATURES);
			} catch (RuntimeException e) {
				degrade(fqn, "force-resolve failed: " + e.getMessage());
				continue;
			}
			if (cls == null || cls.resolvingLevel() < SootClass.HIERARCHY || !carriesHierarchy(cls)) {
				degrade(fqn, cls == null ? "absent from the Scene"
						: (cls.resolvingLevel() < SootClass.HIERARCHY ? "resolved below HIERARCHY level"
								: "resolved to an empty phantom (no source on the Soot classpath)"));
				continue;
			}
			if (wasPhantom && !cls.isPhantom() && !releasedStalePhantom) {
				// An owner already present as a phantom was upgraded in place, so addClass never
				// ran and the cached FastHierarchy still describes the phantom. Drop it. (An
				// owner that is merely still flagged phantom was not modified and needs no
				// invalidation — that is the common case, see the class javadoc.)
				Scene.v().releaseFastHierarchy();
				releasedStalePhantom = true;
			}
			RefType type = cls.getType();
			resolvedOwners.put(fqn, type);
			loaded.add(type);
		}
		System.out.println("[TargetMatching] Target owners force-resolved: " + resolvedOwners.size()
				+ " usable, " + degradedOwners.size() + " degraded to exact matching"
				+ (degradedOwners.isEmpty() ? "" : " " + degradedOwners));
		return loaded;
	}

	/**
	 * Can {@code cls} answer a subtype question, or is it a class Soot invented?
	 *
	 * <p>Soot mints a phantom {@link SootClass} when {@code SourceLocator} finds no source for a
	 * name. Measured, such a class carries {@code getModifiers() == 0}, no superclass, no
	 * interfaces and no methods — nothing {@code FastHierarchy} can traverse, so
	 * {@code canStoreType} against it is a definite, wrong {@code false}. A class Soot actually
	 * read carries at least a superclass (every class but {@code java.lang.Object} has one,
	 * interfaces included) or interfaces or methods, whether or not it is <i>also</i> flagged
	 * phantom — which under {@code -force-android-jar} the whole JDK is.
	 *
	 * <p>The three clauses are a disjunction on purpose: any one of them is evidence a definition
	 * was read, and requiring all three would reject a marker interface such as
	 * {@code java.io.Serializable}.
	 */
	static boolean carriesHierarchy(SootClass cls) {
		return cls.hasSuperclass() || cls.getInterfaceCount() > 0 || cls.getMethodCount() > 0;
	}

	private void degrade(String fqn, String why) {
		if (degradedOwners.add(fqn)) {
			System.out.println("[TargetMatching] WARN owner '" + fqn + "' " + why
					+ "; degrading it to exact equals matching (subtype call sites of this owner"
					+ " will not be marked)");
		}
	}

	/** Owners that could not be resolved and therefore match by exact FQN only. */
	public Set<String> degradedOwners() {
		return degradedOwners;
	}

	/**
	 * Does a call site {@code (callSiteType, callSiteName)} hit the target {@code t}?
	 *
	 * <p>Takes the raw type and name rather than a {@code SootMethodRef} so both match points
	 * call it without allocating: {@code resolveInScene} passes
	 * {@code method.getDeclaringClass().getType()} + {@code method.getName()}, the bytecode scan
	 * passes {@code ref.getDeclaringClass().getType()} + {@code ref.getName()}. STRICT parameter
	 * matching stays in {@code resolveInScene} — this helper is lenient by design.
	 *
	 * @param fh the hierarchy obtained <i>after</i> {@link #forceResolveTargets}; may be null
	 *           when no subtype target exists.
	 */
	public boolean matches(Type callSiteType, String callSiteName, TargetMethod t, FastHierarchy fh) {
		if (!nameMatches(t, callSiteName)) {
			return false;
		}
		if (!t.isIncludeSubtypes()) {
			return callSiteType.toString().equals(t.getClassName());
		}
		RefType superType = resolvedOwners.get(t.getClassName());
		if (superType == null || fh == null) {
			// Degraded owner (or no hierarchy available): exact matching, never a silent false.
			degrade(t.getClassName(), "was not resolved before matching");
			return callSiteType.toString().equals(t.getClassName());
		}
		return fh.canStoreType(callSiteType, superType);
	}

	/**
	 * Trailing-{@code *} prefix semantics. The bare {@code *} (from {@code call(* Iterator.*(..))})
	 * reduces to the empty prefix and therefore matches every method of the owner — that is the
	 * intended AspectJ reading, not a degenerate case to reject. A {@code *} anywhere but at the
	 * end falls through to literal equality; no general glob is needed by any spec in the tree.
	 */
	public static boolean nameMatches(TargetMethod t, String callSiteName) {
		String declared = t.getMethodName();
		if (t.isNameIsPattern() && declared.endsWith("*")) {
			return callSiteName.startsWith(declared.substring(0, declared.length() - 1));
		}
		return declared.equals(callSiteName);
	}
}
