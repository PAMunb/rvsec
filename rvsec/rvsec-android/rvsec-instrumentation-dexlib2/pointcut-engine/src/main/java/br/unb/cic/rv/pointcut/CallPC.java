package br.unb.cic.rv.pointcut;

import java.util.List;

/**
 * {@code call(<modifiers>? <returnType> <declaringType>.<methodName>(<paramTypes>))}
 * or {@code call(<modifiers>? <declaringType>.new(<paramTypes>))}.
 *
 * <p>When {@code isConstructor} is true, {@code methodName} is {@code "<init>"} and
 * {@code returnType} is empty.
 *
 * <p>{@code paramTypes} contains AspectJ simple names (e.g. {@code "Cipher"},
 * {@code "byte[]"}, {@code "int"}); {@code varargs} is true when the original source
 * used {@code ..} to match any argument list — in that case {@code paramTypes} is
 * empty.
 */
public record CallPC(
        boolean isConstructor,
        String returnType,
        String declaringType,
        String methodName,
        List<String> paramTypes,
        boolean varargs
) implements PointcutExpression {
    public CallPC {
        paramTypes = List.copyOf(paramTypes);
    }
}
