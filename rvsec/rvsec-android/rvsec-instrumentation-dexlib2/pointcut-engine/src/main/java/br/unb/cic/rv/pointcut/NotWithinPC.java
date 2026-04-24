package br.unb.cic.rv.pointcut;

/**
 * {@code !within(<typePattern>)} — excludes join points inside classes matching
 * the pattern.
 *
 * <p>Common shapes from JavaMOP base-aspect exclusions:
 * {@code !within(sun..*)}, {@code !within(mop..*)},
 * {@code !within(com.runtimeverification.rvmonitor.java.rt.RVMObject+)}.
 */
public record NotWithinPC(String typePattern) implements PointcutExpression {
}
