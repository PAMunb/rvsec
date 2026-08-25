package br.unb.cic.rvsec.crysl.core.emit;

import java.util.ArrayList;
import java.util.List;

/**
 * The four CSV schemas the component emits, declared column for column against the files already
 * committed under {@code data/jca_android/}.
 *
 * <p>The component substitutes the manual tables; it does not open a parallel island beside them.
 * That is only true if the emitted file is the same file: same columns, same names, same order. So
 * the committed header is transcribed here as data, and {@code CommittedSchemaDriftTest} reads the
 * real headers off disk at build time and fails when the two disagree. A schema drift is then a red
 * build rather than a second dialect nobody notices until two tables stop being comparable.
 *
 * <p>The committed column names are Portuguese-and-English as the files have them, and they are not
 * translated: a schema is an interface with the readers under {@code scripts/}, and renaming a
 * column to read better breaks every one of them.
 *
 * <p>{@link #extensions()} are columns the emitter adds after the committed ones, each with the
 * reason it exists. Appending is the only extension shape a {@code csv.DictReader} survives, and
 * every extension is checked to be a genuine addition rather than a rename of a committed column.
 */
public enum CsvSchema {

    /**
     * The predicate graph, one row per predicate site. This is the M4 table.
     *
     * <p>It carries two vocabularies at once, and neither substitutes the other. {@code verdict}
     * and {@code disposition} are about a <em>site</em> - where in the specification the predicate
     * is read or written, and what was decided about that site. {@code fidelity} is about a
     * <em>clause</em> - how faithfully the specification implements the rule clause the site comes
     * from. There is no bijection between sites and clauses: one clause is implemented at several
     * sites, and one site translates a composite of clauses. Emitting one column in place of the
     * other would replace a manual table with an automatic table that measures something else.
     */
    PREDICATE_GRAPH("predicate_graph.csv",
            List.of("file", "event", "site_kind", "polarity", "guard", "arity", "predicate",
                    "position_types", "splitter", "clause", "mechanism", "verdict", "disposition",
                    "reason", "automaton_membership"),
            List.of(
                    new Extension("fidelity",
                            "the clause-level fidelity class (FIEL, PROJETADO, CONFLADO, AUSENTE); "
                                    + "the committed schema carries only the site-level verdict and "
                                    + "disposition, which describe a different object"),
                    new Extension("origin",
                            "derived or inherited (INV-CONF-15); the fidelity class is human "
                                    + "judgement wherever it is inherited, and a reader must be "
                                    + "able to compute the derived fraction of any aggregate "
                                    + "instead of taking the whole table on trust"))),

    /** The clause-by-clause constraint comparison. This is the M3 table. */
    CONSTRAINT_TABLE("constraint_table.csv",
            List.of("spec", "cryptsl_line", "mop_line", "verdict"),
            List.of()),

    /**
     * The event-alphabet mapping M2 takes its ε-erasure decisions from (INV-CONF-10).
     *
     * <p>The committed file is anchored on {@code .cryptsl} paths, because it was produced against
     * the abandoned {@code api30} corpus. That file stays readable as the historical input; the
     * component, as the map's new producer, re-anchors {@code rule_line} to the upstream
     * {@code .crysl} rules. The column name {@code cryptsl_line} in the constraint table above is
     * left alone for the same reason the others are: it is a schema, not a claim about the oracle.
     */
    ORDER_ALPHABET_MAP("order_alphabet_map.csv",
            List.of("spec", "mop_event", "order_symbol", "symbol_kind", "rule", "rule_line",
                    "disposition", "reason"),
            List.of()),

    /** The record of every departure from the rule, with the reason and the task that owns it. */
    DIVERGENCE_RECORD("divergence_record.csv",
            List.of("file", "hunk", "kind", "summary", "reason", "task"),
            List.of());

    /**
     * The caveat INV-CONF-15 requires beside every M4 aggregate.
     *
     * <p>It is a constant rather than a sentence each emitter writes for itself because a caveat
     * that has to be remembered is a caveat that will be dropped from exactly the table that most
     * needs it. Both the CSV emitter and the Markdown emitter append it to the counting rule of
     * every M4 table, so it travels in the same column as the number it qualifies.
     */
    public static final String M4_JUDGEMENT_CAVEAT =
            "INV-CONF-15: the FIEL/PROJETADO/CONFLADO/AUSENTE classification is human judgement "
                    + "wherever the row's origin is 'inherited'; the derived fraction is "
                    + "computable from the origin column and is not asserted by this table";

    /**
     * One column this component adds after the committed ones.
     *
     * @param column the column name
     * @param reason why the committed schema is not enough without it
     */
    public record Extension(String column, String reason) {
    }

    private final String fileName;
    private final List<String> committedColumns;
    private final List<Extension> extensions;

    CsvSchema(String fileName, List<String> committedColumns, List<Extension> extensions) {
        this.fileName = fileName;
        this.committedColumns = List.copyOf(committedColumns);
        this.extensions = List.copyOf(extensions);
    }

    /** The name of the committed file this schema is transcribed from. */
    public String fileName() {
        return fileName;
    }

    /** The header of the committed file, column for column and in order. */
    public List<String> committedColumns() {
        return committedColumns;
    }

    /** The columns this component adds after the committed ones, with their reasons. */
    public List<Extension> extensions() {
        return extensions;
    }

    /** The body columns of the emitted table: the committed header followed by the extensions. */
    public List<String> bodyColumns() {
        List<String> columns = new ArrayList<>(committedColumns);
        for (Extension extension : extensions) {
            columns.add(extension.column());
        }
        return List.copyOf(columns);
    }
}
