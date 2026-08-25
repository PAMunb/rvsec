package br.unb.cic.rvsec.crysl.core.model;

import java.time.Instant;
import java.util.Objects;

/**
 * Identifies the artifact an input came from: the git repository, the commit read, and the instant
 * the read happened.
 *
 * <p>There is one stamp per corpus, never one per run. The component's input spans two git
 * repositories - {@code rvsec} for the {@code .mop} sets and {@code rvsec-cognicrypt} for the
 * upstream oracle - plus the SDK under {@code $ANDROID_HOME}. A single scalar commit for the whole
 * run would stamp an oracle-derived number with the commit of a repository that did not produce it,
 * which is the failure INV-CONF-01 exists to prevent.
 *
 * @param repository the repository or corpus source the artifact was read from
 * @param commit     the commit of that repository, not of the run
 * @param data       the instant the artifact was read
 */
public record SourceStamp(String repository, String commit, Instant data) {

    public SourceStamp {
        Objects.requireNonNull(repository, "SourceStamp.repository is mandatory (INV-CONF-01)");
        Objects.requireNonNull(commit, "SourceStamp.commit is mandatory (INV-CONF-01)");
        Objects.requireNonNull(data, "SourceStamp.data is mandatory (INV-CONF-01)");
    }
}
