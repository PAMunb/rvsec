package br.unb.cic.rvsec.crysl.core.metric;

import br.unb.cic.rvsec.crysl.core.model.Provenance;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * The four idioms a {@code .mop} specification uses to implement a CrySL {@code CONSTRAINTS}
 * clause, read out of the specification's text.
 *
 * <h2>Why text, and why here</h2>
 *
 * <p>Two of the four idioms are invisible in the canonical model. {@code SpecModel.constraints}
 * holds only the {@code condition(…)} clauses of the events, which is idiom B in its guarded form;
 * a helper method declared inside the specification (idiom C) and an external helper class in
 * {@code rvsec-core} (idiom D) leave no trace there at all, and the most common shape of all —
 * an {@code Arrays.asList(…)} allow-list consulted from an event <em>body</em> rather than from a
 * guard — leaves none either. A census built on the model alone would report those clauses absent,
 * which is exactly the failure this metric exists to avoid: it would publish a limitation of the
 * reader as a defect of the specification.
 *
 * <p>So the reader is textual, and it is deliberately shallow. It recognises the shapes the corpus
 * actually writes and refuses everything else out loud (see {@link ClauseFamily#OTHER}). It is not
 * a Java parser and must not become one: what it needs to answer is "is there a site of a known
 * idiom over these names or these values", and a shape it does not know is a countable {@code
 * Unknown}, not an occasion to grow the reader.
 *
 * <h2>Comments are stripped first, and that is not cosmetic</h2>
 *
 * <p>The specifications of this corpus carry long comments that quote the clauses they implement —
 * and, in several files, quote the clauses they deliberately <em>do not</em> implement, with the
 * measurement that justified the deletion. {@code GCMParameterSpecSpec} spells out
 * {@code offset >= 0 && len >= 0 && src.length >= offset + len} in the comment explaining why those
 * three conjuncts were removed. A reader that scanned raw text would find them and report the
 * clauses implemented. A comment is not countable and does not enter a metric.
 */
public final class SpecificationIdioms {

    /**
     * A comparison, written so that Java generics do not look like one.
     *
     * <p>{@code List<String> algorithms = …} contains {@code <} and {@code >} and is not a
     * comparison. The relational operators are therefore only recognised when they are spaced,
     * which the corpus always does and a type argument never does; the two-character operators
     * need no such care because no type argument contains them.
     */
    private static final Pattern COMPARISON = Pattern.compile(
            "[\\w)\\]]\\s*(?:>=|<=|==|!=)\\s*|[\\w)\\]]\\s+[<>]\\s+");

    private static final Pattern ARRAYS_AS_LIST = Pattern.compile("Arrays\\s*\\.\\s*asList\\s*\\(");

    private static final Pattern LIST_VARIABLE = Pattern.compile("(\\w+)\\s*=\\s*$");

    private static final Pattern HELPER = Pattern.compile(
            "\\bprivate\\s+(?:static\\s+)?[\\w<>\\[\\],\\s]+?\\b(\\w+)\\s*\\(");

    private static final Pattern ALIAS_CALL = Pattern.compile(
            "ConscryptAliasTable\\s*\\.\\s*(?:matches|canonical)\\s*\\(\\s*\"([^\"]*)\"");

    private static final Pattern MOP_IMPORT = Pattern.compile(
            "^\\s*import\\s+(?:static\\s+)?(br\\.unb\\.cic\\.mop\\.[\\w.]+)", Pattern.MULTILINE);

    private static final Pattern INSTANCEOF = Pattern.compile("\\binstanceof\\b");

    /** An {@code Arrays.asList(…)} literal: idiom A, or idiom C when it sits inside a helper. */
    public record AllowList(String variable, Set<String> values, int offset,
                            Optional<String> helper) {
    }

    /** A method the specification declares for itself: idiom C. */
    public record Helper(String name, int start, int end) {
    }

    /** A site of an idiom, with the text that was matched so a reader can judge it. */
    public record Site(String evidence, Provenance where, Optional<String> helper) {
    }

    private final String file;
    private final String code;
    private final List<Helper> helpers;
    private final List<AllowList> allowLists;
    private final List<int[]> statements;
    private final List<Object[]> aliasCalls;
    private final List<String> mopImports;

    private SpecificationIdioms(String file, String code) {
        this.file = file;
        this.code = code;
        this.helpers = findHelpers(code);
        this.allowLists = findAllowLists(code, helpers);
        this.statements = findStatements(code);
        this.aliasCalls = findAliasCalls(code);
        this.mopImports = findMopImports(code);
    }

    /**
     * Reads one specification.
     *
     * @param file the file name, for provenance
     * @param text the specification source as it stands (INV-CONF-12: read, never written)
     * @return the idioms it contains
     */
    public static SpecificationIdioms of(String file, String text) {
        Objects.requireNonNull(file, "file is mandatory");
        Objects.requireNonNull(text, "text is mandatory");
        return new SpecificationIdioms(file, stripComments(text));
    }

    /** The file this was read from. */
    public String file() {
        return file;
    }

    /** The source with comments already blanked out. */
    public String code() {
        return code;
    }

    /** The {@code Arrays.asList(…)} literals, in declaration order. */
    public List<AllowList> allowLists() {
        return List.copyOf(allowLists);
    }

    /** The methods the specification declares for itself. */
    public List<Helper> helpers() {
        return List.copyOf(helpers);
    }

    /** The {@code br.unb.cic.mop} classes it imports — the candidates for idiom D. */
    public List<String> mopImports() {
        return List.copyOf(mopImports);
    }

    /** Whether the specification tests a runtime type anywhere. */
    public boolean usesInstanceof() {
        return INSTANCEOF.matcher(code).find();
    }

    /**
     * The alias-table service this site consults, if any.
     *
     * <p>This is the field task 8.2 exists for. An allow-list that is textually identical to the
     * rule's is <em>not</em> the same check when it is tested through {@code
     * ConscryptAliasTable.matches(…)}: the table maps platform spellings onto the list's entries,
     * so the specification admits strings the rule's literal list does not. A reader that compared
     * the two lists character by character would answer "conformant" where the correct verdict is
     * "more permissive", which is why the dependency is recorded per clause rather than as a
     * footnote about the corpus.
     *
     * <p>Only the service name is recorded here. How many alias rows that service actually has is a
     * property of {@code ConscryptAliasTable}, which lives in another Maven module, and the
     * distribution is very uneven — so a caller that wants the weight of the dependency reads the
     * table itself rather than trusting a number copied into this one.
     */
    private Optional<String> aliasServiceNear(String variable, Optional<String> helper) {
        for (Object[] call : aliasCalls) {
            String service = (String) call[0];
            String arguments = (String) call[1];
            if (variable != null && !variable.isBlank() && containsWord(arguments, variable)) {
                return Optional.of(service);
            }
        }
        if (helper.isPresent()) {
            for (Helper declared : helpers) {
                if (!declared.name().equals(helper.get())) {
                    continue;
                }
                for (Object[] call : aliasCalls) {
                    int offset = (Integer) call[2];
                    if (offset >= declared.start() && offset < declared.end()) {
                        return Optional.of((String) call[0]);
                    }
                }
            }
        }
        return Optional.empty();
    }

    /**
     * An allow-list of this specification that shares at least one value with the clause.
     *
     * <p>The comparison is case-insensitive because the set declares case-insensitivity as its one
     * normalisation rule, and because the corpus relies on it: {@code SSLContext.crysl} writes
     * {@code TLSv1.2} and {@code SSLContextSpec} writes {@code TLSV1.2}. Intersection rather than
     * equality is the right test for <em>which idiom implements this clause</em>: a list that is
     * wider or narrower than the rule's still implements it, and how it differs is a divergence for
     * the corpus record rather than a reason to call the clause unimplemented.
     */
    public Optional<Site> allowListFor(Set<String> values) {
        Set<String> wanted = upper(values);
        for (AllowList list : allowLists) {
            if (!intersects(list.values(), wanted)) {
                continue;
            }
            return Optional.of(new Site(evidenceAt(list.offset()), at(list.offset()), list.helper()));
        }
        return Optional.empty();
    }

    /**
     * A comparison of this specification that mentions one of the clause's values together with the
     * clause's own variable.
     *
     * <p>This is the second shape a value clause takes: {@code KeyPairGeneratorSpec} writes
     * {@code case "EC": return keySize == 256;} where the rule writes {@code keysize in {256}}. The
     * variable is required here — unlike in {@link #allowListFor(Set)} — because a bare numeric
     * literal is far too common to identify a clause on its own, and the variable name survives
     * translation in this corpus up to capitalisation.
     */
    public Optional<Site> comparisonWithValue(String variable, Set<String> values) {
        Set<String> wanted = upper(values);
        for (int[] bounds : statements) {
            String statement = code.substring(bounds[0], bounds[1]);
            if (!COMPARISON.matcher(statement).find()) {
                continue;
            }
            if (!containsWordIgnoringCase(statement, variable)) {
                continue;
            }
            for (String value : wanted) {
                if (containsWordIgnoringCase(statement, value)) {
                    return Optional.of(new Site(statement.strip(), at(bounds[0]), helperAt(bounds[0])));
                }
            }
        }
        return Optional.empty();
    }

    /**
     * A comparison of this specification over every one of the clause's variables.
     *
     * <p>All of them, not any of them: {@code length[output1] > outOffset} is implemented by a
     * statement that mentions {@code output1} <em>and</em> {@code outOffset}, and one that mentions
     * only {@code outOffset} is about something else. The names are matched exactly, because on
     * this side of the translation they were carried over verbatim — {@code IvParameterSpec.crysl}
     * writes {@code iv}, {@code offset} and {@code len} and {@code IvParameterSpec.mop} writes the
     * same three.
     *
     * <p>What this does not check is the operator. The corpus contains at least one clause where the
     * specification wrote a weaker one — the rule's {@code len > 0} against the specification's
     * {@code len >= 0} — and the census answers "implemented by idiom B" for it, with the matched
     * statement carried in {@link Site#evidence()} so that the weakening is visible rather than
     * asserted away. M3 counts idioms; whether an idiom is faithful is a divergence, adjudicated in
     * the corpus record.
     */
    public Optional<Site> comparisonOver(Set<String> variables) {
        if (variables.isEmpty()) {
            return Optional.empty();
        }
        for (int[] bounds : statements) {
            String statement = code.substring(bounds[0], bounds[1]);
            if (!COMPARISON.matcher(statement).find()) {
                continue;
            }
            boolean all = true;
            for (String variable : variables) {
                if (!containsWord(statement, variable)) {
                    all = false;
                    break;
                }
            }
            if (all) {
                return Optional.of(new Site(statement.strip(), at(bounds[0]), helperAt(bounds[0])));
            }
        }
        return Optional.empty();
    }

    /**
     * The external helper class this specification delegates to, if it imports one.
     *
     * <p>Idiom D is an import from {@code br.unb.cic.mop} plus a use of a name that class exports.
     * The predicate substrate ({@code PredicateStore}, {@code ExecutionContext}) and the reporting
     * envelope ({@code ErrorCollector} and its types) are imported by every specification of the set
     * and implement no clause, so the caller names the exported symbols it is looking for rather
     * than this method guessing from the import list.
     *
     * <p><strong>A list, and not a set, because the first match wins.</strong> A specification that
     * calls two of the names the family expects — {@code CipherSpec} calls {@code isValid} at line
     * 159 and {@code alg} at line 85 — has two candidate sites, and the one this returns is the
     * {@link Site} that ends up in the published {@code mop_line} column. With a {@code Set} the
     * winner was whichever name the JVM's iteration order happened to visit first, and
     * {@code Set.of}'s order is salted per JVM, so the same corpus published two different
     * provenances on two runs (INV-CONF-02). The caller therefore states the precedence and this
     * method honours it, in order.
     *
     * @param exportedNames the helper entry points the family expects, in precedence order
     */
    public Optional<Site> externalHelper(List<String> exportedNames) {
        if (mopImports.isEmpty()) {
            return Optional.empty();
        }
        for (String name : exportedNames) {
            if (helpers.stream().anyMatch(helper -> helper.name().equals(name))) {
                // Declared in the specification itself: that is idiom C, not D.
                continue;
            }
            Matcher matcher = Pattern.compile("\\b" + Pattern.quote(name) + "\\s*\\(").matcher(code);
            if (matcher.find()) {
                return Optional.of(new Site(evidenceAt(matcher.start()), at(matcher.start()),
                        Optional.empty()));
            }
        }
        return Optional.empty();
    }

    /**
     * A statement of this specification mentioning every one of the given words.
     *
     * <p>Unlike {@link #comparisonOver(Set)} this asks for no operator, because the shape it serves
     * — a runtime {@code instanceof} — is not a comparison.
     */
    public Optional<Site> statementWith(String... words) {
        for (int[] bounds : statements) {
            String statement = code.substring(bounds[0], bounds[1]);
            boolean all = true;
            for (String word : words) {
                if (!containsWord(statement, word)) {
                    all = false;
                    break;
                }
            }
            if (all) {
                return Optional.of(new Site(statement.strip(), at(bounds[0]), helperAt(bounds[0])));
            }
        }
        return Optional.empty();
    }

    /** The alias-table service consulted at a site, empty when the site consults none. */
    public Optional<String> aliasServiceOf(Site site) {
        String evidence = site.evidence();
        Matcher matcher = ALIAS_CALL.matcher(evidence);
        if (matcher.find()) {
            return Optional.of(matcher.group(1));
        }
        for (AllowList list : allowLists) {
            // A blank name means the list was written inline, with nothing to look it up by; a
            // blank needle would match every evidence string and attribute the wrong service.
            if (!list.variable().isBlank() && containsWord(evidence, list.variable())) {
                return aliasServiceNear(list.variable(), site.helper());
            }
        }
        return aliasServiceNear("", site.helper());
    }

    /** Where an offset falls, as {@code file:line}. */
    public Provenance at(int offset) {
        int line = 1;
        for (int i = 0; i < offset && i < code.length(); i++) {
            if (code.charAt(i) == '\n') {
                line++;
            }
        }
        return new Provenance(file, line);
    }

    private Optional<String> helperAt(int offset) {
        for (Helper helper : helpers) {
            if (offset >= helper.start() && offset < helper.end()) {
                return Optional.of(helper.name());
            }
        }
        return Optional.empty();
    }

    private String evidenceAt(int offset) {
        int start = offset;
        while (start > 0 && code.charAt(start - 1) != '\n' && code.charAt(start - 1) != ';'
                && code.charAt(start - 1) != '{' && code.charAt(start - 1) != '}') {
            start--;
        }
        int end = offset;
        while (end < code.length() && code.charAt(end) != '\n' && code.charAt(end) != ';') {
            end++;
        }
        return code.substring(start, Math.min(end + 1, code.length())).strip();
    }

    // ── reading ───────────────────────────────────────────────────────────────────────────────

    /**
     * Blanks out comments, keeping every other character at its own offset so that line numbers
     * survive. Replacing them with nothing would shift every provenance in the file.
     */
    static String stripComments(String text) {
        char[] out = text.toCharArray();
        boolean inLine = false;
        boolean inBlock = false;
        boolean inString = false;
        boolean inChar = false;
        for (int i = 0; i < out.length; i++) {
            char c = out[i];
            char next = i + 1 < out.length ? out[i + 1] : '\0';
            if (inLine) {
                if (c == '\n') {
                    inLine = false;
                } else {
                    out[i] = ' ';
                }
            } else if (inBlock) {
                if (c == '*' && next == '/') {
                    out[i] = ' ';
                    out[i + 1] = ' ';
                    i++;
                    inBlock = false;
                } else if (c != '\n') {
                    out[i] = ' ';
                }
            } else if (inString) {
                if (c == '\\') {
                    i++;
                } else if (c == '"') {
                    inString = false;
                }
            } else if (inChar) {
                if (c == '\\') {
                    i++;
                } else if (c == '\'') {
                    inChar = false;
                }
            } else if (c == '/' && next == '/') {
                out[i] = ' ';
                out[i + 1] = ' ';
                i++;
                inLine = true;
            } else if (c == '/' && next == '*') {
                out[i] = ' ';
                out[i + 1] = ' ';
                i++;
                inBlock = true;
            } else if (c == '"') {
                inString = true;
            } else if (c == '\'') {
                inChar = true;
            }
        }
        return new String(out);
    }

    private static List<Helper> findHelpers(String code) {
        List<Helper> found = new ArrayList<>();
        Matcher matcher = HELPER.matcher(code);
        while (matcher.find()) {
            int open = code.indexOf('{', matcher.end());
            if (open < 0) {
                continue;
            }
            int depth = 0;
            int end = open;
            for (int i = open; i < code.length(); i++) {
                if (code.charAt(i) == '{') {
                    depth++;
                } else if (code.charAt(i) == '}') {
                    depth--;
                    if (depth == 0) {
                        end = i;
                        break;
                    }
                }
            }
            found.add(new Helper(matcher.group(1), matcher.start(), end));
        }
        return found;
    }

    private static List<AllowList> findAllowLists(String code, List<Helper> helpers) {
        List<AllowList> found = new ArrayList<>();
        Matcher matcher = ARRAYS_AS_LIST.matcher(code);
        while (matcher.find()) {
            int open = matcher.end() - 1;
            int close = matchParen(code, open);
            if (close < 0) {
                continue;
            }
            Set<String> values = new LinkedHashSet<>();
            for (String argument : splitTopLevel(code.substring(open + 1, close))) {
                String value = argument.strip();
                if (value.startsWith("\"") && value.endsWith("\"") && value.length() >= 2) {
                    value = value.substring(1, value.length() - 1);
                }
                if (!value.isEmpty()) {
                    values.add(value.toUpperCase(Locale.ROOT));
                }
            }
            String before = code.substring(Math.max(0, matcher.start() - 80), matcher.start());
            Matcher variable = LIST_VARIABLE.matcher(before);
            String name = variable.find() ? variable.group(1) : "";
            Optional<String> helper = Optional.empty();
            for (Helper declared : helpers) {
                if (matcher.start() >= declared.start() && matcher.start() < declared.end()) {
                    helper = Optional.of(declared.name());
                }
            }
            found.add(new AllowList(name, values, matcher.start(), helper));
        }
        return found;
    }

    /** Statement bounds, cut at {@code ;}, {@code &#123;} and {@code &#125;}. */
    private static List<int[]> findStatements(String code) {
        List<int[]> bounds = new ArrayList<>();
        int start = 0;
        for (int i = 0; i < code.length(); i++) {
            char c = code.charAt(i);
            if (c == ';' || c == '{' || c == '}') {
                if (i > start) {
                    bounds.add(new int[] {start, i});
                }
                start = i + 1;
            }
        }
        if (start < code.length()) {
            bounds.add(new int[] {start, code.length()});
        }
        return bounds;
    }

    private static List<Object[]> findAliasCalls(String code) {
        List<Object[]> calls = new ArrayList<>();
        Matcher matcher = ALIAS_CALL.matcher(code);
        while (matcher.find()) {
            int open = code.indexOf('(', matcher.start());
            int close = matchParen(code, open);
            String arguments = close < 0 ? "" : code.substring(open + 1, close);
            calls.add(new Object[] {matcher.group(1), arguments, matcher.start()});
        }
        return calls;
    }

    private static List<String> findMopImports(String code) {
        List<String> imports = new ArrayList<>();
        Matcher matcher = MOP_IMPORT.matcher(code);
        while (matcher.find()) {
            imports.add(matcher.group(1));
        }
        return imports;
    }

    private static int matchParen(String code, int open) {
        int depth = 0;
        for (int i = open; i < code.length(); i++) {
            char c = code.charAt(i);
            if (c == '(') {
                depth++;
            } else if (c == ')') {
                depth--;
                if (depth == 0) {
                    return i;
                }
            }
        }
        return -1;
    }

    private static List<String> splitTopLevel(String arguments) {
        List<String> parts = new ArrayList<>();
        int depth = 0;
        int start = 0;
        for (int i = 0; i < arguments.length(); i++) {
            char c = arguments.charAt(i);
            if (c == '(' || c == '[' || c == '{') {
                depth++;
            } else if (c == ')' || c == ']' || c == '}') {
                depth--;
            } else if (c == ',' && depth == 0) {
                parts.add(arguments.substring(start, i));
                start = i + 1;
            }
        }
        parts.add(arguments.substring(start));
        return parts;
    }

    private static Set<String> upper(Set<String> values) {
        Set<String> upper = new LinkedHashSet<>();
        for (String value : values) {
            upper.add(value.toUpperCase(Locale.ROOT));
        }
        return upper;
    }

    private static boolean intersects(Set<String> left, Set<String> right) {
        for (String value : left) {
            if (right.contains(value)) {
                return true;
            }
        }
        return false;
    }

    private static boolean containsWord(String haystack, String word) {
        if (word == null || word.isBlank()) {
            return false;
        }
        return Pattern.compile("(?<![\\w$])" + Pattern.quote(word) + "(?![\\w$])")
                .matcher(haystack).find();
    }

    private static boolean containsWordIgnoringCase(String haystack, String word) {
        if (word == null || word.isBlank()) {
            return false;
        }
        return Pattern.compile("(?<![\\w$])" + Pattern.quote(word) + "(?![\\w$])",
                Pattern.CASE_INSENSITIVE).matcher(haystack).find();
    }
}
