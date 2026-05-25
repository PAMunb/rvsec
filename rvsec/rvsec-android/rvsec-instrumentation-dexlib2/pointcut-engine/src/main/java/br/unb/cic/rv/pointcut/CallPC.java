package br.unb.cic.rv.pointcut;

import java.util.List;

/**
 * {@code call(<modifiers>? <returnType> <declaringType>.<methodName>(<paramSpecs>))}
 * or {@code call(<modifiers>? <declaringType>.new(<paramSpecs>))}.
 *
 * <p>When {@code isConstructor} is true, {@code methodName} is {@code "<init>"} and
 * {@code returnType} is empty.
 *
 * <p>{@code paramSpecs} carries the parsed parameter list. Each
 * {@link ParamSpec} holds the descriptor (AspectJ simple name —
 * {@code "Cipher"}, {@code "byte[]"}, {@code "int"}, {@code ".."}) and a
 * {@code isSubtype} flag set to {@code true} when the source spelled the
 * param as {@code T+} (AspectJ subtype operator, matched via
 * {@link InheritanceResolver} at match time). The trailing {@code +} is
 * consumed at parse time and is not part of {@link ParamSpec#descriptor()}.
 * {@code varargs} is true when the source used {@code ..} to match any
 * argument list — in that case {@code paramSpecs} is empty.
 */
public record CallPC(
        boolean isConstructor,
        String returnType,
        String declaringType,
        String methodName,
        List<ParamSpec> paramSpecs,
        boolean varargs
) implements PointcutExpression {
    public CallPC {
        paramSpecs = List.copyOf(paramSpecs);
    }

    /**
     * Per-parameter spec for a {@code call()} pointcut.
     *
     * <p>{@code descriptor} — the parameter type as written by the user
     * (e.g. {@code "Object"}, {@code "java.security.Provider"},
     * {@code "String[]"}, {@code ".."}). The trailing {@code "+"} subtype
     * marker, if present in the source, is stripped here.
     *
     * <p>{@code isSubtype} — {@code true} iff the user wrote {@code T+}: match
     * any subtype of {@code T} per {@link InheritanceResolver}. {@code false}
     * for exact descriptor equality.
     */
    public record ParamSpec(String descriptor, boolean isSubtype) { }
}
