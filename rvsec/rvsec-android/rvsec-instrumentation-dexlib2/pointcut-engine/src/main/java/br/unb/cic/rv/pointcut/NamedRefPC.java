package br.unb.cic.rv.pointcut;

/**
 * Reference to a named pointcut declared in another aspect — e.g.
 * {@code BaseAspect.notwithin()} emitted by rv-monitor templates, or
 * {@code adviceexecution()} from AspectJ's built-in vocabulary.
 *
 * <p>These nodes are opaque to the weaver: we emit the advice as if the named
 * reference were {@code true}. In practice the common cases are exclusions
 * that the {@code coverage-weaver} / pointcut matcher handle via package
 * filters, not via true pointcut semantics. The AST node exists so that parsing
 * never fails on unknown names; downstream components decide how to interpret.
 */
public record NamedRefPC(String name) implements PointcutExpression {
}
