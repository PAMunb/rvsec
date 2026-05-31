package br.unb.cic.rv.grammar.util;

import java.util.Set;

/**
 * The closed enumeration of matrix rows, as the single source of truth for
 * {@code MatrixIntegrityTest.testEveryDesignatorHasMatrixRow} (INV-INS-88).
 *
 * <p>Each string is the <em>rendered</em> (backtick-free, pipe-unescaped) form of the
 * "AspectJ syntax" column in {@code docs/aspectj_grammar_coverage.md} — i.e. exactly what
 * {@link MatrixMarkdownParser} produces when it concatenates a table cell's text/code-span
 * literals. The set MUST stay in 1:1 set-equality with the matrix's first column. 73 entries.
 *
 * <p>Mirrors the closed enumeration in {@code specs/instrumentation/spec.md} §"Closed
 * enumeration of matrix rows".
 */
public final class AspectJDesignators {

    private AspectJDesignators() { }

    public static final Set<String> DESIGNATORS = Set.of(
            // Classical pointcut designators (21)
            "call(MethodPattern)",
            "execution(MethodPattern)",
            "target(name) binding",
            "target(Type) type-matching",
            "this(name) binding",
            "this(Type) type-matching",
            "args(name) binding",
            "args(Type) type-matching",
            "args(*, name, ..) mixed",
            "withincode(MethodPattern)",
            "cflow(Pointcut)",
            "cflowbelow(Pointcut)",
            "if(BooleanExpression)",
            "handler(TypePattern)",
            "get(FieldPattern)",
            "set(FieldPattern)",
            "staticinitialization(TypePattern)",
            "initialization(ConstructorPattern)",
            "preinitialization(ConstructorPattern)",
            "adviceexecution()",
            "named-pointcut reference",
            // JavaMOP MOP-extensions (2)
            "condition(BooleanExpression)",
            "__STATICSIG macro",
            // Within-family per-stage delegation (4)
            "within(pkg..*) positive simple",
            "within(*..Log) suffix-wildcard",
            "within(T+) T+-inside-positive",
            "!within(TypePattern)",
            // AspectJ 5 annotation pointcut designators (6)
            "@annotation(AnnotationType)",
            "@target(AnnotationType)",
            "@this(AnnotationType)",
            "@args(AnnotationType)",
            "@within(AnnotationType)",
            "@withincode(AnnotationType)",
            // Advice forms (5)
            "before() advice",
            "after() advice",
            "after() returning(Id) advice",
            "after() throwing(Id) advice",
            "around() advice",
            // Type-pattern modifiers (11)
            "T+ in call() param",
            "T+ in call() owner",
            "T+ in call() return",
            "T+ inside !within(...)",
            "* wildcard",
            ".. standalone varargs",
            "(T, ..) trailing-mixed",
            "..* dot-glob",
            ".* single-level glob",
            "T[] / T[][] arrays",
            "Outer.Inner (inner-class qualifier)",
            // SignaturePattern modifiers (5)
            "positive visibility (public)",
            "negated visibility (!public)",
            "static signature modifier",
            "final signature modifier",
            "throws ExceptionPattern",
            // Composition operators (4)
            "&& composition",
            "|| composition",
            "! negation",
            "parentheses grouping",
            // Advice-body reflective API (7)
            "thisJoinPoint binding",
            "thisJoinPointStaticPart binding",
            "thisEnclosingJoinPointStaticPart binding",
            "JoinPoint.getArgs()",
            "JoinPoint.getSignature()",
            "JoinPoint.getTarget()",
            "JoinPoint.getKind()",
            // Around-advice mechanics (1)
            "proceed(...)",
            // Aspect declaration mechanics (6)
            "aspect Foo { ... }",
            "pointcut p(): ... declaration",
            "abstract aspect + concrete subaspect",
            "aspect inheritance",
            "declare precedence",
            "privileged aspect",
            // Runtime linkage (1)
            "org.aspectj.lang.JoinPoint family"
    );
}
