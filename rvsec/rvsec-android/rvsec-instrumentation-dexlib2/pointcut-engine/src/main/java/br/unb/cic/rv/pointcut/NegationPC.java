package br.unb.cic.rv.pointcut;

/**
 * Generic negation pointcut: {@code !<inner>} (§4.N).
 *
 * <p>Wraps the type forms {@code !target(Type)} and {@code !args(Type)}, where
 * {@code inner} is a {@link TargetPC} / {@link ArgsPC} carrying its resolved type.
 * The matcher inverts the inner verdict; a negation carries no bindings.
 *
 * <p>{@code !within(...)} keeps its dedicated {@link NotWithinPC} node because the
 * weaver evaluates exclusion scopes directly during class-type filtering.
 */
public record NegationPC(PointcutExpression inner) implements PointcutExpression {
}
