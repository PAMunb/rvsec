package br.unb.cic.rv.pointcut;

/**
 * Binary combination of two pointcut expressions with {@code &&} or {@code ||}.
 *
 * <p>AST nesting reflects operator precedence: {@code ||} binds looser than
 * {@code &&}, so {@code call(X) && target(t) || call(Y)} parses as
 * {@code (call(X) && target(t)) || call(Y)}.
 */
public record CombinedPC(Op op, PointcutExpression left, PointcutExpression right)
        implements PointcutExpression {

    public enum Op { AND, OR }
}
