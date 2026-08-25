package br.unb.cic.rvsec.crysl.core.metric;

import br.unb.cic.rvsec.crysl.core.model.Label;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Whether a specification reports a misuse from inside an event body instead of letting the
 * automaton reject the word, and which events do it.
 *
 * <p>This is the "specification absorbs misuse" property, and it is measured here rather than by a
 * shell script because the number has to travel with the rule that produced it (INV-CONF-02). The
 * ad-hoc census it replaces was a regular expression run by hand over a directory; its answer was
 * right and its provenance was a paragraph in a handoff document.
 *
 * <p>The distinction it draws matters for M0.2. A specification whose only {@code addError} sits in
 * an event body accuses <em>without</em> the automaton ever leaving its language: the misuse is
 * absorbed by a {@code condition} that fires an error and lets the trace continue. A specification
 * whose {@code addError} is in {@code @fail} accuses only when the word leaves the language. The two
 * are different accusation sites, and a specification with neither cannot accuse at all.
 *
 * <h2>Why the scan is textual</h2>
 * <p>The rule is anchored on the {@code ere}/{@code fsm} line, and that line is a lexical boundary
 * rather than an AST node: everything before it is declarations and event bodies, everything after
 * it is handlers. Reading it from the parser would mean walking {@code EventDefinition.getAction()},
 * which lives on the {@code javamop} side, and the model module may not depend on either parser
 * (design D-16). The scan is parser-free, so it belongs here; it costs one pass over the file.
 *
 * @param absorbs whether the specification carries at least one such call
 * @param events  the events the calls are attributed to, in file order and without duplicates
 * @param rule    the counting rule, stated in full, travelling with the answer
 */
public record MisuseAbsorption(boolean absorbs, List<Label> events, String rule) {

    /**
     * The counting rule, verbatim.
     *
     * <p>It is deliberately the rule of the independent probe
     * ({@code docs/handoff/20260824_arnes_adjudicacao/scripts/absorve.py}), so that the two routes
     * answer the same question and a disagreement between them is a finding rather than a
     * definitional difference.
     */
    public static final String RULE =
            "a call named addError in the text preceding the first line whose first token is "
                    + "'ere:' or 'fsm:', with comments blanked; the call is attributed to the event "
                    + "whose 'event <id>' declaration most recently precedes it, and a call before "
                    + "the first event declaration is counted in 'absorbs' but attributed to no "
                    + "event";

    private static final Pattern FORMULA_LINE =
            Pattern.compile("^[ \\t]*(ere|fsm)[ \\t]*:", Pattern.MULTILINE);

    private static final Pattern EVENT_DECLARATION =
            Pattern.compile("\\bevent\\s+([A-Za-z_$][\\w$]*)\\b");

    private static final Pattern ADD_ERROR = Pattern.compile("\\baddError\\s*\\(");

    public MisuseAbsorption {
        Objects.requireNonNull(rule, "MisuseAbsorption.rule is mandatory (INV-CONF-02)");
        events = List.copyOf(events);
    }

    /** Runs the scan over a {@code .mop} file, which is read and never written (INV-CONF-12). */
    public static MisuseAbsorption scan(Path mopFile) {
        Objects.requireNonNull(mopFile, "mopFile is mandatory");
        try {
            return scan(new String(Files.readAllBytes(mopFile), StandardCharsets.UTF_8));
        } catch (IOException e) {
            throw new UncheckedIOException("cannot read " + mopFile, e);
        }
    }

    /** Runs the scan over text already in memory. */
    public static MisuseAbsorption scan(String text) {
        String code = blankComments(text);
        Matcher formula = FORMULA_LINE.matcher(code);
        int cut = formula.find() ? formula.start() : code.length();
        String head = code.substring(0, cut);

        Map<String, Label> byName = new LinkedHashMap<>();
        boolean absorbs = false;
        Matcher call = ADD_ERROR.matcher(head);
        while (call.find()) {
            absorbs = true;
            String owner = enclosingEvent(head, call.start());
            if (owner != null) {
                byName.putIfAbsent(owner, new Label(owner));
            }
        }
        return new MisuseAbsorption(absorbs, new ArrayList<>(byName.values()), RULE);
    }

    /** The identifier of the {@code event} declaration nearest above {@code offset}, or null. */
    private static String enclosingEvent(String head, int offset) {
        Matcher declaration = EVENT_DECLARATION.matcher(head);
        String owner = null;
        while (declaration.find() && declaration.start() < offset) {
            owner = declaration.group(1);
        }
        return owner;
    }

    /**
     * The text with every comment character replaced by a space, length and newlines preserved.
     *
     * <p>String and character literals are tracked because a {@code //} inside a literal is not a
     * comment, and the corpus writes message literals with slashes in them ({@code "HMAC/SHA256"});
     * a scan that took the first {@code //} would blank the rest of a live line. Blanking rather
     * than deleting keeps every offset mapping to the original file, which is what lets the
     * attribution above compare positions.
     *
     * <p>This repeats the blanking {@code mop.SourceText} does. The repetition is deliberate and it
     * is one method long: {@code SourceText} lives on the lifter module and the model module may not
     * depend on it (D-16), and the alternative — routing the scan through the lift — would make a
     * parser-free measurement depend on a parser.
     */
    private static String blankComments(String raw) {
        char[] out = raw.toCharArray();
        int i = 0;
        int n = out.length;
        while (i < n) {
            char c = out[i];
            if (c == '"' || c == '\'') {
                char quote = c;
                i++;
                while (i < n && out[i] != quote) {
                    if (out[i] == '\\') {
                        i++;
                    }
                    i++;
                }
                i++;
            } else if (c == '/' && i + 1 < n && out[i + 1] == '/') {
                while (i < n && out[i] != '\n') {
                    out[i++] = ' ';
                }
            } else if (c == '/' && i + 1 < n && out[i + 1] == '*') {
                while (i < n && !(out[i] == '*' && i + 1 < n && out[i + 1] == '/')) {
                    if (out[i] != '\n') {
                        out[i] = ' ';
                    }
                    i++;
                }
                if (i < n) {
                    out[i++] = ' ';
                }
                if (i < n) {
                    out[i++] = ' ';
                }
            } else {
                i++;
            }
        }
        return new String(out);
    }
}
