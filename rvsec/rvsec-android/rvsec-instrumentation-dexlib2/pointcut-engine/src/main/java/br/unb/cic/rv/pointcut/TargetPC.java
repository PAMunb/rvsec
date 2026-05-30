package br.unb.cic.rv.pointcut;

/**
 * {@code target(...)} — two forms distinguished at parse time:
 *
 * <ul>
 *   <li>{@code target(name)} (binding): {@code name} is a lowercase advice-parameter
 *       identifier (e.g. {@code target(o)}, {@code target(map)}). The receiver is bound
 *       to that parameter; no type filtering happens. {@code type} is {@code null}.</li>
 *   <li>{@code target(Type)} (type pattern): {@code type} is a capitalized/qualified type
 *       (optionally trailing {@code +}; e.g. {@code target(Cipher)}). The matcher constrains
 *       the call receiver's declared type to {@code type} or a subtype (§4.TT). {@code name}
 *       is {@code null}.</li>
 * </ul>
 *
 * Exactly one of {@code name} / {@code type} is non-null.
 */
public record TargetPC(String name, String type) implements PointcutExpression {

    /** Binding form: {@code target(o)}. */
    public static TargetPC binding(String name) {
        return new TargetPC(name, null);
    }

    /** Type-pattern form: {@code target(Cipher)} / {@code target(Cipher+)}. */
    public static TargetPC type(String type) {
        return new TargetPC(null, type);
    }
}
