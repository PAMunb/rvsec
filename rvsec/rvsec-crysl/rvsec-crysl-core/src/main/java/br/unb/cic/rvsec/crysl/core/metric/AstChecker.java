package br.unb.cic.rvsec.crysl.core.metric;

import br.unb.cic.rvsec.crysl.core.automata.LabelAutomaton;
import br.unb.cic.rvsec.crysl.core.automata.LabelTransition;
import br.unb.cic.rvsec.crysl.core.model.Event;
import br.unb.cic.rvsec.crysl.core.model.SpecModel;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;

/**
 * The four checks that run over the specification as written, before any normalization.
 *
 * <p>This class exists because of a measured fact rather than a hunch: the defects it catches pass
 * the JavaMOP parser, the RV-Monitor generator and {@code javac} with <strong>zero errors</strong>.
 * {@code jca/GCMParameterSpecSpec.mop} declares two events called {@code c1} and an {@code ere}
 * that names a {@code c2} which does not exist; it parses, generates a monitor and compiles.
 * {@code jca/SecretKeySpecSpec.mop} declares four events and admits two of them in its {@code ere},
 * and does so with an unbalanced parenthesis in the first event's {@code condition}; it also
 * parses, generates and compiles. So neither "it parsed" nor "it compiled" is an oracle of sanity,
 * and nothing downstream of the parser can be relied on to notice.
 *
 * <p>The checks are also deliberately <em>outside</em> the language quotient. A gate that compares
 * languages after normalization cannot see a defect that lives inside its own quotient, and two of
 * these are exactly of that kind: a declared event absent from the formula is local and can even be
 * erased by ε-normalization, and a {@code @match} without a {@code @fail} is about handlers, so two
 * specifications differing only in the handler have identical languages (design D-12).
 *
 * <p>A specification that declares no {@code ere} and no {@code fsm} raises no violation of check
 * (3), and it does so for the right reason rather than by exception: it has no order to violate, so
 * the lifter gives it the automaton that accepts every word over its own alphabet, where every
 * declared event sits on a self-loop. The seventeen property-less files of {@code generic_new} are
 * of that shape.
 *
 * <p>Every violation is one line of text naming the specification, the check and the evidence.
 * They are strings rather than a type hierarchy because nothing branches on them: they are counted
 * and printed, and a closed hierarchy would be four records with one consumer.
 */
public final class AstChecker {

    /** The rule behind every violation this class emits, stated in full (INV-CONF-02). */
    public static final String RULE =
            "four checks over the specification as written, before any normalization: (1) no two "
                    + "events share an identifier; (2) every symbol of the ere/fsm formula is a "
                    + "declared event identifier; (3) every declared event appears in the formula; "
                    + "(4) every declared @match-family handler is paired with a @fail. A file can "
                    + "fail all four and still parse, generate a monitor and compile with zero "
                    + "errors";

    private AstChecker() {
    }

    /**
     * Runs the four checks.
     *
     * @param specification the name every violation is reported under; it is the specification's
     *                      own name and not its declared type, because two files can declare the
     *                      same type - {@code SecretKeySpec.mop} declares {@code SecretKey} - and a
     *                      violation attributed to a type nobody can find the file for is not
     *                      actionable
     * @param model         the lifted specification; {@link SpecModel#events()} keeps declaration
     *                      order and keeps duplicates, which check (1) needs
     * @param labelOrder    the language the {@code ere}/{@code fsm} denotes, over labels
     * @param facts         the handler states, which check (4) needs
     * @return the violations, one line each, in check order; empty when the file is clean
     */
    public static List<String> check(String specification, SpecModel model,
                                     LabelAutomaton labelOrder, MonitorFacts facts) {
        List<String> violations = new ArrayList<>();

        Set<String> declared = new LinkedHashSet<>();
        Set<String> duplicated = new TreeSet<>();
        for (Event event : model.events()) {
            if (!declared.add(event.label().name())) {
                duplicated.add(event.label().name());
            }
        }
        for (String identifier : duplicated) {
            violations.add(specification + ": duplicate event identifier '" + identifier
                    + "'. Two event declarations share a name, so the formula cannot say which one "
                    + "it means and the dispatcher cannot say which one fired");
        }

        Set<String> used = new TreeSet<>();
        for (LabelTransition transition : labelOrder.transitions()) {
            used.add(transition.symbol().name());
        }

        for (String symbol : used) {
            if (!declared.contains(symbol)) {
                violations.add(specification + ": the formula names '" + symbol
                        + "', which no event declares. The symbol can never fire, so the branch of "
                        + "the automaton that reads it is unreachable");
            }
        }

        Set<String> absorbing = new TreeSet<>();
        facts.absorption().events().forEach(label -> absorbing.add(label.name()));
        for (String identifier : declared) {
            if (!used.contains(identifier)) {
                // The corpus writes error-reporting events deliberately outside the ere: the body
                // carries an addError that a condition governs, so the misuse is reported without
                // the word ever leaving the language. That is the "absorbs misuse" idiom and it is
                // not the same finding as an event the automaton forgot, so the line says which
                // one this is instead of leaving the reader to open the file.
                violations.add(specification + ": event '" + identifier
                        + "' is declared and absent from the formula. The call is observed and the "
                        + "automaton never reads it"
                        + (absorbing.contains(identifier)
                                ? "; its body carries an addError, so this is the absorbs-misuse "
                                        + "idiom and not a dropped event"
                                : ""));
            }
        }

        if (!facts.matchKeys().isEmpty() && facts.handler(MonitorFacts.FAIL) == HandlerState.ABSENT) {
            violations.add(specification + ": @" + String.join(", @", facts.matchKeys())
                    + " declared with no @fail. The specification reacts when the word is accepted "
                    + "and says nothing when it is rejected, which is the half that accuses");
        }

        return List.copyOf(violations);
    }

}
