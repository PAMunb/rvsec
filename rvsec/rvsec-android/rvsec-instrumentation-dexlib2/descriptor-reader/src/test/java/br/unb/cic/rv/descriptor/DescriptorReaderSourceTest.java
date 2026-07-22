package br.unb.cic.rv.descriptor;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Exercises the {@link DescriptorReader} public read overloads that the string-based
 * tests never reach: {@link DescriptorReader#read(java.io.File)},
 * {@link DescriptorReader#read(Path)} and the error branches of
 * {@link DescriptorReader#read(InputStream)}.
 *
 * <p>These file/stream entry points are the ones production actually uses — the DEX
 * weaver hands the reader an on-disk descriptor path (JavaMOP's emitted
 * {@code *MonitorAspect.json}), not an in-memory string. The existing
 * {@code DescriptorReaderTest}/{@code DescriptorReaderNegativeTest} cover the String
 * and (happy-path) InputStream surface only, so every catch block below was dark.
 *
 * <p>WHY each case matters, with concrete values:
 * <ul>
 *   <li>A well-formed descriptor written to a real file and read back through both the
 *       {@code File} and the NIO {@code Path} overload must deserialize identically to the
 *       string path — this is the positive control proving the failure cases below fail
 *       for the right reason (bad content), not because file reading is broken.</li>
 *   <li>A <em>missing</em> file surfaces {@link DescriptorParseError} whose message quotes
 *       the offending path (Jackson throws {@code FileNotFoundException}, an
 *       {@link IOException}, so the {@code "Failed to read descriptor file: <path>"} branch
 *       is taken, not the mapping branch).</li>
 *   <li>A structurally-wrong file ({@code {"monster":1}}, an unknown property) trips
 *       {@code FAIL_ON_UNKNOWN_PROPERTIES}, i.e. the {@code JsonMappingException} branch,
 *       and the error must name both the source file and the offending field.</li>
 *   <li>The {@code InputStream} overload has the same two error branches; a malformed-JSON
 *       stream ({@code "{ nope"}) hits the {@code IOException}/{@code JsonParseException}
 *       branch and an unknown-property stream hits the mapping branch.</li>
 *   <li>A root-level type mismatch ({@code "42"} — an int where the aspect object is
 *       expected) yields a {@code JsonMappingException} with an <em>empty</em> path
 *       reference, exercising the {@code pointer == null || pointer.isEmpty()} arm of
 *       {@code formatMappingError} that the field-level type-mismatch test never takes.</li>
 * </ul>
 */
class DescriptorReaderSourceTest {

    /** Minimal but non-trivial descriptor: proves content survives a file/Path round-trip. */
    private static final String VALID_DESCRIPTOR = "{"
            + "\"aspectName\":\"MultiSpec_1MonitorAspect\","
            + "\"shortName\":\"MultiSpec_1\","
            + "\"imports\":[\"javax.crypto.Cipher\"]"
            + "}";

    @Test
    void readsFromFileAndPath(@TempDir Path tmp) throws IOException {
        Path file = tmp.resolve("descriptor.json");
        Files.writeString(file, VALID_DESCRIPTOR, StandardCharsets.UTF_8);

        // File overload.
        AspectDescriptor fromFile = DescriptorReader.read(file.toFile());
        assertEquals("MultiSpec_1MonitorAspect", fromFile.getAspectName());
        assertEquals(1, fromFile.getImports().size());
        assertEquals("javax.crypto.Cipher", fromFile.getImports().get(0));

        // Path overload delegates to File; must yield an equivalent tree.
        AspectDescriptor fromPath = DescriptorReader.read(file);
        assertEquals("MultiSpec_1MonitorAspect", fromPath.getAspectName());
        assertEquals("MultiSpec_1", fromPath.getShortName());
    }

    @Test
    void missingFileReportsIoErrorWithPath(@TempDir Path tmp) {
        Path absent = tmp.resolve("does-not-exist.json");

        DescriptorParseError e = assertThrows(DescriptorParseError.class,
                () -> DescriptorReader.read(absent.toFile()));
        // The IOException branch prefixes "Failed to read descriptor file: <file>".
        assertTrue(e.getMessage().contains("Failed to read descriptor file"),
                "missing-file error should use the IOException branch; got: " + e.getMessage());
        assertTrue(e.getMessage().contains("does-not-exist.json"),
                "error should quote the missing path; got: " + e.getMessage());
    }

    @Test
    void unknownPropertyInFileCitesFileAndField(@TempDir Path tmp) throws IOException {
        Path file = tmp.resolve("bad-schema.json");
        Files.writeString(file, "{\"monster\":1}", StandardCharsets.UTF_8);

        DescriptorParseError e = assertThrows(DescriptorParseError.class,
                () -> DescriptorReader.read(file.toFile()));
        // JsonMappingException branch: formatMappingError(source = file path).
        assertTrue(e.getMessage().contains("bad-schema.json"),
                "mapping error should name the source file; got: " + e.getMessage());
        assertTrue(e.getMessage().contains("monster"),
                "mapping error should cite the unknown field; got: " + e.getMessage());
    }

    @Test
    void malformedStreamReportsParseError() {
        // JsonParseException extends IOException -> read(InputStream) IOException branch.
        InputStream in = new ByteArrayInputStream("{ nope".getBytes(StandardCharsets.UTF_8));
        DescriptorParseError e = assertThrows(DescriptorParseError.class,
                () -> DescriptorReader.read(in));
        assertTrue(e.getMessage().contains("input stream"),
                "stream IO error should name the input-stream source; got: " + e.getMessage());
    }

    @Test
    void unknownPropertyInStreamCitesStreamSource() {
        InputStream in = new ByteArrayInputStream(
                "{\"monster\":1}".getBytes(StandardCharsets.UTF_8));
        DescriptorParseError e = assertThrows(DescriptorParseError.class,
                () -> DescriptorReader.read(in));
        // JsonMappingException branch of the stream overload: source == "<input stream>".
        assertTrue(e.getMessage().contains("input stream"),
                "stream mapping error should name the input-stream source; got: " + e.getMessage());
        assertTrue(e.getMessage().contains("monster"),
                "stream mapping error should cite the unknown field; got: " + e.getMessage());
    }

    @Test
    void streamHappyPathIsThePositiveControl() {
        // Positive control: the same overload accepts a well-formed stream, so the two
        // failing stream cases above fail on content, not on stream handling.
        InputStream in = new ByteArrayInputStream(
                VALID_DESCRIPTOR.getBytes(StandardCharsets.UTF_8));
        AspectDescriptor desc = DescriptorReader.read(in);
        assertNotNull(desc);
        assertEquals("MultiSpec_1MonitorAspect", desc.getAspectName());
    }

    @Test
    void rootTypeMismatchFormatsErrorWithoutPath() {
        // "42" is valid JSON but an int where the aspect OBJECT is expected: Jackson
        // raises a JsonMappingException whose path reference is empty, so
        // formatMappingError takes the "(no path)" arm the field-level mismatch test
        // (advices:42) never reaches. The message therefore omits " at path ...".
        DescriptorParseError e = assertThrows(DescriptorParseError.class,
                () -> DescriptorReader.read("42"));
        assertTrue(e.getMessage().contains("Failed to parse descriptor"),
                "root mismatch should still produce a parse-descriptor error; got: " + e.getMessage());
        assertTrue(!e.getMessage().contains(" at path "),
                "empty-pointer error must omit the ' at path ' suffix; got: " + e.getMessage());
    }
}
