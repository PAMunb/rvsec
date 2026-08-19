package br.unb.cic.mop.jca.util;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

import org.junit.Test;

/**
 * The in-code alias table against the registry it is derived from.
 *
 * <p>{@code data/jca_android/alias_table.csv} is what a reviewer reads and what
 * the conformance gate compares against; {@link ConscryptAliasTable} is what a
 * woven monitor executes. Nothing else ties them together, so a row added to one
 * and not the other would go unnoticed and the registry would stop being
 * evidence. That is what this test exists to prevent: it compares the two row
 * for row, in file order, every column included -- the source pointer and the
 * {@code inApi30Allowlist} flag as much as the alias itself.
 */
public class ConscryptAliasTableTest {

    private static final String REGISTRY = "rv-android/data/jca_android/alias_table.csv";

    // --- the class equals the registry ---

    @Test
    public void inCodeTableEqualsTheRegistryRowForRow() throws IOException {
        List<String[]> registry = readRegistry();
        List<String[]> code = ConscryptAliasTable.rows();

        assertEquals("row count", registry.size(), code.size());
        for (int i = 0; i < registry.size(); i++) {
            assertEquals("row " + (i + 1) + " of " + REGISTRY,
                    Arrays.toString(registry.get(i)), Arrays.toString(code.get(i)));
        }
    }

    @Test
    public void tableHasTheOneHundredAndFiftyEightExtractedRows() throws IOException {
        assertEquals(158, readRegistry().size());
        assertEquals(158, ConscryptAliasTable.rows().size());
    }

    // --- the corrected pointers of the two rows the pivot brief got wrong ---

    @Test
    public void carriesTheCorrectedSourcePointers() {
        assertEquals("90", lineOf("TrustManagerFactory", "X509"));
        assertEquals("115", lineOf("MessageDigest", "SHA1"));
        assertEquals("116", lineOf("MessageDigest", "SHA"));
    }

    // --- resolution ---

    @Test
    public void resolvesAnAliasToTheNameTheRuleWrites() {
        assertEquals("PKIX", ConscryptAliasTable.canonical("TrustManagerFactory", "X509"));
        assertEquals("SHA-1", ConscryptAliasTable.canonical("MessageDigest", "SHA1"));
        assertEquals("SHA-1", ConscryptAliasTable.canonical("MessageDigest", "SHA"));
        assertEquals("SHA-256", ConscryptAliasTable.canonical("MessageDigest", "SHA256"));
    }

    @Test
    public void leavesAValueNoRowExplainsUntouched() {
        assertEquals("SunX509", ConscryptAliasTable.canonical("TrustManagerFactory", "SunX509"));
        assertEquals("Whatever", ConscryptAliasTable.canonical("NoSuchService", "Whatever"));
    }

    @Test
    public void anAliasMakesTheTranscribedListMatch() {
        List<String> trustManagerFactory = Arrays.asList("PKIX");
        assertTrue(ConscryptAliasTable.matches("TrustManagerFactory", "X509", trustManagerFactory));
        assertTrue(ConscryptAliasTable.matches("TrustManagerFactory", "PKIX", trustManagerFactory));
        assertFalse(ConscryptAliasTable.matches("TrustManagerFactory", "SunX509", trustManagerFactory));
    }

    @Test
    public void caseAloneIsNotAMisuse() {
        List<String> signature = Arrays.asList("SHA256withRSA");
        assertTrue(ConscryptAliasTable.matches("Signature", "SHA256WITHRSA", signature));
        assertTrue(ConscryptAliasTable.matches("Signature", "sha256withrsa", signature));
    }

    @Test
    public void resolutionIgnoresTheAllowlistFlag() {
        // The flag is a property of the record, not an input to resolution: a row
        // flagged `no` still resolves when the list happens to carry its canonical.
        assertTrue(ConscryptAliasTable.matches("Cipher", "RSA/None/NoPadding",
                Arrays.asList("RSA/ECB/NoPadding")));
    }

    // --- helpers ---

    private static String lineOf(String service, String alias) {
        for (String[] row : ConscryptAliasTable.rows()) {
            if (row[0].equals(service) && row[1].equals(alias)) {
                return row[3];
            }
        }
        throw new AssertionError("no row " + service + "." + alias);
    }

    private static List<String[]> readRegistry() throws IOException {
        File file = locate();
        List<String[]> rows = new ArrayList<>();
        List<String> lines = Files.readAllLines(file.toPath(), StandardCharsets.UTF_8);
        for (int i = 1; i < lines.size(); i++) {
            String line = lines.get(i).trim();
            if (line.isEmpty()) {
                continue;
            }
            String[] cells = line.split(",", -1);
            assertEquals("five columns on line " + (i + 1) + " of " + REGISTRY, 5, cells.length);
            rows.add(cells);
        }
        return rows;
    }

    /**
     * The registry lives in the sibling rv-android tree, so the test walks up from
     * the module directory until it finds it rather than assuming a depth.
     */
    private static File locate() {
        File dir = new File(System.getProperty("user.dir")).getAbsoluteFile();
        while (dir != null) {
            File candidate = new File(dir, REGISTRY);
            if (candidate.isFile()) {
                return candidate;
            }
            dir = dir.getParentFile();
        }
        throw new AssertionError("could not find " + REGISTRY + " above " + System.getProperty("user.dir"));
    }
}
