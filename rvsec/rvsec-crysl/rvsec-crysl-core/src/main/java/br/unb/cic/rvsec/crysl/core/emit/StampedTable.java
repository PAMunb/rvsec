package br.unb.cic.rvsec.crysl.core.emit;

import br.unb.cic.rvsec.crysl.core.model.SourceStamp;
import br.unb.cic.rvsec.crysl.core.model.Version;
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

/**
 * The one object in this package that turns numbers into text, and the one that refuses.
 *
 * <p>INV-CONF-02 says a table reporting a count without naming the rule that produced it must not
 * be emitted. A rule stated in a comment is not a rule: it cannot fail a build and it cannot stop
 * an emission. So the counting rule is a mandatory constructor argument here, and every emitter of
 * this package builds its output as a {@code StampedTable} - there is no second path from an
 * aggregate to a character. {@code EmitterChokePointTest} checks that structurally: no other class
 * of {@code core.emit} may touch {@code java.nio.file.Files}, a {@code Writer} or an
 * {@code OutputStream}, so an emitter that tried to write around this class would fail the build
 * rather than quietly publish an unstamped table.
 *
 * <p>Both versions are carried, never one (D-17, INV-CONF-01). The input spans two git
 * repositories - {@code rvsec} for the specifications and {@code rvsec-cognicrypt} for the oracle -
 * so a table that put specification and rule side by side under a single scalar commit would stamp
 * an oracle-derived number with the commit of a repository that did not produce it.
 *
 * <p>The stamp occupies a fixed position in every format so a reader never has to hunt for it
 * (task 4.7): the last {@link #STAMP_COLUMNS} columns of every CSV row, the bullet block
 * immediately under the H1 of every Markdown report, and the first member of every JSON document.
 */
public final class StampedTable {

    /**
     * The stamp columns every emitted CSV row ends with, in this order.
     *
     * <p>They are trailing columns rather than a comment preamble because the Python readers under
     * {@code scripts/} that consume these files during the coexistence window use a plain
     * {@code csv.DictReader}: a leading {@code #} line would be read as the header row and turn
     * every one of them into a parse failure. A {@code DictReader} ignores columns it does not
     * know, so appending is the only extension a reader survives.
     */
    public static final List<String> STAMP_COLUMNS = List.of(
            "mop_corpus", "mop_repository", "mop_commit", "mop_read_at",
            "oracle_corpus", "oracle_repository", "oracle_commit", "oracle_read_at",
            "counting_rule");

    private final String title;
    private final Version mopVersion;
    private final Version oracleVersion;
    private final String countingRule;
    private final List<String> bodyColumns;
    private final List<List<String>> rows;

    /**
     * @param title        what the table is about, used as the Markdown H1
     * @param mopVersion   corpus and commit of the {@code .mop} side
     * @param oracleVersion corpus and commit of the CrySL side
     * @param countingRule the rule behind every aggregate in {@code rows}, stated in full
     * @param bodyColumns  the columns of the table proper, before the stamp columns
     * @param rows         one entry per row, each the size of {@code bodyColumns}
     * @throws IllegalArgumentException when the counting rule is absent or blank (INV-CONF-02), or
     *                                  when a row does not have the width of the header
     */
    public StampedTable(String title, Version mopVersion, Version oracleVersion,
                        String countingRule, List<String> bodyColumns, List<List<String>> rows) {
        this.title = Objects.requireNonNull(title, "StampedTable.title is mandatory");
        this.mopVersion = requireStamped(mopVersion, "mop");
        this.oracleVersion = requireStamped(oracleVersion, "oracle");
        if (countingRule == null || countingRule.isBlank()) {
            throw new IllegalArgumentException(
                    "INV-CONF-02: the table '" + title + "' reports counts and names no counting "
                            + "rule; a table that does not say how it counted must not be emitted");
        }
        this.countingRule = countingRule;
        this.bodyColumns = List.copyOf(bodyColumns);
        List<List<String>> copied = new ArrayList<>(rows.size());
        for (List<String> row : rows) {
            if (row.size() != this.bodyColumns.size()) {
                throw new IllegalArgumentException("row of width " + row.size()
                        + " in a table of width " + this.bodyColumns.size() + ": " + row);
            }
            copied.add(List.copyOf(row));
        }
        this.rows = List.copyOf(copied);
    }

    /**
     * A version whose fields are present and are not placeholders.
     *
     * <p>The model's records already reject {@code null}. What they cannot reject is a stamp filled
     * with the empty string or with {@code "unknown"}, which type-checks and still fails to say
     * which corpus state the table describes.
     */
    private static Version requireStamped(Version version, String side) {
        if (version == null) {
            throw new MissingVersionError(
                    "INV-CONF-01: the " + side + " version of this table is absent");
        }
        requireIdentifying(version.corpus(), side + " corpus");
        SourceStamp source = version.source();
        requireIdentifying(source.repository(), side + " repository");
        requireIdentifying(source.commit(), side + " commit");
        return version;
    }

    private static void requireIdentifying(String value, String what) {
        if (value == null || value.isBlank() || "unknown".equalsIgnoreCase(value.trim())
                || "TODO".equalsIgnoreCase(value.trim())) {
            throw new MissingVersionError("INV-CONF-01: the " + what
                    + " is a placeholder (" + value + "), so the table it stamps names no corpus "
                    + "state; emission is refused rather than publishing an unattributable count");
        }
    }

    /** The columns of the table proper, before the stamp. */
    public List<String> bodyColumns() {
        return bodyColumns;
    }

    /** The full emitted CSV header: the body columns followed by the stamp columns. */
    public List<String> csvHeader() {
        List<String> header = new ArrayList<>(bodyColumns);
        header.addAll(STAMP_COLUMNS);
        return List.copyOf(header);
    }

    /** The rule behind every aggregate in this table. */
    public String countingRule() {
        return countingRule;
    }

    /**
     * The stamp as an ordered map, for the JSON document header.
     *
     * <p>Ordered because the JSON emitter writes it as the first member of the document and a
     * reader is entitled to find the fields in the same order as the CSV columns.
     */
    public Map<String, String> stamp() {
        Map<String, String> stamp = new LinkedHashMap<>();
        for (int i = 0; i < STAMP_COLUMNS.size(); i++) {
            stamp.put(STAMP_COLUMNS.get(i), stampValues().get(i));
        }
        return Map.copyOf(stamp);
    }

    private List<String> stampValues() {
        return List.of(
                mopVersion.corpus(), mopVersion.source().repository(),
                mopVersion.source().commit(), mopVersion.source().data().toString(),
                oracleVersion.corpus(), oracleVersion.source().repository(),
                oracleVersion.source().commit(), oracleVersion.source().data().toString(),
                countingRule);
    }

    /**
     * The table as RFC 4180 CSV, with {@code \n} line endings on every platform.
     *
     * <p>The line ending is fixed rather than taken from the platform because these files are
     * compared against committed ones by {@code git diff}, and a run on another machine must not
     * show every line as changed.
     */
    public String csv() {
        StringBuilder out = new StringBuilder();
        appendCsvRow(out, csvHeader());
        List<String> stamp = stampValues();
        for (List<String> row : rows) {
            List<String> full = new ArrayList<>(row);
            full.addAll(stamp);
            appendCsvRow(out, full);
        }
        return out.toString();
    }

    private static void appendCsvRow(StringBuilder out, List<String> cells) {
        for (int i = 0; i < cells.size(); i++) {
            if (i > 0) {
                out.append(',');
            }
            out.append(escapeCsv(cells.get(i)));
        }
        out.append('\n');
    }

    private static String escapeCsv(String cell) {
        String value = cell == null ? "" : cell;
        boolean needsQuotes = value.indexOf(',') >= 0 || value.indexOf('"') >= 0
                || value.indexOf('\n') >= 0 || value.indexOf('\r') >= 0;
        if (!needsQuotes) {
            return value;
        }
        return '"' + value.replace("\"", "\"\"") + '"';
    }

    /**
     * The table as a Markdown report in the shape of {@code data/gh104/evidence/harness/*.md}: an
     * H1, the stamp as the bullet block directly under it, then the table.
     *
     * @param sections extra prose blocks appended after the table, already Markdown
     */
    public String markdown(List<String> sections) {
        StringBuilder out = new StringBuilder();
        out.append("# ").append(title).append("\n\n");
        out.append("- **mop** `").append(mopVersion.corpus()).append("` — `")
                .append(mopVersion.source().repository()).append('@')
                .append(mopVersion.source().commit()).append("` read ")
                .append(mopVersion.source().data()).append('\n');
        out.append("- **oracle** `").append(oracleVersion.corpus()).append("` — `")
                .append(oracleVersion.source().repository()).append('@')
                .append(oracleVersion.source().commit()).append("` read ")
                .append(oracleVersion.source().data()).append('\n');
        out.append("- **counting rule** ").append(countingRule).append('\n');
        out.append("- rows: ").append(rows.size()).append("\n\n");

        appendMarkdownRow(out, bodyColumns);
        out.append('|');
        for (int i = 0; i < bodyColumns.size(); i++) {
            out.append("---|");
        }
        out.append('\n');
        for (List<String> row : rows) {
            appendMarkdownRow(out, row);
        }
        for (String section : sections) {
            out.append('\n').append(section);
            if (!section.endsWith("\n")) {
                out.append('\n');
            }
        }
        return out.toString();
    }

    private static void appendMarkdownRow(StringBuilder out, List<String> cells) {
        out.append('|');
        for (String cell : cells) {
            out.append(' ').append(escapeMarkdown(cell)).append(" |");
        }
        out.append('\n');
    }

    private static String escapeMarkdown(String cell) {
        String value = cell == null ? "" : cell;
        return value.replace("|", "\\|").replace("\r\n", " ").replace('\n', ' ');
    }

    /**
     * Write already-rendered text to disk, creating the parent directories.
     *
     * <p>This is the package's only filesystem write, which is what makes the choke point a fact
     * rather than a convention: an emitter cannot reach a file except by handing text to this
     * class, and it cannot produce text except by building a table that carries its counting rule.
     */
    public static void write(Path target, String content) {
        try {
            Path parent = target.getParent();
            if (parent != null) {
                Files.createDirectories(parent);
            }
            Files.writeString(target, content, StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new UncheckedIOException("could not write " + target, e);
        }
    }
}
