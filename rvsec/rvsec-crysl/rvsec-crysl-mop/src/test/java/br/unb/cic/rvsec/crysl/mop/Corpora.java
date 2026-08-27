package br.unb.cic.rvsec.crysl.mop;

import br.unb.cic.rvsec.crysl.core.model.SourceStamp;
import br.unb.cic.rvsec.crysl.core.model.Version;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.Instant;
import java.util.List;
import java.util.stream.Stream;

/**
 * Where the five {@code .mop} corpora live and how the tests stamp them.
 *
 * <p>The corpora are read from the sibling {@code rvsec-mop} module in the working tree, not copied
 * into test resources. A copy would answer a question about a snapshot: {@code jca_android} changed
 * in every prior round of this work, and a test that passes against a frozen copy while the live
 * set has moved is worse than no test. INV-CONF-12 makes the read one-way — nothing here writes to
 * a corpus path.
 */
final class Corpora {

    /**
     * The five corpora, with the file count each is measured at.
     *
     * <p>Four carry a literal because they are frozen: any change in their size is a finding, and
     * the number is what states it. {@code jca_android} is the live set under construction, so its
     * size is read from the directory instead — a literal there is arithmetic that moves whenever a
     * specification is added, says nothing about the lift, and is discovered one build cycle at a
     * time because JUnit stops at the first failed assertion.
     */
    static final List<Corpus> ALL = List.of(
            new Corpus("jca", 23),
            new Corpus("jca_android", filesOf("jca_android").size()),
            new Corpus("jca_android_bug_predicate", 23),
            new Corpus("generic", 118),
            new Corpus("generic_new", 27));

    /** The files the five corpora hold between them — the denominator of the lift census. */
    static int expectedTotal() {
        return ALL.stream().mapToInt(Corpus::expectedFiles).sum();
    }

    private Corpora() {
    }

    /** The directory holding the five corpus directories, relative to this module. */
    static Path root() {
        return Paths.get("..", "..", "rvsec-mop", "src", "main", "resources").normalize();
    }

    static Path directory(String corpus) {
        return root().resolve(corpus);
    }

    static Path file(String corpus, String name) {
        return directory(corpus).resolve(name);
    }

    /** The {@code .mop} files of one corpus, sorted, so that a run is diffable against the last. */
    static List<Path> filesOf(String corpus) {
        try (Stream<Path> entries = Files.list(directory(corpus))) {
            return entries.filter(p -> p.getFileName().toString().endsWith(".mop")).sorted().toList();
        } catch (IOException e) {
            throw new UncheckedIOException("cannot list corpus " + corpus, e);
        }
    }

    /**
     * A stamp for one corpus. The commit is a fixed literal rather than the working tree's HEAD:
     * a test asserting reproducible counts must itself be reproducible, and INV-CONF-01 only
     * requires that a model carry the stamp of the corpus it came from, not that a test invent one.
     */
    static Version version(String corpus) {
        return new Version(corpus, new SourceStamp("rvsec", "working-tree", Instant.EPOCH));
    }

    record Corpus(String name, int expectedFiles) {
    }
}
