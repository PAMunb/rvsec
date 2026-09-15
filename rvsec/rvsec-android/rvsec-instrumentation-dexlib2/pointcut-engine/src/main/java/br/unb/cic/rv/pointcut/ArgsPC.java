package br.unb.cic.rv.pointcut;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * {@code args(...)} — two overlapping views of the same comma-separated body:
 *
 * <ul>
 *   <li>{@code names}: the binding-name list (advice-parameter identifiers),
 *       preserved for the advice-emitter which joins these against the positional
 *       {@code argN} register keys. {@code args(o, o1)} → {@code [o, o1]}.</li>
 *   <li>{@code types}: the POSITIONAL element list used by the matcher (§4.AT).
 *       Each entry classifies the corresponding {@code args} position as a Type
 *       (capitalized/qualified/{@code T+}), a binding name (lowercase ident → entry
 *       is {@code null}, no type filtering), {@code "*"} (accept-any-single), or
 *       {@code ".."} (trailing accept-any-rest). Its size, with the trailing
 *       {@code ".."} counted apart, is the arity the matcher enforces in every form
 *       (INV-INS-159).</li>
 * </ul>
 *
 * <p>The two lists are independent because they answer different questions: the
 * emitter needs binding names (skipping wildcards), the matcher needs positional
 * type/wildcard structure. {@code names} match the {@code AdviceDescriptor.parameters}
 * list by name; {@code types} drive the arity check and declared-type subtype matching
 * against the matched call's argument descriptors.
 */
public record ArgsPC(List<String> names, List<String> types) implements PointcutExpression {

    public ArgsPC {
        names = List.copyOf(names);
        // types positions may be null (a binding-name position carries no type
        // filter), so List.copyOf is unusable — it rejects null elements. Use a
        // null-tolerant unmodifiable copy.
        types = Collections.unmodifiableList(new ArrayList<>(types));
    }
}
