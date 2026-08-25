package br.unb.cic.rvsec.crysl.core.compare;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * {@code data/jca_android/order_alphabet_map.csv}, read for the one column M2 is not allowed to
 * decide for itself.
 *
 * <p>The map associates a {@code .mop} event with the {@code ORDER} symbol it stands for, and where
 * there is no such symbol its {@code disposition} column says so, per row, with a written reason and
 * a rule line. M2 takes every &epsilon;-erasure decision from that column and from nowhere else
 * (INV-CONF-10, design D-05). The alternative - inferring erasure from the shape of the automaton,
 * typically from a self-loop - is not merely unreviewed, it is <em>insufficient</em>: it does not
 * license erasing {@code KeyGeneratorSpec.g3}, which loops only at the initial state. What licenses
 * that erasure is N1, valid there by the decidable {@code MapOfMonitor} criterion, and no automaton
 * shape can see it. So the shape criterion survives as a check and never as a source, and this class
 * is the source.
 *
 * <p>An event with no row at all is not an erasure and not a mapping: it is a gap in a hand-written
 * artifact, and M2 emits a typed refusal for it rather than choosing (task 10.4). An erasure the
 * comparator invents is a decision nobody reviewed; an erasure the map declares has an owner, a
 * written reason and provenance, and M2's job is to check it.
 *
 * <p>The file is read strictly read-only (INV-CONF-12). Its {@code rule}/{@code rule_line} columns
 * are still anchored to the abandoned {@code api30} generation and cite {@code .cryptsl} files; that
 * anchoring is carried through verbatim rather than rewritten, because rewriting a committed
 * artifact to agree with a newer oracle is exactly the move INV-CONF-14 forbids. Where the
 * anchoring matters to a verdict, it is a finding to report.
 *
 * @param source the path the rows were read from, for the report header
 * @param rows   every data row, grouped by specification, in file order
 */
public record AlphabetMap(String source, Map<String, List<Row>> rows) {

    /** The header line the reader anchors the column positions to. */
    public static final String HEADER =
            "spec,mop_event,order_symbol,symbol_kind,rule,rule_line,disposition,reason";

    /** The counting rule behind every erasure decision this map licenses (INV-CONF-02). */
    public static final String COUNTING_RULE =
            "R-ORDER-MAP: one row per (.mop event -> ORDER symbol) association. An event is erased "
                    + "to epsilon when it has at least one row and every row it has carries "
                    + "disposition = order-unmapped; it is mapped when some row carries "
                    + "disposition = mapped; and it is a refusal when it has no row at all. "
                    + "Erasure is never inferred from automaton shape (INV-CONF-10).";

    /** What the {@code disposition} column declares about one row. */
    public enum Disposition {
        /** The event stands for the named {@code ORDER} symbol. */
        MAPPED("mapped"),
        /** The event has no {@code ORDER} counterpart, for the reason the row carries. */
        ORDER_UNMAPPED("order-unmapped");

        private final String csv;

        Disposition(String csv) {
            this.csv = csv;
        }

        /** The token as the committed file spells it. */
        public String csv() {
            return csv;
        }

        static Disposition of(String token) {
            for (Disposition disposition : values()) {
                if (disposition.csv.equals(token)) {
                    return disposition;
                }
            }
            throw new IllegalArgumentException("order_alphabet_map.csv declares the disposition '"
                    + token + "', which is not one this component knows. The column is closed to "
                    + MAPPED.csv + " and " + ORDER_UNMAPPED.csv + "; a third value is a schema "
                    + "change and has to be read by a human before a verdict rests on it");
        }
    }

    /**
     * One declared association.
     *
     * @param specification the {@code .mop} specification, as the corpus names it
     * @param mopEvent      the event label
     * @param orderSymbol   the rule symbol it stands for, empty when the disposition is unmapped
     * @param symbolKind    {@code event} or {@code aggregate}, empty when unmapped
     * @param rule          the rule the row cites, still spelled as the historical {@code .cryptsl}
     * @param ruleLine      the line of the rule the row cites, empty when unmapped
     * @param disposition   what the row declares
     * @param reason        the written justification, quoted verbatim into the verdict (task 10.5)
     */
    public record Row(String specification, String mopEvent, String orderSymbol, String symbolKind,
                      String rule, String ruleLine, Disposition disposition, String reason) {

        public Row {
            Objects.requireNonNull(specification, "Row.specification is mandatory");
            Objects.requireNonNull(mopEvent, "Row.mopEvent is mandatory");
            Objects.requireNonNull(disposition, "Row.disposition is mandatory");
            Objects.requireNonNull(reason, "Row.reason is mandatory (use the empty string)");
        }

        /** True when this row declares the event has no {@code ORDER} symbol. */
        public boolean unmapped() {
            return disposition == Disposition.ORDER_UNMAPPED;
        }
    }

    public AlphabetMap {
        Objects.requireNonNull(source, "AlphabetMap.source is mandatory");
        Map<String, List<Row>> copy = new LinkedHashMap<>();
        rows.forEach((specification, list) -> copy.put(specification, List.copyOf(list)));
        rows = Map.copyOf(copy);
    }

    /**
     * Reads the committed map.
     *
     * <p>Comment lines - everything from {@code #} to the end of the line, at the start of a line -
     * carry the declared G-ORDER skips as prose and never as data rows, deliberately: a row for a
     * skipped specification, even an empty one, would take the file out of the skip. They are
     * skipped here for the same reason they were written that way.
     *
     * @param csv the map, read and never written (INV-CONF-12)
     */
    public static AlphabetMap read(Path csv) throws IOException {
        List<String> lines = Files.readAllLines(csv, StandardCharsets.UTF_8);
        Map<String, List<Row>> rows = new LinkedHashMap<>();
        boolean sawHeader = false;
        for (String line : lines) {
            if (line.isBlank() || line.startsWith("#")) {
                continue;
            }
            if (!sawHeader) {
                if (!line.trim().equals(HEADER)) {
                    throw new IOException("order_alphabet_map.csv does not carry the header this "
                            + "reader is anchored to.\n  expected: " + HEADER + "\n  found:    "
                            + line.trim());
                }
                sawHeader = true;
                continue;
            }
            List<String> fields = split(line);
            if (fields.size() < 7) {
                throw new IOException("order_alphabet_map.csv row has " + fields.size()
                        + " fields, and the schema declares 8: " + line);
            }
            Row row = new Row(fields.get(0), fields.get(1), fields.get(2), fields.get(3),
                    fields.get(4), fields.get(5), Disposition.of(fields.get(6)),
                    fields.size() > 7 ? fields.get(7) : "");
            rows.computeIfAbsent(row.specification(), key -> new ArrayList<>()).add(row);
        }
        if (!sawHeader) {
            throw new IOException("order_alphabet_map.csv carries no header line: " + csv);
        }
        return new AlphabetMap(csv.toAbsolutePath().toString(), rows);
    }

    /** Every row of one specification, in file order; empty when the map declares none. */
    public List<Row> rowsOf(String specification) {
        return rows.getOrDefault(specification, List.of());
    }

    /**
     * Every row of one event of one specification.
     *
     * <p>A list rather than an optional because the map is not a bijection on purpose:
     * {@code KeyGeneratorSpec.init} is one event over two rule symbols ({@code i1} and {@code i3}),
     * and collapsing the two rows would lose the aggregate the row pair states.
     */
    public List<Row> rowsOf(String specification, String mopEvent) {
        return rowsOf(specification).stream().filter(row -> row.mopEvent().equals(mopEvent)).toList();
    }

    /** Whether the map says anything at all about this event. */
    public boolean declares(String specification, String mopEvent) {
        return !rowsOf(specification, mopEvent).isEmpty();
    }

    /**
     * Whether the map declares this event erased to &epsilon;.
     *
     * <p>Every row of the event has to say so. An event with one {@code mapped} row and one
     * {@code order-unmapped} row stands for a symbol on the mapped row's authority, and erasing it
     * would delete a letter the map says the rule has.
     */
    public boolean erases(String specification, String mopEvent) {
        List<Row> found = rowsOf(specification, mopEvent);
        return !found.isEmpty() && found.stream().allMatch(Row::unmapped);
    }

    /**
     * Whether the map renames this event across the two sides - the row's {@code order_symbol}
     * differs from the {@code .mop} label.
     *
     * <p>The corpus's own examples are {@code SecureRandomSpec.g3 -> gI} and
     * {@code SecureRandomSpec.setSeed1 -> s2}: no name heuristic gets either right, which is why the
     * association is a table and not an inference.
     */
    public boolean renames(String specification, String mopEvent) {
        return rowsOf(specification, mopEvent).stream()
                .anyMatch(row -> !row.unmapped() && !row.orderSymbol().equals(mopEvent));
    }

    /** Splits one CSV line, honouring double-quoted fields with embedded commas and {@code ""}. */
    private static List<String> split(String line) {
        List<String> fields = new ArrayList<>();
        StringBuilder current = new StringBuilder();
        boolean quoted = false;
        for (int i = 0; i < line.length(); i++) {
            char c = line.charAt(i);
            if (quoted) {
                if (c == '"') {
                    if (i + 1 < line.length() && line.charAt(i + 1) == '"') {
                        current.append('"');
                        i++;
                    } else {
                        quoted = false;
                    }
                } else {
                    current.append(c);
                }
            } else if (c == '"') {
                quoted = true;
            } else if (c == ',') {
                fields.add(current.toString());
                current.setLength(0);
            } else {
                current.append(c);
            }
        }
        fields.add(current.toString());
        return fields;
    }
}
