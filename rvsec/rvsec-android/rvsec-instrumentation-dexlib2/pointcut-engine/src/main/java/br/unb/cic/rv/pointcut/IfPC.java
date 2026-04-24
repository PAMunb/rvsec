package br.unb.cic.rv.pointcut;

/**
 * {@code if(<javaExpr>)} — a runtime guard expression.
 *
 * <p>The parser keeps the Java expression opaque; the weaver emits an
 * {@code if-eqz} branch around the monitor invocation, delegating the
 * expression evaluation to a generated static helper method (task 4.3
 * {@code IfGuardEmitter}).
 */
public record IfPC(String javaExpression) implements PointcutExpression {
}
