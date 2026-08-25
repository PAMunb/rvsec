package br.unb.cic.rvsec.crysl.core;

import java.nio.file.Path;

/**
 * An input the run needs is missing or unreadable.
 *
 * <p>This is the one fatal that happens <em>before</em> any metric runs, and it is deliberately not
 * a typed {@code Unknown}. An {@code Unknown} is a finding about a specification the component read
 * and could not decide; a {@code CorpusReadError} says the component never read anything, so there
 * is no finding to publish and nothing partial is emitted. Confusing the two would let a mistyped
 * path be published as a corpus in which the component "could not decide" — a measurement about the
 * caller's shell, presented as a measurement about the corpus.
 *
 * <p>A run that hits this exits non-zero ({@code ExitCode.CORPUS_READ_ERROR}). By contrast a run
 * that produces many {@code LiftFailure}s or many {@code Unknown}s exits {@code 0}: those are
 * results, and their counts belong in the report.
 */
public class CorpusReadError extends RuntimeException {

    private static final long serialVersionUID = 1L;

    /**
     * @param what the role the missing input plays, in the caller's words (e.g. "the .mop corpus")
     * @param path the path that was tried, so the message names it rather than describing it
     */
    public CorpusReadError(String what, Path path) {
        super(what + " is missing or unreadable: " + path.toAbsolutePath());
    }
}
