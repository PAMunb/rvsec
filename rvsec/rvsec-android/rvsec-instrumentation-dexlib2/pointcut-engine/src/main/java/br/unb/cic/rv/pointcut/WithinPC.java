package br.unb.cic.rv.pointcut;

/**
 * {@code within(<typePattern>)} — restricts the match to join points lexically
 * within a class matching the pattern.
 *
 * <p>Rare in our fixtures (the common form is the negated {@link NotWithinPC}),
 * but the parser still models it as a first-class node for symmetry.
 */
public record WithinPC(String typePattern) implements PointcutExpression {
}
