package br.unb.cic.rvsec.crysl.core.model;

import java.util.List;
import java.util.Objects;

/**
 * Two or more labels match the same signature and the guard separating them is not statically
 * decidable, so the morphism {@code h} cannot say which letters the call emits.
 *
 * <p>The {@code labels} list must be non-empty (INV-CONF-07). A refusal that does not name which
 * labels overlap does not say how many letters the call emits, which is the one thing the reader
 * needs in order to decide whether the overlap matters.
 *
 * @param labels    the overlapping labels, in declaration order
 * @param signature the signature they all match
 * @param site      where the overlap was found
 */
public record OverlappingDispatch(List<String> labels, Signature signature, Provenance site)
        implements Unknown {

    public OverlappingDispatch {
        Objects.requireNonNull(signature, "OverlappingDispatch.signature is mandatory");
        Objects.requireNonNull(site, "OverlappingDispatch.site is mandatory");
        labels = List.copyOf(labels);
        if (labels.isEmpty()) {
            throw new IllegalArgumentException(
                    "OverlappingDispatch.labels must be non-empty (INV-CONF-07): a refusal that "
                            + "does not name the overlapping labels does not say how many letters "
                            + "the call emits");
        }
    }
}
