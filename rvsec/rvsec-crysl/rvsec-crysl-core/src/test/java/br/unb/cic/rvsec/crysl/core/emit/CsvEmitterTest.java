package br.unb.cic.rvsec.crysl.core.emit;

import static org.junit.jupiter.api.Assertions.assertAll;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.unb.cic.rvsec.crysl.core.emit.CsvEmitter.AlphabetRow;
import br.unb.cic.rvsec.crysl.core.emit.CsvEmitter.ConstraintRow;
import br.unb.cic.rvsec.crysl.core.emit.CsvEmitter.DivergenceRow;
import br.unb.cic.rvsec.crysl.core.emit.CsvEmitter.Fidelity;
import br.unb.cic.rvsec.crysl.core.emit.CsvEmitter.M4Row;
import br.unb.cic.rvsec.crysl.core.emit.CsvEmitter.Origin;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/** The CSV side: the committed schemas, the two M4 vocabularies, and the round-trip fixture. */
class CsvEmitterTest {

    private static final CsvEmitter EMITTER = new CsvEmitter(Fixtures.MOP, Fixtures.ORACLE);

    private static final List<M4Row> M4_ROWS = List.of(
            new M4Row("CipherSpec.mop", "i2", "body", "positive", "", "2", "GENERATED_KEY",
                    "Key|", "", "Cipher.crysl:174 generatedKey[key, part(0,\"/\",transformation)]",
                    "store", "read:body", "", "the splitter lives in CipherTransformationUtil.alg",
                    "member", Fidelity.CONFLADO, Origin.DERIVED),
            new M4Row("KeyStoreSpec.mop", "gk1", "match", "positive", "", "1",
                    "GENERATED_PUBLIC_KEY", "Key", "", "KeyStore.crysl:41 generatedPubkey[key]",
                    "store", "read:match", "", "", "member", Fidelity.FIEL, Origin.INHERITED));

    private static final List<ConstraintRow> CONSTRAINT_ROWS = List.of(
            new ConstraintRow("CipherInputStreamSpec", "CipherInputStream.crysl:26", "",
                    "CRYSL-NAO-IMPLEMENTADO"));

    private static final List<AlphabetRow> ALPHABET_ROWS = List.of(
            new AlphabetRow("CipherSpec", "i2", "Inits", "aggregated", "Cipher",
                    "Cipher.crysl:31", "mapped", "one event over six init overloads"));

    private static final List<DivergenceRow> DIVERGENCE_ROWS = List.of(
            new DivergenceRow("jca_android/KeyPairGeneratorSpec.mop", "", "api30-omits",
                    "EC is kept in the allow-list", "closed by D-15", "2.6;11.5"));

    @Test
    @DisplayName("the four tables go out under the committed headers, plus the stamp columns")
    void test_headers_are_the_committed_schemas() {
        assertAll(
                () -> assertHeader(CsvSchema.PREDICATE_GRAPH,
                        EMITTER.predicateGraph("R4", M4_ROWS)),
                () -> assertHeader(CsvSchema.CONSTRAINT_TABLE,
                        EMITTER.constraintTable("R1", CONSTRAINT_ROWS)),
                () -> assertHeader(CsvSchema.ORDER_ALPHABET_MAP,
                        EMITTER.orderAlphabetMap("R2", ALPHABET_ROWS)),
                () -> assertHeader(CsvSchema.DIVERGENCE_RECORD,
                        EMITTER.divergenceRecord("R5", DIVERGENCE_ROWS)));
    }

    private static void assertHeader(CsvSchema schema, StampedTable table) {
        List<String> emitted = List.of(table.csv().lines().findFirst().orElseThrow().split(",", -1));
        List<String> expected = new java.util.ArrayList<>(schema.bodyColumns());
        expected.addAll(StampedTable.STAMP_COLUMNS);
        assertEquals(expected, emitted, schema.fileName());
    }

    @Test
    @DisplayName("the M4 table emits the site vocabulary and the clause vocabulary side by side")
    void test_m4_carries_both_vocabularies() {
        StampedTable table = EMITTER.predicateGraph("R4", M4_ROWS);
        List<String> columns = table.bodyColumns();

        // verdict/disposition are about the site; fidelity is about the clause behind it. They are
        // not two names for one measurement, so neither substitutes the other.
        assertAll(
                () -> assertTrue(columns.containsAll(List.of("verdict", "disposition"))),
                () -> assertTrue(columns.contains("fidelity")),
                () -> assertTrue(table.csv().contains("read:body")),
                () -> assertTrue(table.csv().contains("CONFLADO")));
    }

    @Test
    @DisplayName("INV-CONF-15: every M4 row carries its origin and every M4 table the caveat")
    void test_inv_conf_15_origin_and_caveat() {
        StampedTable table = EMITTER.predicateGraph("R4", M4_ROWS);
        List<String> dataLines = table.csv().lines().skip(1).toList();

        assertAll(
                () -> assertTrue(dataLines.get(0).contains("derived")),
                () -> assertTrue(dataLines.get(1).contains("inherited")),
                () -> assertTrue(table.countingRule().startsWith("R4 | INV-CONF-15"),
                        "the caveat is appended by the emitter, not left to the caller"),
                () -> assertTrue(dataLines.stream()
                        .allMatch(line -> line.contains("INV-CONF-15")),
                        "the caveat travels in the same cell as the rule it qualifies"));
    }

    @Test
    @DisplayName("a row anchored on the abandoned .cryptsl corpus is refused, not passed through")
    void test_rows_are_re_anchored_to_the_upstream_rules() {
        assertAll(
                () -> assertThrows(IllegalArgumentException.class,
                        () -> new ConstraintRow("CipherSpec", "Cipher.cryptsl:26", "", "OK")),
                () -> assertThrows(IllegalArgumentException.class,
                        () -> new AlphabetRow("CipherSpec", "i2", "Inits", "aggregated", "Cipher",
                                "generated/api30/Cipher.cryptsl:31", "mapped", "")));
    }

    @Test
    @DisplayName("INV-CONF-02: no CSV table exists without a counting rule")
    void test_inv_conf_02_no_table_without_a_rule() {
        assertThrows(IllegalArgumentException.class, () -> EMITTER.predicateGraph("", M4_ROWS));
    }

    @Test
    @DisplayName("the four files land under their committed names, for the Python readers to parse")
    void test_emits_the_round_trip_fixture() {
        // Written under target/ rather than to a temp directory because task 4.10 re-reads these
        // exact files with the readers under scripts/: the round-trip is only evidence if the
        // artifact it checks is the one the build produced.
        Path outputDir = Path.of("target", "emitted-csv");
        EMITTER.write(outputDir, CsvSchema.PREDICATE_GRAPH, EMITTER.predicateGraph("R4", M4_ROWS));
        EMITTER.write(outputDir, CsvSchema.CONSTRAINT_TABLE,
                EMITTER.constraintTable("R1", CONSTRAINT_ROWS));
        EMITTER.write(outputDir, CsvSchema.ORDER_ALPHABET_MAP,
                EMITTER.orderAlphabetMap("R2", ALPHABET_ROWS));
        EMITTER.write(outputDir, CsvSchema.DIVERGENCE_RECORD,
                EMITTER.divergenceRecord("R5", DIVERGENCE_ROWS));

        for (CsvSchema schema : CsvSchema.values()) {
            Path file = outputDir.resolve(schema.fileName());
            assertTrue(Files.isRegularFile(file), "not written: " + file);
            assertTrue(read(file).startsWith(String.join(",", schema.committedColumns())),
                    schema.fileName() + " must open on the committed header, with no preamble: a "
                            + "leading # line is read as the header row by csv.DictReader");
        }
    }

    private static String read(Path file) {
        try {
            return Files.readString(file, StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }
}
