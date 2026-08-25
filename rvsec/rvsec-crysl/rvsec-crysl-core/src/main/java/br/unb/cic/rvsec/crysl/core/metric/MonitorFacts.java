package br.unb.cic.rvsec.crysl.core.metric;

import br.unb.cic.rvsec.crysl.core.model.Provenance;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * The MOP-side facts M0 needs and {@code SpecModel} has no field for, expressed in types the model
 * module owns.
 *
 * <p>{@code SpecModel} is the shape both languages are lifted to, so it carries nothing that only
 * JavaMOP has; {@code mop.MopLift} carries those facts on the lifter side. M0 lives in the model
 * module and may not depend on the lifter (design D-16), so the caller hands it this record. It is a
 * parameter object and not an abstraction: there is one producer, the MOP lift, and one consumer,
 * {@link M0Vitality}.
 *
 * <p>Three of the four fields come from the parser and cannot be recovered from the text:
 *
 * <ul>
 *   <li>{@code declaredParameters} is {@code spec.getParameters().size()};</li>
 *   <li>{@code eventsBindingParameters} is how many events have a non-empty
 *       {@code getMOPParametersOnSpec()} — the event parameters that are also specification
 *       parameters. It is the numerator of the {@code n/N} binding fraction M0.1 reads;</li>
 *   <li>{@code handlers} is keyed exactly as {@code getHandlers()} reports it, which is
 *       <strong>lowercased</strong>: {@code @match1} arrives as {@code "match1"}, so a lookup
 *       written {@code "@match1"} finds nothing and reports the handler absent.</li>
 * </ul>
 *
 * <p>The fourth, {@code absorption}, is parser-free and is produced by {@link MisuseAbsorption}
 * itself.
 *
 * @param declaredParameters      number of parameters the specification declares
 * @param declaredEvents          number of events it declares
 * @param eventsBindingParameters number of those events that bind at least one declared parameter
 * @param handlers                handler key (lowercased) to what the parser found; a key missing
 *                                from the map is {@link HandlerState#ABSENT}
 * @param absorption              whether misuse is reported from inside an event body
 * @param site                    where the specification itself is declared, which is what every
 *                                M0 finding without a narrower position is stamped with
 */
public record MonitorFacts(int declaredParameters, int declaredEvents, int eventsBindingParameters,
                           Map<String, HandlerState> handlers, MisuseAbsorption absorption,
                           Provenance site) {

    /** The handler key JavaMOP fires when the observed word leaves the language. */
    public static final String FAIL = "fail";

    /** The prefix of every handler key JavaMOP fires when the word is accepted. */
    public static final String MATCH_PREFIX = "match";

    public MonitorFacts {
        Objects.requireNonNull(absorption, "MonitorFacts.absorption is mandatory");
        Objects.requireNonNull(site, "MonitorFacts.site is mandatory");
        Map<String, HandlerState> copy = new LinkedHashMap<>();
        for (Map.Entry<String, HandlerState> entry : handlers.entrySet()) {
            copy.put(entry.getKey().toLowerCase(), entry.getValue());
        }
        handlers = Map.copyOf(copy);
        if (declaredParameters < 0 || declaredEvents < 0 || eventsBindingParameters < 0) {
            throw new IllegalArgumentException("MonitorFacts counts are non-negative, got "
                    + declaredParameters + "/" + declaredEvents + "/" + eventsBindingParameters);
        }
        if (eventsBindingParameters > declaredEvents) {
            throw new IllegalArgumentException("MonitorFacts.eventsBindingParameters ("
                    + eventsBindingParameters + ") exceeds declaredEvents (" + declaredEvents + ")");
        }
    }

    /** What the parser found under {@code key}, lowercasing it first (trap (e)). */
    public HandlerState handler(String key) {
        return handlers.getOrDefault(key.toLowerCase(), HandlerState.ABSENT);
    }

    /** Whether a {@code @fail} is declared with at least one statement in it. */
    public boolean failCanAccuse() {
        return handler(FAIL) == HandlerState.NON_EMPTY;
    }

    /**
     * The declared {@code @match}-family keys, sorted.
     *
     * <p>Sorted rather than in declaration order: {@code Map.copyOf} does not preserve iteration
     * order, and a violation message that named the same two handlers in a different order from run
     * to run would not be diffable against the last run.
     */
    public List<String> matchKeys() {
        return handlers.keySet().stream().filter(key -> key.startsWith(MATCH_PREFIX)).sorted()
                .toList();
    }
}
