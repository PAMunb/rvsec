package br.unb.cic.rv.grammar.util;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.net.URL;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Stream;

/**
 * Deterministic, portable demand counter for the AspectJ grammar coverage matrix. Replaces the
 * shell {@code grep} + {@code ProcessBuilder} approach with pure Java (no {@code bash}, no
 * {@code LC_ALL}, no shell quoting). Invoked directly by {@code MatrixIntegrityTest}.
 *
 * <p>Two demand signals:
 * <ul>
 *   <li>{@link #countMop} — <b>SourceDemand</b>: scans the {@code .mop} corpora under
 *       {@code $RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/{aspect,jca,generic,generic_new}/},
 *       matching <b>only {@code *.mop} files plus {@code aspect/Coverage.aj}</b>. The git-ignored
 *       {@code -s} stray {@code *.aj} build artifacts that sit in {@code jca/} and
 *       {@code generic_new/} are NEVER matched (R11.1) — they would inflate
 *       {@code execution()}/{@code within()} counts.</li>
 *   <li>{@link #countCompiledAj} — <b>PipelineDemand</b>: scans the committed
 *       {@code empirical-monitors/{jca,generic,generic_new}/MultiSpec_1MonitorAspect.aj} snapshot
 *       (post-JavaMOP compilation, WITHOUT {@code -s}). PipelineDemand is the authoritative scope
 *       signal: closures ship in-change when {@code countCompiledAj ≥ 1}.</li>
 * </ul>
 *
 * <p>A designator's {@link Pattern} distinguishes pointcut use from Java-statement use; the map is
 * the audit trail quoted inline in the matrix. {@code testSourceDemandCountsReproducible} and
 * {@code testPipelineDemandCountsReproducible} assert the matrix columns against this helper
 * (INV-INS-93).
 */
public final class DemandCounter {

    private DemandCounter() { }

    /** Source corpora shipped by the project. The compiled-{@code .aj} corpus has no ASPECT entry
     *  (Coverage.aj is absorbed by {@code coverage-weaver}, never compiled into the MultiSpec aspect). */
    public enum Corpus {
        ASPECT, JCA, GENERIC, GENERIC_NEW;

        /** Directory name under the resource roots. */
        public String dir() {
            return name().toLowerCase();
        }
    }

    // ----- Designator keys (the regex-map vocabulary). -------------------------------------------
    // These are DemandCounter's own logical designator names, distinct from the matrix "AspectJ
    // syntax" column keys (AspectJDesignators); §5 maps matrix rows to these designators when it
    // fills the SourceDemand/PipelineDemand columns. The regex map is extended empirically in §1.

    public static final String CONDITION = "condition";
    public static final String STATICSIG = "__STATICSIG";
    public static final String ADVICEEXECUTION = "adviceexecution";
    public static final String EXECUTION_POSITIVE = "execution_positive";
    public static final String WITHIN_POSITIVE = "within_positive";
    public static final String NOT_WITHIN = "not_within";
    public static final String IF_PCD = "if_pcd";
    public static final String TARGET_TYPE = "target_type";
    public static final String ARGS_TYPE = "args_type";
    public static final String NOT_TARGET = "not_target";
    public static final String NOT_ARGS = "not_args";
    public static final String CALL_RETURN_TSUBTYPE = "call_return_tsubtype";
    public static final String CALL_OWNER_TSUBTYPE = "call_owner_tsubtype";
    public static final String CALL_NAME_GLOB = "call_name_glob";
    public static final String CALL_TRAILING_VARARGS = "call_trailing_varargs";
    public static final String CALL_RETURN_WILDCARD = "call_return_wildcard";

    /**
     * Per-designator pattern map. Each pattern is anchored to distinguish pointcut use from
     * Java-statement use. The counting rule (per-occurrence) is uniform: every {@link Matcher#find}
     * hit in a corpus file counts one. Negated-form ownership is disambiguated by dedicated keys
     * ({@link #NOT_WITHIN}, {@link #NOT_TARGET}, {@link #NOT_ARGS}) so a negated occurrence is owned
     * by exactly one designator (INV-INS-93 §1.2b).
     *
     * <p><b>Seed map (round-11 §3.4)</b>: covers the designators referenced by §1 demand regen and
     * the §4 path-β assertion tests. Extended/validated empirically in §1; the matrix quotes each
     * pattern inline for reviewer audit.
     */
    static final Map<String, Pattern> PATTERNS = new LinkedHashMap<>();
    static {
        // condition(...) — JavaMOP MOP-extension; absorbed by the JavaMOP compiler (β).
        PATTERNS.put(CONDITION, Pattern.compile("(?<![A-Za-z0-9_])condition\\s*\\("));
        // __STATICSIG macro — absorbed by the JavaMOP compiler (β).
        PATTERNS.put(STATICSIG, Pattern.compile("__STATICSIG"));
        // adviceexecution() — appears only inside !adviceexecution() in commonPointcut.
        PATTERNS.put(ADVICEEXECUTION, Pattern.compile("(?<![A-Za-z0-9_])adviceexecution\\s*\\("));
        // Positive execution(...) — excludes the "execution(" inside "adviceexecution(" (word
        // boundary) and the negated "!execution(" form.
        PATTERNS.put(EXECUTION_POSITIVE, Pattern.compile("(?<![A-Za-z0-9_!])execution\\s*\\("));
        // Positive within(...) — excludes "withincode(" (no "(" right after "within"), the negated
        // "!within(" form, and "adviceexecution".
        PATTERNS.put(WITHIN_POSITIVE, Pattern.compile("(?<![A-Za-z0-9_!])within\\s*\\("));
        // Negated within — !within(...).
        PATTERNS.put(NOT_WITHIN, Pattern.compile("!\\s*within\\s*\\("));
        // if(...) AspectJ PCD — pointcut-level use (after && / || or at clause start), NOT a Java
        // "if (" statement in an advice body.
        PATTERNS.put(IF_PCD, Pattern.compile("(?:^|&&|\\|\\|)\\s*if\\s*\\("));
        // target(Type) / args(Type) type-matching forms — capital-initial argument (a type, not a
        // lowercase binding name). Includes the negated forms via NOT_TARGET / NOT_ARGS keys.
        PATTERNS.put(TARGET_TYPE, Pattern.compile("(?<![A-Za-z0-9_!])target\\s*\\(\\s*[A-Z]"));
        PATTERNS.put(ARGS_TYPE, Pattern.compile("(?<![A-Za-z0-9_!])args\\s*\\(\\s*[A-Z]"));
        PATTERNS.put(NOT_TARGET, Pattern.compile("!\\s*target\\s*\\("));
        PATTERNS.put(NOT_ARGS, Pattern.compile("!\\s*args\\s*\\("));
        // T+ in call() return position — zero demand everywhere (NOT-NEEDED α, §4.R'); the pattern
        // matches a subtype marker on the return type immediately after "call(".
        PATTERNS.put(CALL_RETURN_TSUBTYPE,
                Pattern.compile("call\\s*\\(\\s*[A-Za-z_][A-Za-z0-9_.]*\\+\\s+"));
        // §4.O — T+ in call() OWNER position (the "Owner+.method" subtype marker). Counted
        // PER-OCCURRENCE of the "+." owner token (INV-INS-93 §1.2b: per-line yields 39, per-occurrence
        // yields 64 in generic_new — the matrix pins per-occurrence). The leading alnum/underscore
        // class anchors the marker to an identifier owner, so the standalone "(..)" varargs token and
        // the return-position "T+ " (followed by a space) are NOT matched. Disjoint from
        // CALL_RETURN_TSUBTYPE (that requires a space after "+", this requires a "." after "+") and
        // from the negated keys (no "!" involvement).
        PATTERNS.put(CALL_OWNER_TSUBTYPE, Pattern.compile("[A-Za-z0-9_]\\+\\."));
        // §4.X — method-name prefix glob "name*" in call() (e.g. "add*", "write*"). Anchored to an
        // identifier-char immediately before "*(" so the leading "* " return-type wildcard (space after
        // the "*") is NOT matched, and so only the method-name token glob is counted. 13 sites in
        // generic_new; 0 elsewhere. Per-occurrence.
        PATTERNS.put(CALL_NAME_GLOB, Pattern.compile("call\\([^)]*[A-Za-z0-9_]\\*\\("));
        // §4.V — "(T, ..)" trailing-mixed varargs inside a call() signature: a parameter list with at
        // least one concrete leading parameter followed by ", ..". The ", .." prefix distinguishes this
        // from the standalone "(..)" accept-anything form (no preceding parameter). 6 jca sites; 0
        // elsewhere. Per-occurrence.
        PATTERNS.put(CALL_TRAILING_VARARGS, Pattern.compile("call\\([^)]*, \\.\\.\\)"));
        // §4.RW — "* " (match-any) return-type wildcard in the return position of a call(): the "*"
        // immediately after "call(" followed by a space (the return-type slot, before the owner). This
        // is the dominant generic/generic_new call shape "call(* Owner.name(..))". Anchored to "call(\*
        // " so the method-name token glob "name*(" (CALL_NAME_GLOB, where "*" abuts "(") and the
        // standalone "(..)" varargs token are NOT matched. Per-occurrence: 240 generic, 67 generic_new,
        // 0 jca (jca call() sites all spell a concrete return like "public void Owner.name(..)").
        PATTERNS.put(CALL_RETURN_WILDCARD, Pattern.compile("call\\(\\* "));
    }

    // ----- Public API ----------------------------------------------------------------------------

    /** SourceDemand: occurrences of {@code designator} in {@code corpus}'s {@code .mop} files
     *  (plus {@code aspect/Coverage.aj}). */
    public static int countMop(String designator, Corpus corpus) {
        Pattern p = pattern(designator);
        int total = 0;
        for (Path f : mopFiles(corpus)) {
            total += count(p, f);
        }
        return total;
    }

    /** PipelineDemand: occurrences of {@code designator} in {@code corpus}'s compiled
     *  {@code MultiSpec_1MonitorAspect.aj}. ASPECT has no compiled corpus and returns 0. */
    public static int countCompiledAj(String designator, Corpus corpus) {
        Pattern p = pattern(designator);
        Path f = compiledAjFile(corpus);
        return (f == null) ? 0 : count(p, f);
    }

    /** All SourceDemand counts: designator -> (corpus -> count). */
    public static Map<String, Map<Corpus, Integer>> countAllMop() {
        Map<String, Map<Corpus, Integer>> out = new LinkedHashMap<>();
        for (String d : PATTERNS.keySet()) {
            Map<Corpus, Integer> per = new LinkedHashMap<>();
            for (Corpus c : Corpus.values()) {
                per.put(c, countMop(d, c));
            }
            out.put(d, per);
        }
        return out;
    }

    /** All PipelineDemand counts: designator -> (corpus -> count) over {JCA, GENERIC, GENERIC_NEW}. */
    public static Map<String, Map<Corpus, Integer>> countAllCompiledAj() {
        Map<String, Map<Corpus, Integer>> out = new LinkedHashMap<>();
        for (String d : PATTERNS.keySet()) {
            Map<Corpus, Integer> per = new LinkedHashMap<>();
            for (Corpus c : new Corpus[]{Corpus.JCA, Corpus.GENERIC, Corpus.GENERIC_NEW}) {
                per.put(c, countCompiledAj(d, c));
            }
            out.put(d, per);
        }
        return out;
    }

    // ----- Path resolution -----------------------------------------------------------------------

    /** {@code $RVSEC_HOME/rvsec/rvsec-mop/src/main/resources}. */
    static Path mopRoot() {
        String home = System.getenv("RVSEC_HOME");
        if (home == null || home.isBlank()) {
            throw new IllegalStateException(
                    "RVSEC_HOME is not set — required to resolve the .mop source corpora for DemandCounter.countMop");
        }
        return Paths.get(home, "rvsec", "rvsec-mop", "src", "main", "resources");
    }

    /**
     * Compiled-{@code .aj} corpus root, resolved by a three-step lookup chain (D-decision):
     * (1) JVM system property {@code gh62.compiled.aj.path}; (2) environment variable
     * {@code GH62_COMPILED_AJ_PATH}; (3) the committed fixture directory
     * {@code grammar-tests/src/test/resources/compiled-aj-fixtures/} on the test classpath
     * (byte-identical to {@code empirical-monitors/}), so CI runs without {@code $RVSEC_HOME} access
     * still produce reproducible counts.
     */
    static Path compiledAjRoot() {
        String prop = System.getProperty("gh62.compiled.aj.path");
        if (prop != null && !prop.isBlank()) {
            return Paths.get(prop);
        }
        String env = System.getenv("GH62_COMPILED_AJ_PATH");
        if (env != null && !env.isBlank()) {
            return Paths.get(env);
        }
        URL fixtures = DemandCounter.class.getClassLoader().getResource("compiled-aj-fixtures");
        if (fixtures == null) {
            throw new IllegalStateException(
                    "compiled-aj-fixtures not on the test classpath and neither gh62.compiled.aj.path nor "
                            + "GH62_COMPILED_AJ_PATH is set — cannot resolve the compiled .aj corpus");
        }
        try {
            return Paths.get(fixtures.toURI());
        } catch (java.net.URISyntaxException e) {
            throw new IllegalStateException("malformed compiled-aj-fixtures URL: " + fixtures, e);
        }
    }

    // ----- Internals -----------------------------------------------------------------------------

    private static Pattern pattern(String designator) {
        Pattern p = PATTERNS.get(designator);
        if (p == null) {
            throw new IllegalArgumentException(
                    "unknown designator '" + designator + "' — not in DemandCounter.PATTERNS (known: "
                            + PATTERNS.keySet() + ")");
        }
        return p;
    }

    /** The {@code .mop} files (plus {@code aspect/Coverage.aj}) for a corpus; stray {@code *.aj}
     *  build artifacts in {@code jca/}/{@code generic_new/} are excluded (R11.1). Symlinks not followed. */
    private static List<Path> mopFiles(Corpus corpus) {
        Path dir = mopRoot().resolve(corpus.dir());
        if (!Files.isDirectory(dir)) {
            return List.of();
        }
        List<Path> files = new ArrayList<>();
        try (Stream<Path> s = Files.list(dir)) {
            s.filter(Files::isRegularFile).forEach(f -> {
                String n = f.getFileName().toString();
                if (n.endsWith(".mop") || n.equals("Coverage.aj")) {
                    files.add(f);
                }
            });
        } catch (IOException e) {
            throw new UncheckedIOException("failed to list .mop corpus " + dir, e);
        }
        return files;
    }

    /** The compiled {@code MultiSpec_1MonitorAspect.aj} for a corpus, or {@code null} for ASPECT
     *  (no compiled corpus) or when the file is absent. */
    private static Path compiledAjFile(Corpus corpus) {
        if (corpus == Corpus.ASPECT) {
            return null;
        }
        Path f = compiledAjRoot().resolve(corpus.dir()).resolve("MultiSpec_1MonitorAspect.aj");
        return Files.isRegularFile(f) ? f : null;
    }

    private static int count(Pattern p, Path file) {
        String content;
        try {
            content = Files.readString(file);
        } catch (IOException e) {
            throw new UncheckedIOException("failed to read corpus file " + file, e);
        }
        Matcher m = p.matcher(content);
        int n = 0;
        while (m.find()) {
            n++;
        }
        return n;
    }
}
