package br.unb.cic.rvsec.crysl.core.model;

import java.util.Objects;

/**
 * The version stamp every {@link SpecModel} carries: which corpus the model was lifted from, and
 * the source stamp of that corpus alone.
 *
 * <p>Two runs of the component a day apart are not comparable without this, because the corpora
 * move: the predicate substrate signature of {@code jca_android} changed five times in four days.
 *
 * @param corpus identifier of the corpus, e.g. {@code jca_android} or {@code CrySL-Rules}
 * @param source where that corpus was read from and at which commit
 */
public record Version(String corpus, SourceStamp source) {

    public Version {
        Objects.requireNonNull(corpus, "Version.corpus is mandatory (INV-CONF-01)");
        Objects.requireNonNull(source, "Version.source is mandatory (INV-CONF-01)");
    }
}
