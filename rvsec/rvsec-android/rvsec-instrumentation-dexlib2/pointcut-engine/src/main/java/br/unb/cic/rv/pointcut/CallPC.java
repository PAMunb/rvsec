package br.unb.cic.rv.pointcut;

import java.util.List;

/**
 * {@code call(<modifiers>? <returnType> <declaringType>.<methodName>(<paramSpecs>))}
 * or {@code call(<modifiers>? <declaringType>.new(<paramSpecs>))}.
 *
 * <p>When {@code isConstructor} is true, {@code methodName} is {@code "<init>"} and
 * {@code returnType} is empty.
 *
 * <p>{@code paramSpecs} carries the fixed positional head of the parameter
 * list. Each {@link ParamSpec} holds the descriptor (AspectJ simple name —
 * {@code "Cipher"}, {@code "byte[]"}, {@code "int"}) and a {@code isSubtype}
 * flag set to {@code true} when the source spelled the param as {@code T+}
 * (AspectJ subtype operator, matched via {@link InheritanceResolver} at match
 * time). The trailing {@code +} is consumed at parse time and is not part of
 * {@link ParamSpec#descriptor()}.
 *
 * <p>{@code varargs} is true when the source ended the parameter list with a
 * trailing {@code ..} (e.g. {@code (..)} or {@code (String, ..)}): the head in
 * {@code paramSpecs} must match positionally and the tail accepts any number
 * of remaining arguments. For standalone {@code (..)} the head is empty
 * (match-anything); for {@code (String, ..)} the head is {@code [String]}.
 * When {@code varargs} is false the parameter list is exact: {@code ()} has an
 * empty head and {@code (String, int)} has a two-element head.
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

    /**
     * Result of splitting a {@code call()} parameter list: the fixed positional
     * {@code head} plus a {@code trailingVarargs} flag set when the list ended
     * with {@code ..}. Standalone {@code (..)} yields {@code (head=[],
     * trailingVarargs=true)}; {@code (String, ..)} yields
     * {@code (head=[String], trailingVarargs=true)}; {@code ()} yields
     * {@code (head=[], trailingVarargs=false)}; {@code (String, int)} yields
     * {@code (head=[String, int], trailingVarargs=false)}.
     */
    public record ParamList(List<ParamSpec> head, boolean trailingVarargs) {
        public ParamList {
            head = List.copyOf(head);
        }
    }
}
