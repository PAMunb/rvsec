package br.unb.cic.rv.cli;

import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.immutable.ImmutableDexFile;
import com.android.tools.smali.dexlib2.writer.pool.DexPool;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import picocli.CommandLine;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Covers {@code --results-json} on the {@code instrument} subcommand — the
 * production path's only channel for the weaver's counters (INV-INS-105).
 *
 * <p>The failure case runs end to end through
 * {@link BatchRunner#instrumentOne}: a pipeline that fails still has to produce
 * the document, because an absent file must mean the JVM died rather than that
 * the weave went badly. The success case is asserted one level down, against
 * {@link BatchRunner#writeResultsJson}, because driving a genuine success needs
 * a real APK plus javac, d8 and a keystore — fixtures this suite does not carry.
 * What the success case is here to pin is the document shape the Python wrapper
 * parses, not the pipeline that produced it.
 */
class ResultsJsonReportingTest {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    /** Config with nothing resolved — runPipeline reports config_validation. */
    private static EffectiveConfig failingConfig() {
        return new EffectiveConfig(null, null, null, null, List.of(),
                null, null, null, true, null, "INFO");
    }

    @Test
    void instrumentWritesResultsJsonWhenTheWeaveFails(@TempDir Path tmp) throws Exception {
        Path apk = Files.createFile(tmp.resolve("sample.apk"));
        // Deliberately under a directory that does not exist yet: the Python
        // wrapper names one file per APK inside a subdirectory it has not
        // necessarily created, and a successful weave must not be reported as
        // a write failure just because the parent was missing.
        Path out = tmp.resolve("reports").resolve("sample.json");

        BatchRunner.instrumentOne(failingConfig(), apk, out);

        assertTrue(Files.isRegularFile(out),
                "a failed weave must still report its counters and phase");
        JsonNode root = MAPPER.readTree(out.toFile());
        assertEquals("dexlib2", root.get("variant").asText(),
                "variant tag is the Python wrapper's contract");
        assertEquals(1, root.get("results").size(),
                "the single-APK path writes a one-element results array");
        JsonNode entry = root.get("results").get(0);
        assertEquals("sample.apk", entry.get("apkName").asText());
        assertFalse(entry.get("success").asBoolean());
        assertTrue(entry.hasNonNull("phase"), "phase pinpoints how far the pipeline got");
        assertTrue(entry.hasNonNull("message"));
    }

    /**
     * A well-formed failure exits 1 after writing its document, so "exit 1 with
     * JSON" is a failed weave and "no JSON" is a dead JVM.
     *
     * <p>{@code --android-jar} is what makes the exit assertion mean something:
     * without it {@link ConfigResolver#resolve} throws on any host with no
     * Android SDK, picocli returns 1 on its own, and the run never reaches
     * {@link BatchRunner}. The path need not exist — the pipeline stops at
     * {@code config_validation} before opening it.
     */
    @Test
    void instrumentExitsOneWhenTheWeaveFails(@TempDir Path tmp) throws Exception {
        Path apk = Files.createFile(tmp.resolve("sample.apk"));
        Path out = tmp.resolve("sample.json");

        int exit = new CommandLine(new InstrumentationCli()).execute(
                "instrument", apk.toString(),
                "--android-jar", tmp.resolve("android.jar").toString(),
                "--results-json", out.toString());

        assertEquals(1, exit, "a failed weave must not exit 0");
        JsonNode entry = MAPPER.readTree(out.toFile()).get("results").get(0);
        assertFalse(entry.get("success").asBoolean());
        assertEquals("config_validation", entry.get("phase").asText());
    }

    /**
     * dexlib2's {@code ExceptionWithContext} keeps the real cause ("Unsigned
     * short value out of range") only in {@code getCause()}, so a message built
     * from the outermost exception alone names the symptom and hides the cause.
     */
    @Test
    void failureMessageCarriesTheInnermostCause() {
        String chain = BatchRunner.causeChain(new RuntimeException("outer",
                new RuntimeException("middle", new IllegalStateException("inner"))));

        assertTrue(chain.contains("inner"), chain);
        assertEquals(2, chain.split("; caused by: ", -1).length - 1, chain);
    }

    /**
     * A failure keeps what was measured before it: an empty {@code weaveCounts}
     * would erase the statistics of every DEX woven before the failing one.
     */
    @Test
    void failureKeepsTheCountersAccumulatedSoFar(@TempDir Path tmp) throws Exception {
        BatchRunner.PerApkResult failure = BatchRunner.failed(
                tmp.resolve("sample.apk"), "m", "uncaught", Map.of("advices", 3));
        Path out = tmp.resolve("results.json");

        BatchRunner.writeResultsJson(List.of(failure), out);

        JsonNode entry = MAPPER.readTree(out.toFile()).get("results").get(0);
        assertEquals(3, entry.get("weaveCounts").get("advices").asInt());
    }

    @Test
    void resultsJsonCarriesWeaveCountsForASuccessfulWeave(@TempDir Path tmp) throws Exception {
        BatchRunner.PerApkResult success = new BatchRunner.PerApkResult(
                "cryptoapp.apk", true, "instrumented + signed", "signed",
                Map.of("matchesApplied", 42, "plansSkippedHighRegister", 3));
        Path out = tmp.resolve("results.json");

        BatchRunner.writeResultsJson(List.of(success), out);

        JsonNode entry = MAPPER.readTree(out.toFile()).get("results").get(0);
        assertTrue(entry.get("success").asBoolean());
        assertEquals("signed", entry.get("phase").asText());
        // The counters are the reason the option exists: task 6.4 reads
        // plansSkippedHighRegister to tell whether emitting N invokes instead
        // of 1 pushed any site over its register budget.
        assertEquals(42, entry.get("weaveCounts").get("matchesApplied").asInt());
        assertEquals(3, entry.get("weaveCounts").get("plansSkippedHighRegister").asInt());
    }

    /**
     * {@code advicesExcludedByArity} counts the advice/overload pairs the
     * wrapper grouping loop left out of a wrapper because the advice's
     * positional {@code args()} arity does not fit the overload (INV-INS-159):
     * an advice excluded from two overloads counts 2. It travels beside
     * {@code wrappersGenerated}, and a zero is written rather than omitted: the
     * Python wrapper copies {@code weaveCounts} through whole, so an absent key
     * and a zero would be indistinguishable downstream.
     *
     * <p>Like the case above this is a serialisation test: {@code counts} is
     * built by hand, so it pins the document shape, not the origin of the
     * number. What produces the number is the grouping loop, covered by the
     * advice-emitter tests.
     */
    @Test
    void resultsJsonCarriesTheArityCounterBesideWrappersGenerated(@TempDir Path tmp)
            throws Exception {
        BatchRunner.PerApkResult excluded = new BatchRunner.PerApkResult(
                "twoOverloads.apk", true, "instrumented + signed", "signed",
                Map.of("wrappersGenerated", 2, "advicesExcludedByArity", 2));
        BatchRunner.PerApkResult none = new BatchRunner.PerApkResult(
                "clean.apk", true, "instrumented + signed", "signed",
                Map.of("wrappersGenerated", 4, "advicesExcludedByArity", 0));
        Path out = tmp.resolve("results.json");

        BatchRunner.writeResultsJson(List.of(excluded, none), out);

        JsonNode results = MAPPER.readTree(out.toFile()).get("results");
        assertEquals(2, results.get(0).get("weaveCounts").get("wrappersGenerated").asInt());
        assertEquals(2, results.get(0).get("weaveCounts").get("advicesExcludedByArity").asInt(),
                "one excluded pair per overload");
        assertTrue(results.get(1).get("weaveCounts").hasNonNull("advicesExcludedByArity"),
                "an APK with no excluded pair carries the key, never omits it");
        assertEquals(0, results.get(1).get("weaveCounts").get("advicesExcludedByArity").asInt());
    }

    /**
     * The pipeline itself writes every wrapper counter, zeros included:
     * {@code wrappersGenerated}, {@code advicesExcludedByArity},
     * {@code wrapperTargetsUnresolved} (INV-INS-160) and the two APK-scoped
     * alias counters {@code wrappersAliasedToSubtype} and
     * {@code wrapperAliasesUnmerged}. Driven through {@link BatchRunner#instrumentOne}
     * on an APK holding one empty DEX and a descriptor with no advices, which
     * stops at {@code dex_only} because no monitor build is configured.
     */
    @Test
    void aWovenApkReportsEveryWrapperCounter(@TempDir Path tmp) throws Exception {
        Path descriptor = Files.writeString(tmp.resolve("descriptor.json"),
                "{\"aspectName\":\"EmptyMonitorAspect\",\"imports\":[],\"advices\":[]}");
        Path dex = tmp.resolve("classes.dex");
        DexPool.writeTo(dex.toString(),
                new ImmutableDexFile(Opcodes.forDexVersion(35), Collections.emptySet()));
        Path apk = tmp.resolve("empty.apk");
        try (ZipOutputStream zip = new ZipOutputStream(Files.newOutputStream(apk))) {
            zip.putNextEntry(new ZipEntry("classes.dex"));
            zip.write(Files.readAllBytes(dex));
            zip.closeEntry();
        }
        EffectiveConfig cfg = new EffectiveConfig(descriptor, null,
                Files.createDirectory(tmp.resolve("work")), null, List.of(),
                null, null, null, false, null, "INFO");
        Path out = tmp.resolve("empty.json");

        BatchRunner.instrumentOne(cfg, apk, out);

        JsonNode entry = MAPPER.readTree(out.toFile()).get("results").get(0);
        assertEquals("dex_only", entry.get("phase").asText(), entry.get("message").asText());
        JsonNode counts = entry.get("weaveCounts");
        for (String key : List.of("wrappersGenerated", "advicesExcludedByArity",
                "wrapperTargetsUnresolved", "wrappersAliasedToSubtype", "wrapperAliasesUnmerged")) {
            assertTrue(counts.hasNonNull(key), key + " must be written, never omitted");
            assertEquals(0, counts.get(key).asInt(), key);
        }
    }

    @Test
    void instrumentWritesNothingWhenNoResultsJsonIsRequested(@TempDir Path tmp) throws Exception {
        Path apk = Files.createFile(tmp.resolve("sample.apk"));

        BatchRunner.instrumentOne(failingConfig(), apk, null);

        try (var entries = Files.list(tmp)) {
            assertEquals(List.of(apk), entries.toList(),
                    "ad-hoc console runs must not leave report files behind");
        }
    }
}
