package br.unb.cic.mop.extractor.visitor;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

import br.unb.cic.mop.extractor.model.MopMethod;
import javamop.parser.ast.ImportDeclaration;
import javamop.parser.ast.MOPSpecFile;
import javamop.parser.ast.aspectj.CombinedPointCut;
import javamop.parser.ast.aspectj.MethodPattern;
import javamop.parser.ast.aspectj.MethodPointCut;
import javamop.parser.ast.aspectj.PointCut;
import javamop.parser.ast.aspectj.TypePattern;
import javamop.parser.ast.mopspec.EventDefinition;
import javamop.parser.ast.mopspec.JavaMOPSpec;

/**
 * Extracts the (owner, method) targets declared by the {@code call(...)} pointcuts of a
 * JavaMOP spec.
 *
 * <p>The AspectJ pointcut grammar admits four constructions beyond the explicit-import,
 * exact-name style the JCA specs use, and all four are handled here:
 * <ul>
 *   <li>an asterisk import ({@code import java.util.*;}) as the owner's only declaration —
 *       the package is registered and owners are resolved against it by {@code Class.forName};</li>
 *   <li>the {@code +} subtype operator on the owner ({@code Collection+}) — stripped, with
 *       {@code includeSubtypes} recording that the match is by hierarchy, not by exact FQN;</li>
 *   <li>a trailing {@code *} in the method name ({@code add*}, or the bare {@code *}) —
 *       preserved verbatim as a pattern, with {@code nameIsPattern} set;</li>
 *   <li>the constructor form {@code Owner.new(..)} — the grammar routes it here with the
 *       literal member name {@code new}, which no Soot method carries; it is emitted as
 *       {@code <init>}, the name Soot gives every constructor.</li>
 * </ul>
 *
 * <p>Owner resolution has three steps, in order: explicit imports, then the registered wildcard
 * packages, then the {@code java.lang} package Java leaves implicit. The third step is bounded
 * rather than free: a target whose owner resolves only through it is flagged
 * {@link MopMethod#isOwnerFromImplicitSeed}, and the gator side emits such a target with
 * {@code MatchPolicy.STRICT}. The bound is the reason the step is admissible at all — resolving
 * {@code String} under lenient matching would make {@code String#valueOf} match every overload
 * (measured: 74 call sites over 3 corpus APKs, 17 of them woven), which is worse than leaving it
 * unresolved. An owner that resolves through none of the three is logged and skipped, never
 * dropped in silence.
 */
public class UsedJcaMethodsVisitor extends VoidVisitorAdapter<Object> {
	/** Member name the grammar emits for {@code Owner.new(..)}; Soot names constructors {@code <init>}. */
	private static final String CONSTRUCTOR_POINTCUT_NAME = "new";
	private static final String SOOT_CONSTRUCTOR_NAME = "<init>";
	private static final String SUBTYPE_OPERATOR = "+";
	/** The package Java leaves implicit in every compilation unit; the third resolution step. */
	private static final String IMPLICIT_PACKAGE = "java.lang";
	private static final String NAME_WILDCARD = "*";
	/** Marker the grammar emits for an unconstrained parameter list; it names no type. */
	private static final String VARARGS_MARKER = "..";
	private static final Set<String> PRIMITIVE_TYPES = Set.of(
			"boolean", "byte", "char", "short", "int", "long", "float", "double", "void");

	private Set<String> classes = new HashSet<>();
	private Set<MopMethod> methods = new HashSet<>();

	private Map<String, String> imports = new HashMap<>();
	// Declaration-ordered: two wildcard packages could both offer a class of the same simple
	// name, and the first import wins deterministically rather than by hash order.
	private Set<String> wildcardPackages = new LinkedHashSet<>();
	private Set<String> skippedOwners = new LinkedHashSet<>();

	@Override
	public void visit(MOPSpecFile f, Object arg) {
		if (f.getSpecs() != null) {
			f.getImports().forEach(i -> i.accept(this, arg));
			f.getSpecs().forEach(i -> i.accept(this, arg));
		}
	}

	@Override
	public void visit(ImportDeclaration n, Object arg) {
		String name = n.getName().toString();
		if (n.isAsterisk()) {
			wildcardPackages.add(name);
			return;
		}
		String key = name.substring(name.lastIndexOf('.') + 1);
		imports.put(key, name);
	}

	@Override
	public void visit(JavaMOPSpec s, Object arg) {		
		if (!Objects.isNull(s.getEvents())) {
			for (EventDefinition e : s.getEvents()) {
				e.accept(this, arg);
			}
		}
	}

	@Override
	public void visit(EventDefinition e, Object arg) {
		if (!Objects.isNull(e.getPointCut())) {
			e.getPointCut().accept(this, arg);
		}
	}

	@Override
	public void visit(CombinedPointCut p, Object arg) {
		for (PointCut subP : p.getPointcuts()) {
			subP.accept(this, arg);
		}
	}

	@Override
	public void visit(MethodPointCut p, Object arg) {
		MethodPattern signature = p.getSignature();
		if (signature == null || signature.getOwner() == null) {
			return;
		}

		String declaredOwner = signature.getOwner().toString();
		boolean includeSubtypes = declaredOwner.endsWith(SUBTYPE_OPERATOR);
		String simpleOwner = includeSubtypes
				? declaredOwner.substring(0, declaredOwner.length() - SUBTYPE_OPERATOR.length())
				: declaredOwner;

		String fqn = resolveOwner(simpleOwner);
		// Third and last step. Kept separate from resolveOwner so the route is *recorded*, not
		// merely taken: MatchPolicy.STRICT is attached downstream to targets that reached the
		// owner this way and to no others, so a target that already resolved cannot change
		// policy underneath the frozen ruler.
		boolean ownerFromImplicitSeed = false;
		if (fqn == null) {
			fqn = resolveInImplicitPackage(simpleOwner);
			ownerFromImplicitSeed = fqn != null;
		}
		if (fqn == null) {
			// The silence is the defect being repaired here: an unimported owner used to fall
			// through with no else-branch, so a spec could contribute zero targets forever
			// without anything saying so.
			if (skippedOwners.add(simpleOwner)) {
				System.out.println("[UsedJcaMethodsVisitor] WARN skipped owner '" + simpleOwner
						+ "': resolvable through neither the explicit imports " + imports.keySet()
						+ ", the wildcard packages " + wildcardPackages
						+ ", nor the implicit " + IMPLICIT_PACKAGE + " package");
			}
			return;
		}
		classes.add(fqn);

		String memberName = signature.getMemberName();
		boolean nameIsPattern = memberName.endsWith(NAME_WILDCARD);
		if (CONSTRUCTOR_POINTCUT_NAME.equals(memberName)) {
			// Unambiguous: 'new' is a Java keyword, so no method may be named it.
			memberName = SOOT_CONSTRUCTOR_NAME;
			nameIsPattern = false;
		}

		MopMethod method = new MopMethod(fqn, memberName, getParams(signature), signature.toString(), includeSubtypes,
				nameIsPattern, ownerFromImplicitSeed);
		methods.add(method);
	}

	/**
	 * Resolve a simple owner name to an FQN through the two <em>import-driven</em> routes:
	 * explicit imports first, then the wildcard-import packages via {@code Class.forName}.
	 * Returns {@code null} when neither answers — the caller then tries the implicit package.
	 */
	private String resolveOwner(String simpleOwner) {
		String explicit = imports.get(simpleOwner);
		if (explicit != null) {
			return explicit;
		}
		for (String pkg : wildcardPackages) {
			String candidate = pkg + "." + simpleOwner;
			try {
				Class.forName(candidate);
				return candidate;
			} catch (ClassNotFoundException | LinkageError e) {
				// Not this package's class — keep looking.
			}
		}
		return null;
	}

	/**
	 * The implicit-package step, kept apart from {@link #resolveOwner} because its result carries
	 * a consequence the other two routes do not: a target that reaches its owner here is emitted
	 * STRICT.
	 */
	private String resolveInImplicitPackage(String simpleName) {
		String candidate = IMPLICIT_PACKAGE + "." + simpleName;
		try {
			Class.forName(candidate);
			return candidate;
		} catch (ClassNotFoundException | LinkageError e) {
			return null;
		}
	}

	private List<String> getParams(MethodPattern method) {
		List<String> params = new ArrayList<>();
		for (TypePattern type : method.getParameters()) {
			params.add(resolveParameterType(type.toString()));
		}
		return params;
	}

	/**
	 * Resolve a declared parameter type to its FQN, through the same import-driven routes the
	 * owner uses.
	 *
	 * <p>This exists because a STRICT target is compared against the signature Soot reports at
	 * the call site ({@code TargetResolver.paramsMatch}), which reads {@code java.lang.Object}
	 * where the pointcut wrote {@code Object}. A target whose parameters keep the simple names
	 * the pointcut spelled can therefore never match, which makes the STRICT policy
	 * inexpressible rather than merely imprecise.
	 *
	 * <p>Four shapes are returned untouched, each for a different reason:
	 * <ul>
	 *   <li>the varargs marker {@code ..}, which names no type at all;</li>
	 *   <li>a primitive, which has no package to qualify it with;</li>
	 *   <li>a name that already carries a dot, which is already written as an FQN;</li>
	 *   <li>a name carrying the {@code +} subtype operator. Parameter-position subtype matching
	 *       is out of scope, and stripping the operator here would do worse than nothing: it
	 *       would merge such an entry with its non-subtype twin, since the parameter list
	 *       participates in {@link MopMethod#equals}.</li>
	 * </ul>
	 *
	 * <p>An array suffix is carried across the resolution — {@code String[]} resolves through
	 * {@code String} — and an unresolvable name is returned as written rather than dropped, so
	 * this method never removes information the pointcut declared.
	 */
	private String resolveParameterType(String declared) {
		if (VARARGS_MARKER.equals(declared) || NAME_WILDCARD.equals(declared)
				|| declared.contains(".") || declared.contains(SUBTYPE_OPERATOR)) {
			return declared;
		}
		int arrayStart = declared.indexOf('[');
		String base = arrayStart < 0 ? declared : declared.substring(0, arrayStart);
		String suffix = arrayStart < 0 ? "" : declared.substring(arrayStart);
		if (PRIMITIVE_TYPES.contains(base)) {
			return declared;
		}
		String fqn = resolveOwner(base);
		if (fqn == null) {
			fqn = resolveInImplicitPackage(base);
		}
		return fqn == null ? declared : fqn + suffix;
	}

	public Set<String> getClasses() {
		return classes;
	}

	public Set<MopMethod> getMethods() {
		return methods;
	}

	/** Owners no import of the visited spec could resolve; see the log-and-skip rule above. */
	public Set<String> getSkippedOwners() {
		return skippedOwners;
	}

}
