package br.unb.cic.rvsec.crysl.core.emit;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Properties;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * The build-time schema check: {@link CsvSchema} against the four committed files.
 *
 * <p>This is the mechanism behind the claim that the component <em>substitutes</em> the manual
 * tables. It only substitutes them if the emitted file is the same file - same column names, same
 * order, no additions folded into the middle. Transcribing the header into Java and never checking
 * it would produce a second dialect the moment either side moved, and the two tables would stop
 * being comparable without anybody being told.
 *
 * <p>A missing input directory fails this test rather than skipping it. A schema check that can
 * silently not run is a green with nothing behind it, which is the exact failure mode this whole
 * task group exists to prevent.
 */
class CommittedSchemaDriftTest {

    private static Path schemasDir;

    @BeforeAll
    static void resolveSchemasDir() throws IOException {
        Properties properties = new Properties();
        try (InputStream in = CommittedSchemaDriftTest.class.getClassLoader()
                .getResourceAsStream("committed-schemas.properties")) {
            assertTrue(in != null, "committed-schemas.properties is not on the test classpath; "
                    + "the resource filtering that resolves the committed schema directory is not "
                    + "wired, so the schema check would not be running at all");
            properties.load(in);
        }
        String configured = properties.getProperty("committed.schemas.dir");
        assertFalse(configured == null || configured.isBlank() || configured.startsWith("${"),
                "committed.schemas.dir was not interpolated by the build: " + configured);
        schemasDir = Path.of(configured).normalize();
        assertTrue(Files.isDirectory(schemasDir),
                "the committed schemas are not where the build says they are: " + schemasDir);
    }

    /**
     * The header of a committed file: the first line that is neither blank nor a {@code #} comment.
     *
     * <p>{@code order_alphabet_map.csv} carries a prose preamble in {@code #} lines, and its own
     * reader under {@code scripts/} drops them the same way.
     */
    private static List<String> committedHeader(String fileName) {
        Path file = schemasDir.resolve(fileName);
        assertTrue(Files.isRegularFile(file), "committed schema missing: " + file);
        try {
            for (String line : Files.readAllLines(file, StandardCharsets.UTF_8)) {
                if (line.isBlank() || line.startsWith("#")) {
                    continue;
                }
                return List.of(line.split(",", -1));
            }
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
        throw new AssertionError("committed schema has no header row: " + file);
    }

    @Test
    @DisplayName("CsvSchema transcribes the four committed headers column for column")
    void test_committed_headers_match() {
        for (CsvSchema schema : CsvSchema.values()) {
            assertEquals(committedHeader(schema.fileName()), schema.committedColumns(),
                    "the committed header of " + schema.fileName() + " and the schema this "
                            + "component emits under have drifted apart");
        }
    }

    @Test
    @DisplayName("the emitted header is the committed header plus declared, appended extensions")
    void test_emitted_header_extends_without_renaming() {
        for (CsvSchema schema : CsvSchema.values()) {
            List<String> committed = schema.committedColumns();
            List<String> body = schema.bodyColumns();

            assertEquals(committed, body.subList(0, committed.size()),
                    schema.fileName() + ": the committed columns must come first and unchanged, "
                            + "because csv.DictReader survives an appended column and nothing else");

            List<String> added = new ArrayList<>(body.subList(committed.size(), body.size()));
            for (CsvSchema.Extension extension : schema.extensions()) {
                assertFalse(committed.contains(extension.column()),
                        schema.fileName() + ": '" + extension.column() + "' is declared as an "
                                + "extension and is already a committed column; a rename is not an "
                                + "extension");
                assertFalse(extension.reason().isBlank(),
                        schema.fileName() + ": extension '" + extension.column()
                                + "' carries no reason for existing");
            }
            assertEquals(schema.extensions().size(), added.size());
        }
    }

    @Test
    @DisplayName("the committed files are the historical read: they still cite .cryptsl paths")
    void test_committed_files_are_the_api30_anchored_read() {
        // The map and the constraint table were produced against the abandoned api30 corpus. The
        // component re-anchors what it emits to the upstream .crysl rules; this test records that
        // the committed files are the other thing, so the two are never confused for one format.
        String constraintTable = read("constraint_table.csv");
        assertTrue(constraintTable.contains(".crysl"),
                "constraint_table.csv is expected to cite rule files");

        String alphabetMap = read("order_alphabet_map.csv");
        assertTrue(alphabetMap.contains(".cryptsl"),
                "order_alphabet_map.csv is the api30-anchored historical read; if it stops citing "
                        + ".cryptsl it has been regenerated and this test's premise has changed");
    }

    private static String read(String fileName) {
        try {
            return Files.readString(schemasDir.resolve(fileName), StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }
}
