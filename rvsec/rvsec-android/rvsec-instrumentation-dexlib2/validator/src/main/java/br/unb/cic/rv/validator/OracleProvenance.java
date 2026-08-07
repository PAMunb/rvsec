package br.unb.cic.rv.validator;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * The {@code provenance:} block of a {@code *-oracle.yaml}, and the rule that
 * decides whether an oracle carrying it is admissible as ground truth.
 *
 * <p>A ground-truth oracle derived from a run of the pipeline under test is
 * circular: it would restate what the implementation does and then check the
 * implementation against it. That objection is why Layer 3 was declared N/A in
 * May 2026 rather than populated from an existing run.
 *
 * <p>An oracle derived from a recording of a <em>different</em> weaver is not
 * circular in the same way — it states what an independent implementation of
 * the same specification observed. That makes the three-oracle minimum
 * reachable from data already on disk instead of by writing YAML by hand or by
 * lowering the threshold. What keeps the concession honest is that the class is
 * declared in the file, the source is content-addressed, and a source naming
 * the implementation under test is rejected by this loader rather than by a
 * reviewer noticing (INV-INS-107).
 */
public record OracleProvenance(
        Kind kind,
        /** Free-text citation: doc sections, source files, line numbers, validation steps. */
        String source,
        /** For derived oracles: which weaver produced the recording. */
        String sourceWeaver,
        /** For derived oracles: the recording the events were read out of. */
        String sourceData,
        /** For derived oracles: sha256 of {@link #sourceData} at derivation time. */
        String sourceSha256,
        /** For derived oracles: the script that performed the derivation. */
        String derivationScript
) {

    public enum Kind {
        /** Read from source inspection or manual UI validation. */
        HAND_VALIDATED("hand_validated"),
        /** Read from recorded executions of a weaver other than the one under test. */
        DERIVED_FROM_INDEPENDENT_WEAVER("derived_from_independent_weaver");

        private final String yamlValue;

        Kind(String yamlValue) {
            this.yamlValue = yamlValue;
        }

        public String yamlValue() {
            return yamlValue;
        }

        static Kind fromYaml(String value) {
            for (Kind k : values()) {
                if (k.yamlValue.equals(value)) return k;
            }
            return null;
        }
    }

    /**
     * The implementation under validation. A recording produced by it cannot
     * serve as ground truth for it.
     */
    public static final String IMPLEMENTATION_UNDER_TEST = "dexlib2";

    /**
     * Why an oracle is inadmissible, or {@code null} when it is admissible.
     *
     * <p>The circularity case gets its own message because "malformed file" is
     * the wrong diagnosis for it: the file is well formed, it is the argument
     * that is invalid, and a reader who is told the file is malformed will fix
     * the wrong thing.
     */
    public String rejection() {
        if (kind == null) {
            return "provenance.class missing or unrecognised — expected one of "
                    + Kind.HAND_VALIDATED.yamlValue() + ", "
                    + Kind.DERIVED_FROM_INDEPENDENT_WEAVER.yamlValue();
        }
        if (kind == Kind.HAND_VALIDATED) {
            return isBlank(source)
                    ? "provenance.source missing — a hand-validated oracle must cite the "
                            + "source files, line numbers or validation steps its events came from"
                    : null;
        }
        // Derived: the recording must be named, frozen and attributable, and it
        // must not come from the implementation being validated.
        if (isBlank(sourceWeaver)) {
            return "provenance.source_weaver missing — a derived oracle must name the weaver "
                    + "whose recording it was read from";
        }
        if (IMPLEMENTATION_UNDER_TEST.equalsIgnoreCase(sourceWeaver.trim())) {
            return "circular oracle: provenance.source_weaver is '" + sourceWeaver.trim()
                    + "', the implementation under validation. An oracle derived from a run of "
                    + "the pipeline being validated states what that pipeline does and then "
                    + "checks it against itself; it establishes nothing. Derive it from a "
                    + "recording of an independent weaver instead.";
        }
        if (isBlank(sourceData)) {
            return "provenance.source_data missing — the recording the events were derived from "
                    + "must be named so the derivation can be repeated";
        }
        if (isBlank(sourceSha256)) {
            return "provenance.source_sha256 missing — a derived oracle must be frozen against "
                    + "its source, otherwise re-deriving it after a comparison could quietly "
                    + "retrofit it to the observed behaviour";
        }
        if (isBlank(derivationScript)) {
            return "provenance.derivation_script missing — the derivation must be attributable "
                    + "to a script that can be re-run and audited";
        }
        return null;
    }

    public boolean admissible() {
        return rejection() == null;
    }

    private static boolean isBlank(String s) {
        return s == null || s.isBlank();
    }

    /**
     * Read the {@code provenance:} block out of an oracle YAML.
     *
     * <p>Hand-rolled for the same reason {@code TraceComparator.parseOracle} is:
     * the oracle schema is fixed and small, and the validator carries no YAML
     * dependency. Only the top-level scalars directly under {@code provenance:}
     * are read; nested structures and block scalars are skipped, since none of
     * the admission fields uses them.
     *
     * @return the parsed block, or {@code null} when the file declares no
     *         {@code provenance:} key at all
     */
    static OracleProvenance parse(Path yaml) throws IOException {
        List<String> lines = Files.readAllLines(yaml);
        Map<String, String> fields = new LinkedHashMap<>();
        boolean inBlock = false;
        int baseIndent = -1;

        for (String raw : lines) {
            String noComment = stripComment(raw);
            if (noComment.isBlank()) continue;
            int indent = indentOf(noComment);
            String trimmed = noComment.trim();

            if (!inBlock) {
                if (indent == 0 && trimmed.startsWith("provenance:")) {
                    inBlock = true;
                    baseIndent = indent;
                }
                continue;
            }
            // The block ends at the next key indented at or below "provenance:".
            if (indent <= baseIndent) break;
            int colon = trimmed.indexOf(':');
            if (colon <= 0) continue;
            String key = trimmed.substring(0, colon).trim();
            String value = trimmed.substring(colon + 1).trim();
            // Block scalars (| and >) carry prose, never an admission field.
            if (value.startsWith("|") || value.startsWith(">")) value = "";
            fields.put(key, unquote(value));
        }

        if (!inBlock) return null;
        return new OracleProvenance(
                Kind.fromYaml(fields.get("class")),
                fields.get("source"),
                fields.get("source_weaver"),
                fields.get("source_data"),
                fields.get("source_sha256"),
                fields.get("derivation_script"));
    }

    private static String stripComment(String line) {
        int hash = line.indexOf('#');
        if (hash < 0) return line;
        // Only treat '#' as a comment when it is not inside a quoted value;
        // the admission fields are unquoted paths and hashes, so a simple
        // quote count is enough here.
        long quotes = line.chars().limit(hash).filter(c -> c == '"' || c == '\'').count();
        return quotes % 2 == 0 ? line.substring(0, hash) : line;
    }

    private static int indentOf(String line) {
        int i = 0;
        while (i < line.length() && line.charAt(i) == ' ') i++;
        return i;
    }

    private static String unquote(String v) {
        if (v.length() >= 2
                && ((v.startsWith("\"") && v.endsWith("\""))
                    || (v.startsWith("'") && v.endsWith("'")))) {
            return v.substring(1, v.length() - 1);
        }
        return v;
    }
}
