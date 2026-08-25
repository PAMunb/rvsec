package br.unb.cic.rvsec.crysl.core.model;

import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;

/**
 * One {@code event} declaration of a {@code .mop} specification, or one {@code EVENTS} entry of a
 * CrySL rule, after the pointcut has been resolved to the concrete signatures it matches.
 *
 * <p>{@code declIndex} is not optional and not decorative: declaration order is dispatch order.
 * When two labels match the same signature, the morphism {@code h} maps that signature to the
 * concatenation of their labels <em>in declaration order</em>, so an event that has lost its index
 * has lost the information the comparison needs.
 *
 * <p>{@code signatures} keeps the order the lifter put them in, and that order is part of the
 * contract rather than an implementation detail. It is a pairing key: {@code MopLifter} answers the
 * declared type of a parameterless specification from the <em>first</em> signature its events name,
 * and pairing runs on that answer (INV-CONF-11, design D-06). Held as {@code Set.copyOf} the first
 * element was whatever the JVM's salted hash order put first, so the key of the pairing — and with
 * it, in principle, which rule a specification is measured against — varied between runs of the
 * same corpus. Both lifters build the set in a declared order: {@code PointcutExpander.expand}
 * writes the signatures in the order the pointcut names them, and the CrySL side has one signature
 * per event. This constructor preserves it instead of discarding it.
 *
 * @param label        the declared name of the event
 * @param pointcutText the pointcut as written, kept verbatim for the report
 * @param signatures   the concrete signatures the pointcut resolves to
 * @param guard        the event's {@code condition}, when it declares one
 * @param declIndex    0-based position of the declaration within its file
 */
public record Event(Label label, String pointcutText, Set<Signature> signatures,
                    Optional<Guard> guard, int declIndex) {

    public Event {
        Objects.requireNonNull(label, "Event.label is mandatory");
        Objects.requireNonNull(pointcutText, "Event.pointcutText is mandatory");
        Objects.requireNonNull(guard, "Event.guard is mandatory (use Optional.empty())");
        signatures = Collections.unmodifiableSet(new LinkedHashSet<>(signatures));
        if (declIndex < 0) {
            throw new IllegalArgumentException("Event.declIndex is 0-based, got " + declIndex);
        }
    }
}
