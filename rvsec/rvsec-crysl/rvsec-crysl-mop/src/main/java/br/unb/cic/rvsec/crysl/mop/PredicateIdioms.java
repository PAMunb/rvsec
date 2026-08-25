package br.unb.cic.rvsec.crysl.mop;

import br.unb.cic.rvsec.crysl.core.model.Polarity;
import br.unb.cic.rvsec.crysl.core.model.PredicateRef;
import br.unb.cic.rvsec.crysl.core.model.Provenance;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.Optional;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Recognises the specification-side idioms that stand for CrySL's {@code ENSURES}, {@code REQUIRES}
 * and {@code NEGATES}, on <strong>both</strong> substrates the corpora use.
 *
 * <h2>Why substrate A is still required</h2>
 *
 * <p>The current {@code jca_android} set has <strong>zero</strong> {@code ExecutionContext} sites —
 * it moved to {@code PredicateStore} entirely — so a reader written against today's working tree
 * alone would conclude that {@link PredicateSite.Substrate#EXECUTION_CONTEXT} is dead code and
 * delete it. It is not. The frozen {@code jca} set uses {@code ExecutionContext} in all 23 of its
 * files (110 call sites), and {@code jca} is the set the published measurements were taken over.
 * Any comparison against those numbers — and the whole point of the calibration gate is that such
 * comparisons happen — has to read the frozen set, which means reading substrate A. The third
 * corpus, {@code jca_android_bug_predicate}, is on substrate A as well, with 152 sites.
 *
 * <p>Neither substrate is a superset of the other, which is why they are recognised separately
 * rather than through one normalised idiom: substrate A binds one object per predicate, compares it
 * with {@code equals} and answers a boolean; substrate B binds an object plus further value
 * arguments, compares by identity, and answers three-valued so that "the predicate was never
 * written" is distinguishable from "the predicate was written and does not hold".
 *
 * <h2>Why the scan is over text and not over the AST</h2>
 *
 * <p>The idioms live inside Java blocks — an event's action, a {@code condition(...)} clause, a
 * {@code @match} or {@code @fail} handler. The parser reconstructs those blocks from detached
 * strings and stamps them with fabricated positions, so an AST walk can find the calls but cannot
 * say where they are, and INV-CONF-13 requires every predicate reference to carry {@code
 * file:line}. The scan therefore runs over {@link SourceText}, whose comments are blanked: the
 * corpus contains prose that names these methods, for instance {@code jca_android/MacSpec.mop:254},
 * and a scan that counted comments would report predicate references the file does not make.
 */
public final class PredicateIdioms {

    private static final Pattern EXECUTION_CONTEXT_CALL = Pattern.compile(
            "ExecutionContext\\s*\\.\\s*instance\\s*\\(\\s*\\)\\s*\\.\\s*"
                    + "(setProperty|validate|remove|setObjectAsInAcceptingState"
                    + "|unsetObjectAsInAcceptingState)\\s*\\(");

    private static final Pattern PREDICATE_STORE_CALL = Pattern.compile(
            "PredicateStore\\s*\\.\\s*instance\\s*\\(\\s*\\)\\s*\\.\\s*"
                    + "(ensure|validate|validateAbsent|negate)\\s*\\(");

    /** {@code Property.GENERATED_MAC} and {@code GENERATED_MAC} both yield {@code GENERATED_MAC}. */
    private static final Pattern PROPERTY_ARGUMENT =
            Pattern.compile("^(?:[\\w.]*\\.)?([A-Za-z_$][\\w$]*)$");

    private static final Pattern VERDICT_COMPARISON =
            Pattern.compile("\\A\\s*[!=]=\\s*(?:PredicateVerdict\\s*\\.\\s*)?([A-Z_]+)");

    private PredicateIdioms() {
    }

    /**
     * Everything the two substrates say in one file.
     *
     * @param source the file, comments already blanked
     * @return the recognised sites, in the order they appear in the file
     */
    public static List<PredicateSite> scan(SourceText source) {
        List<PredicateSite> sites = new ArrayList<>();
        collect(source, EXECUTION_CONTEXT_CALL, PredicateSite.Substrate.EXECUTION_CONTEXT, sites);
        collect(source, PREDICATE_STORE_CALL, PredicateSite.Substrate.PREDICATE_STORE, sites);
        sites.sort((a, b) -> Integer.compare(a.ref().site().line(), b.ref().site().line()));
        return sites;
    }

    /**
     * The {@code setObjectAsInAcceptingState} / {@code unsetObjectAsInAcceptingState} marks of a
     * file, which are <em>not</em> predicate references.
     *
     * <p>In CrySL an {@code ENSURES} fires only when the object is in an accepting state of the
     * {@code ORDER}. Substrate A implements that guard explicitly, by marking the object in the
     * {@code @match} handler. It is the precondition of an ensure and not an ensure, so it is kept
     * out of {@code SpecModel.ensures}: putting it there would add 38 references the rules never
     * declare and move M4's denominator by that much.
     */
    public static List<AcceptingStateMark> acceptingStateMarks(SourceText source) {
        List<AcceptingStateMark> marks = new ArrayList<>();
        Matcher matcher = EXECUTION_CONTEXT_CALL.matcher(source.code());
        while (matcher.find()) {
            String method = matcher.group(1);
            if (!method.endsWith("ObjectAsInAcceptingState")) {
                continue;
            }
            List<String> arguments = argumentsOf(source, matcher.end() - 1);
            marks.add(new AcceptingStateMark(
                    "setObjectAsInAcceptingState".equals(method),
                    arguments.isEmpty() ? "" : arguments.get(0),
                    source.at(matcher.start())));
        }
        return marks;
    }

    private static void collect(SourceText source, Pattern pattern,
                                PredicateSite.Substrate substrate, List<PredicateSite> out) {
        Matcher matcher = pattern.matcher(source.code());
        while (matcher.find()) {
            String method = matcher.group(1);
            if (method.endsWith("ObjectAsInAcceptingState")) {
                continue;
            }
            int openParen = matcher.end() - 1;
            List<String> arguments = argumentsOf(source, openParen);
            if (arguments.isEmpty()) {
                continue;
            }
            String name = propertyNameOf(arguments.get(0));
            if (name == null) {
                continue;
            }
            PredicateSite.Kind kind = kindOf(method);
            Provenance site = source.at(matcher.start());
            PredicateRef ref = new PredicateRef(name, arguments.subList(1, arguments.size()),
                    polarityOf(source, method, matcher.start()), site);
            out.add(new PredicateSite(kind, substrate, verdictAt(source, openParen), ref));
        }
    }

    /**
     * The section a call belongs to. {@code validateAbsent} lands in {@code REQUIRES} and not in
     * {@code NEGATES}: it is a precondition stating that the predicate must be absent — the CrySL
     * {@code !p[...]} of a {@code REQUIRES} clause — whereas {@code NEGATES} is the rule
     * <em>withdrawing</em> a predicate it had previously ensured.
     */
    private static PredicateSite.Kind kindOf(String method) {
        return switch (method) {
            case "setProperty", "ensure" -> PredicateSite.Kind.ENSURES;
            case "validate", "validateAbsent" -> PredicateSite.Kind.REQUIRES;
            case "remove", "negate" -> PredicateSite.Kind.NEGATES;
            default -> throw new IllegalStateException("unrecognised idiom method: " + method);
        };
    }

    private static List<String> argumentsOf(SourceText source, int openParen) {
        int close = source.matchParen(openParen);
        if (close < 0) {
            return List.of();
        }
        return SourceText.splitArguments(source.code().substring(openParen + 1, close - 1));
    }

    /** Strips a qualifier: {@code Property.GENERATED_MAC} is the predicate {@code GENERATED_MAC}. */
    private static String propertyNameOf(String argument) {
        Matcher matcher = PROPERTY_ARGUMENT.matcher(argument.trim());
        return matcher.matches() ? matcher.group(1) : null;
    }

    /**
     * Whether the site asks for the predicate or for its absence.
     *
     * <p>Two idioms say "absent" and the corpora use both. {@code validateAbsent} says it in the
     * method name — substrate B's three-valued read, which answers {@code VIOLATED} when the
     * predicate is present. Substrate A has no such method, so the same requirement is written from
     * the violating branch, {@code condition(!ExecutionContext.instance().validate(p, x))}: the
     * event fires exactly when {@code p} is absent. Both are the CrySL {@code !p[x]} of a {@code
     * REQUIRES} clause and both lift to {@link Polarity#NEGATED}.
     *
     * <p>Measured at {@code 5fbe8173}: {@code jca_android} makes 5 {@code validateAbsent} calls
     * (2 in {@code IvChainJunction.mop}, 2 in {@code CipherSpec.mop}, 1 in {@code MacSpec.mop} —
     * the raw {@code grep} count of 9 includes 4 prose mentions, which {@link SourceText} blanks).
     */
    private static Polarity polarityOf(SourceText source, String method, int callStart) {
        return "validateAbsent".equals(method) || negatedAt(source, callStart)
                ? Polarity.NEGATED : Polarity.POSITIVE;
    }

    /**
     * Whether a {@code !} applies to this call, ignoring whitespace and the parentheses that only
     * group it.
     *
     * <p>Both spellings occur and mean the same thing: {@code condition(!EC.instance().validate(…))}
     * and {@code condition(!(EC.instance().validate(…)))}. {@code jca/PBEParameterSpecSpec.mop:47}
     * and its {@code jca_android_bug_predicate} twin write the second one, and a reader that only
     * knew the first lifted those two references with the wrong polarity — {@code REQUIRES p} where
     * the file demands {@code REQUIRES !p} — which is an M4 edge reported present that is really
     * inverted.
     *
     * <p>An opening parenthesis is walked through only while it is the last thing before the call,
     * which is what makes it a grouping parenthesis and not an argument list or another operand:
     * {@code validate(EC.instance().validate(…))} stops on the {@code e} of {@code validate}, and
     * {@code a || (EC.instance().validate(…))} stops on the {@code |}. Only a {@code !} immediately
     * to the left of the call, or of the parentheses wrapping nothing but the call, negates it.
     */
    private static boolean negatedAt(SourceText source, int callStart) {
        for (int i = callStart - 1; i >= 0; i--) {
            char c = source.code().charAt(i);
            if (Character.isWhitespace(c) || c == '(') {
                continue;
            }
            return c == '!';
        }
        return false;
    }

    /**
     * The {@code PredicateVerdict} constant the call is compared against, when the comparison is
     * written on the call itself. {@code IvChainJunction.mop:141} binds the verdict to a local and
     * tests it on the next line; there the comparison is not on the call and this returns empty
     * rather than guessing which test belongs to which call.
     */
    private static Optional<String> verdictAt(SourceText source, int openParen) {
        int close = source.matchParen(openParen);
        if (close < 0) {
            return Optional.empty();
        }
        Matcher matcher = VERDICT_COMPARISON.matcher(source.code().substring(close));
        return matcher.find() ? Optional.of(matcher.group(1)) : Optional.empty();
    }

    /**
     * One {@code ExecutionContext.instance().set/unsetObjectAsInAcceptingState(o)} call.
     *
     * @param set    {@code true} for {@code set}, {@code false} for {@code unset}
     * @param object the argument expression as written
     * @param site   where it was written
     */
    public record AcceptingStateMark(boolean set, String object, Provenance site) {

        public AcceptingStateMark {
            Objects.requireNonNull(object, "AcceptingStateMark.object is mandatory");
            Objects.requireNonNull(site, "AcceptingStateMark.site is mandatory");
        }
    }
}
