package br.unb.cic.rv.pointcut;

/**
 * {@code execution(<sigPattern>)}.
 *
 * <p>JavaMOP's Coverage aspect uses {@code execution(* *.*(..))} — the catch-all.
 * We keep the pattern as an opaque string; matching happens downstream in the
 * {@code coverage-weaver} module which interprets it as "every method that's
 * neither excluded by package filter nor synthetic".
 */
public record ExecutionPC(String signaturePattern) implements PointcutExpression {
}
