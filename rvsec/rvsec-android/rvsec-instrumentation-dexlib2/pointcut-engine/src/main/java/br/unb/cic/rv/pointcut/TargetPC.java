package br.unb.cic.rv.pointcut;

/**
 * {@code target(name)} — binds the receiver of the matched call to the named
 * advice parameter.
 */
public record TargetPC(String name) implements PointcutExpression {
}
