package br.unb.cic.rvsec.crysl.core.calibration;

import java.util.ArrayList;
import java.util.Collection;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Target 8's route: which specifications the <em>generated monitor</em> builds a
 * {@code MapOfMonitor} for.
 *
 * <p>This is a reader, not a metric. It parses nothing of either specification language — it reads
 * the text of {@code MultiSpec_1RuntimeMonitor.java} as {@code rv-monitor} wrote it, which is why
 * it can contradict M0.1's AST proxy and why target 8 costs a generation pass (D-18). The proxy
 * asks whether the specification declares a parameter some event binds; this asks what the
 * generator actually emitted. They agree on the current corpus, and the agreement is a measurement
 * rather than an assumption only because both were taken.
 *
 * <p>The generated monitor names a specification by its <strong>declared</strong> name, which is
 * routinely not its file name: {@code RandomStringPassword.mop} declares
 * {@code RandomStringPasswordSpec} and {@code IvChainJunction.mop} declares
 * {@code IvChainJunctionSpec}. {@link #asFileNames} maps the declared names back, so both sides of
 * the comparison speak the identity the rest of the component uses.
 *
 * @param declared the specifications the monitor declares a monitor class for, in name order
 * @param indexing those of them it also declares a {@code MapOfMonitor} field for
 */
public record MonitorIndexCensus(List<String> declared, List<String> indexing) {

    /** The rule this reader applies, printed beside the number it produces. */
    public static final String RULE =
            "a specification indexes when MultiSpec_1RuntimeMonitor.java declares a field of the "
                    + "shape 'MapOfMonitor<XMonitor> X_..._Map' for it; it is declared when the "
                    + "same file declares a 'class XMonitor'. Names are the specification's "
                    + "DECLARED name, which is mapped back to the .mop file name before comparison";

    /** {@code class XMonitor} — how the generator names a specification's monitor class. */
    private static final Pattern MONITOR_CLASS =
            Pattern.compile("\\bclass\\s+([A-Za-z_0-9]+)Monitor\\b");

    /** {@code MapOfMonitor<XMonitor> X_c_Map} — the field whose presence is the whole question. */
    private static final Pattern MAP_FIELD =
            Pattern.compile("MapOfMonitor<\\s*([A-Za-z_0-9]+)Monitor\\s*>\\s+[A-Za-z_0-9]+_Map");

    /** The generator's own aggregate class, which is not a specification. */
    private static final String AGGREGATE = "MultiSpec_1Runtime";

    public MonitorIndexCensus {
        declared = List.copyOf(declared);
        indexing = List.copyOf(indexing);
    }

    /**
     * Reads one generated monitor.
     *
     * @param monitorSource the text of {@code MultiSpec_1RuntimeMonitor.java}
     * @return what it declares and what it indexes
     */
    public static MonitorIndexCensus read(String monitorSource) {
        Objects.requireNonNull(monitorSource, "monitorSource is mandatory");
        return new MonitorIndexCensus(sorted(names(MONITOR_CLASS, monitorSource)),
                sorted(names(MAP_FIELD, monitorSource)));
    }

    /** The specifications the monitor declares but builds no {@code MapOfMonitor} for. */
    public List<String> notIndexing() {
        Set<String> indexed = new LinkedHashSet<>(indexing);
        return declared.stream().filter(name -> !indexed.contains(name)).toList();
    }

    /**
     * Translates declared specification names into the {@code .mop} file names the rest of the
     * component identifies a specification by.
     *
     * <p>A declared name is its own file name, or the file name with {@code Spec} appended. A name
     * matching neither is returned unchanged rather than dropped: silently losing a specification
     * would turn a naming surprise into a smaller count, which is the shape of error this whole
     * component exists to catch.
     *
     * @param declaredNames the names to translate
     * @param fileNames     the corpus file names, without the {@code .mop} extension
     * @return the translated names, in the order given
     */
    public static List<String> asFileNames(List<String> declaredNames,
                                           Collection<String> fileNames) {
        Set<String> files = new LinkedHashSet<>(fileNames);
        List<String> translated = new ArrayList<>(declaredNames.size());
        for (String declared : declaredNames) {
            if (files.contains(declared)) {
                translated.add(declared);
            } else if (declared.endsWith("Spec")
                    && files.contains(declared.substring(0, declared.length() - "Spec".length()))) {
                translated.add(declared.substring(0, declared.length() - "Spec".length()));
            } else {
                translated.add(declared);
            }
        }
        return translated;
    }

    private static Set<String> names(Pattern pattern, String source) {
        Set<String> found = new LinkedHashSet<>();
        Matcher matcher = pattern.matcher(source);
        while (matcher.find()) {
            String name = matcher.group(1);
            if (!AGGREGATE.equals(name)) {
                found.add(name);
            }
        }
        return found;
    }

    private static List<String> sorted(Set<String> names) {
        List<String> ordered = new ArrayList<>(names);
        ordered.sort(String::compareTo);
        return ordered;
    }
}
