package br.unb.cic.rvsec.crysl.core.emit;

import br.unb.cic.rvsec.crysl.core.model.Version;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Objects;

/**
 * Emits the four CSV tables in the schemas already committed under {@code data/jca_android/}.
 *
 * <p>The component substitutes those manual tables. That is a claim about the file, not about the
 * numbers: an emitted table whose columns differed from the committed ones would be a second
 * dialect, and the readers under {@code scripts/} would have to grow a branch for each. So the
 * header comes from {@link CsvSchema}, which is checked against the committed files at build time.
 *
 * <p>Every row goes out through a {@link StampedTable}, which is what makes INV-CONF-02 a mechanism
 * here: this class cannot produce a table without handing a counting rule to that constructor, and
 * it cannot write a file except through it.
 *
 * <p><b>Anchoring.</b> The committed files cite the oracle as {@code .cryptsl} paths, because they
 * were produced against the abandoned {@code api30} corpus. Those files stay readable as the
 * historical input, and the component, as the new producer of the map, emits {@code .crysl}
 * references to the upstream rules instead. The row types below refuse a {@code .cryptsl} anchor
 * rather than passing it through, so re-anchoring cannot be forgotten one row at a time.
 */
public final class CsvEmitter {

    /** The clause-level fidelity vocabulary, as INV-CONF-15 and the manual tables publish it. */
    public enum Fidelity {
        /** The specification implements the clause as the rule states it. */
        FIEL,
        /** The specification implements a projection of the clause. */
        PROJETADO,
        /** The specification merges this clause with others into one check. */
        CONFLADO,
        /** The specification does not implement the clause. */
        AUSENTE
    }

    /** Whether this metric derived the row's fidelity class or inherited it from human judgement. */
    public enum Origin {
        DERIVED,
        INHERITED;

        /** The lowercase form the CSV carries, matching the committed vocabulary. */
        public String csv() {
            return name().toLowerCase(Locale.ROOT);
        }
    }

    /**
     * One row of {@code predicate_graph.csv}: one predicate site of one specification.
     *
     * <p>The first fifteen components are the committed schema, in its order. {@code fidelity} and
     * {@code origin} are the two columns this component appends: the committed table says what was
     * decided about the <em>site</em>, in {@code verdict} and {@code disposition}, and says nothing
     * about how faithfully the <em>clause</em> behind that site was implemented. Both are emitted,
     * side by side, because there is no bijection between sites and clauses and either one alone
     * answers a question the other was not asked.
     */
    public record M4Row(String file, String event, String siteKind, String polarity, String guard,
                        String arity, String predicate, String positionTypes, String splitter,
                        String clause, String mechanism, String verdict, String disposition,
                        String reason, String automatonMembership, Fidelity fidelity,
                        Origin origin) {

        public M4Row {
            Objects.requireNonNull(file, "M4Row.file is mandatory");
            Objects.requireNonNull(predicate, "M4Row.predicate is mandatory");
            Objects.requireNonNull(fidelity, "M4Row.fidelity is mandatory");
            Objects.requireNonNull(origin, "M4Row.origin is mandatory (INV-CONF-15)");
            requireUpstreamAnchor(clause, "M4Row.clause");
        }

        List<String> cells() {
            return List.of(file, nullToEmpty(event), nullToEmpty(siteKind), nullToEmpty(polarity),
                    nullToEmpty(guard), nullToEmpty(arity), predicate, nullToEmpty(positionTypes),
                    nullToEmpty(splitter), nullToEmpty(clause), nullToEmpty(mechanism),
                    nullToEmpty(verdict), nullToEmpty(disposition), nullToEmpty(reason),
                    nullToEmpty(automatonMembership), fidelity.name(), origin.csv());
        }
    }

    /**
     * One row of {@code constraint_table.csv}: one clause of one rule against the specification.
     *
     * <p>{@code cryptslLine} carries the committed column name and an upstream {@code .crysl}
     * value. The column is not renamed - a schema is an interface with the readers under
     * {@code scripts/} - and the value is not left on the abandoned anchor.
     */
    public record ConstraintRow(String spec, String cryptslLine, String mopLine, String verdict) {

        public ConstraintRow {
            Objects.requireNonNull(spec, "ConstraintRow.spec is mandatory");
            Objects.requireNonNull(verdict, "ConstraintRow.verdict is mandatory");
            requireUpstreamAnchor(cryptslLine, "ConstraintRow.cryptslLine");
        }

        List<String> cells() {
            return List.of(spec, nullToEmpty(cryptslLine), nullToEmpty(mopLine), verdict);
        }
    }

    /**
     * One row of {@code order_alphabet_map.csv}: one {@code .mop} event against one {@code ORDER}
     * symbol, with the disposition M2 takes its ε-erasure decision from (INV-CONF-10).
     */
    public record AlphabetRow(String spec, String mopEvent, String orderSymbol, String symbolKind,
                              String rule, String ruleLine, String disposition, String reason) {

        public AlphabetRow {
            Objects.requireNonNull(spec, "AlphabetRow.spec is mandatory");
            Objects.requireNonNull(mopEvent, "AlphabetRow.mopEvent is mandatory");
            Objects.requireNonNull(disposition, "AlphabetRow.disposition is mandatory");
            requireUpstreamAnchor(ruleLine, "AlphabetRow.ruleLine");
        }

        List<String> cells() {
            return List.of(spec, mopEvent, nullToEmpty(orderSymbol), nullToEmpty(symbolKind),
                    nullToEmpty(rule), nullToEmpty(ruleLine), disposition, nullToEmpty(reason));
        }
    }

    /** One row of {@code divergence_record.csv}: one departure from the rule, with its reason. */
    public record DivergenceRow(String file, String hunk, String kind, String summary,
                                String reason, String task) {

        public DivergenceRow {
            Objects.requireNonNull(file, "DivergenceRow.file is mandatory");
            Objects.requireNonNull(kind, "DivergenceRow.kind is mandatory");
            Objects.requireNonNull(reason, "DivergenceRow.reason is mandatory");
        }

        List<String> cells() {
            return List.of(file, nullToEmpty(hunk), kind, nullToEmpty(summary), reason,
                    nullToEmpty(task));
        }
    }

    private final Version mopVersion;
    private final Version oracleVersion;

    /**
     * @param mopVersion    corpus and commit of the {@code .mop} side
     * @param oracleVersion corpus and commit of the CrySL side; both are carried because a table
     *                      that reports specification and rule side by side describes two corpora
     */
    public CsvEmitter(Version mopVersion, Version oracleVersion) {
        this.mopVersion = mopVersion;
        this.oracleVersion = oracleVersion;
    }

    /**
     * The M4 table.
     *
     * <p>The counting rule is extended with {@link CsvSchema#M4_JUDGEMENT_CAVEAT} here rather than
     * by the caller, so that no M4 table can be emitted without the caveat INV-CONF-15 requires
     * beside every aggregate. It lands in the {@code counting_rule} column of every row, which is
     * the same cell as the rule it qualifies.
     */
    public StampedTable predicateGraph(String countingRule, List<M4Row> rows) {
        List<List<String>> cells = new ArrayList<>(rows.size());
        for (M4Row row : rows) {
            cells.add(row.cells());
        }
        String rule = countingRule == null || countingRule.isBlank()
                ? countingRule
                : countingRule + " | " + CsvSchema.M4_JUDGEMENT_CAVEAT;
        return new StampedTable("predicate graph", mopVersion, oracleVersion, rule,
                CsvSchema.PREDICATE_GRAPH.bodyColumns(), cells);
    }

    /** The M3 table. */
    public StampedTable constraintTable(String countingRule, List<ConstraintRow> rows) {
        List<List<String>> cells = new ArrayList<>(rows.size());
        for (ConstraintRow row : rows) {
            cells.add(row.cells());
        }
        return new StampedTable("constraint table", mopVersion, oracleVersion, countingRule,
                CsvSchema.CONSTRAINT_TABLE.bodyColumns(), cells);
    }

    /** The alphabet map M2 reads its ε-erasure decisions from, re-anchored to the upstream rules. */
    public StampedTable orderAlphabetMap(String countingRule, List<AlphabetRow> rows) {
        List<List<String>> cells = new ArrayList<>(rows.size());
        for (AlphabetRow row : rows) {
            cells.add(row.cells());
        }
        return new StampedTable("order alphabet map", mopVersion, oracleVersion, countingRule,
                CsvSchema.ORDER_ALPHABET_MAP.bodyColumns(), cells);
    }

    /** The divergence record. */
    public StampedTable divergenceRecord(String countingRule, List<DivergenceRow> rows) {
        List<List<String>> cells = new ArrayList<>(rows.size());
        for (DivergenceRow row : rows) {
            cells.add(row.cells());
        }
        return new StampedTable("divergence record", mopVersion, oracleVersion, countingRule,
                CsvSchema.DIVERGENCE_RECORD.bodyColumns(), cells);
    }

    /**
     * Write a table under its committed file name, and answer where it went.
     *
     * <p>The file name comes from the schema rather than from the caller: the point of matching the
     * committed schemas is that the emitted file can stand in the same place as the manual one, and
     * a caller free to choose the name could put a predicate graph in a file nothing reads.
     */
    public Path write(Path outputDir, CsvSchema schema, StampedTable table) {
        if (!schema.bodyColumns().equals(table.bodyColumns())) {
            throw new IllegalArgumentException("table of columns " + table.bodyColumns()
                    + " does not fit the schema of " + schema.fileName());
        }
        Path target = outputDir.resolve(schema.fileName());
        StampedTable.write(target, table.csv());
        return target;
    }

    /**
     * Refuse a reference to the abandoned {@code api30} corpus.
     *
     * <p>The committed tables cite {@code .cryptsl} files and are the historical read. Anything
     * this component emits cites the upstream {@code .crysl} rules, because that is the oracle it
     * was computed against; a row that carried the old anchor would attribute a fresh measurement
     * to a corpus that did not produce it.
     */
    private static void requireUpstreamAnchor(String reference, String what) {
        if (reference != null && reference.contains(".cryptsl")) {
            throw new IllegalArgumentException(what + " cites a .cryptsl path (" + reference
                    + "); the emitted tables are anchored on the upstream .crysl rules, and the "
                    + "committed api30-anchored files are the historical read, not the format");
        }
    }

    private static String nullToEmpty(String value) {
        return value == null ? "" : value;
    }
}
