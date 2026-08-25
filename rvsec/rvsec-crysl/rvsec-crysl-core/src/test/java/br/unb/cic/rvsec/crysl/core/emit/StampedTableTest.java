package br.unb.cic.rvsec.crysl.core.emit;

import static org.junit.jupiter.api.Assertions.assertAll;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.unb.cic.rvsec.crysl.core.model.SourceStamp;
import br.unb.cic.rvsec.crysl.core.model.Version;
import java.time.Instant;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * INV-CONF-02 at the choke point: a table that does not say how it counted does not become text.
 */
class StampedTableTest {

    private static final List<String> COLUMNS = List.of("spec", "count");
    private static final List<List<String>> ROWS = List.of(List.of("CipherSpec", "7"));

    private static StampedTable tableWith(String countingRule) {
        return new StampedTable("m1", Fixtures.MOP, Fixtures.ORACLE, countingRule, COLUMNS, ROWS);
    }

    @Test
    @DisplayName("INV-CONF-02: a table constructed without a counting rule cannot be rendered")
    void test_inv_conf_02_table_carries_rule() {
        // Refused at construction rather than at render: an object that exists only when it is
        // renderable leaves no window in which an unstamped table can be handed around.
        assertAll(
                () -> assertThrows(IllegalArgumentException.class, () -> tableWith(null)),
                () -> assertThrows(IllegalArgumentException.class, () -> tableWith("")),
                () -> assertThrows(IllegalArgumentException.class, () -> tableWith("   ")));
    }

    @Test
    @DisplayName("INV-CONF-02: the counting rule lands in every CSV row and in the Markdown header")
    void test_inv_conf_02_rule_travels_with_the_numbers() {
        StampedTable table = tableWith("R1: one row per ORDER clause");

        String csv = table.csv();
        String markdown = table.markdown(List.of());

        assertAll(
                () -> assertTrue(csv.lines().skip(1)
                        .allMatch(line -> line.contains("R1: one row per ORDER clause")),
                        "every data row carries the rule, not just a header comment"),
                () -> assertTrue(markdown.contains("- **counting rule** R1:")));
    }

    @Test
    @DisplayName("D-17: both stamps travel, and in a fixed position")
    void test_both_stamps_in_a_fixed_position() {
        StampedTable table = tableWith("R1");

        List<String> header = List.of(table.csv().lines().findFirst().orElseThrow().split(","));
        String markdown = table.markdown(List.of());

        assertAll(
                () -> assertEquals(List.of("spec", "count"), header.subList(0, 2)),
                () -> assertEquals(StampedTable.STAMP_COLUMNS, header.subList(2, header.size()),
                        "the stamp is the trailing columns, always the same ones in the same order"),
                () -> assertEquals("rvsec", table.stamp().get("mop_repository")),
                () -> assertEquals("rvsec-cognicrypt", table.stamp().get("oracle_repository")),
                () -> assertTrue(markdown.startsWith("# m1\n\n- **mop** "),
                        "the stamp block sits directly under the H1"));
    }

    @Test
    @DisplayName("INV-CONF-01: a placeholder stamp is an absent stamp")
    void test_inv_conf_01_placeholder_stamp_refused() {
        Version placeholder = new Version("jca_android",
                new SourceStamp("rvsec", "unknown", Instant.parse("2026-08-24T10:00:00Z")));

        assertThrows(MissingVersionError.class, () -> new StampedTable(
                "m1", placeholder, Fixtures.ORACLE, "R1", COLUMNS, ROWS));
    }

    @Test
    @DisplayName("a cell carrying a comma or a quote is escaped, not silently split")
    void test_csv_escaping() {
        StampedTable table = new StampedTable("m1", Fixtures.MOP, Fixtures.ORACLE, "R1",
                List.of("reason"), List.of(List.of("alg in {\"AES\", \"DES\"}")));

        assertTrue(table.csv().contains("\"alg in {\"\"AES\"\", \"\"DES\"\"}\""));
    }
}
