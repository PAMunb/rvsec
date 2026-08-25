package br.unb.cic.rvsec.crysl.core.model;

import java.util.List;
import java.util.Objects;

/**
 * A specification of more than one parameter whose {@code ORDER} interleaves events over different
 * objects, so a single word over one object's alphabet does not describe the language.
 *
 * @param params the declared parameters the order interleaves over
 * @param site   where the order was declared
 */
public record MultiSlicedOrder(List<String> params, Provenance site) implements Unknown {

    public MultiSlicedOrder {
        Objects.requireNonNull(site, "MultiSlicedOrder.site is mandatory");
        params = List.copyOf(params);
    }
}
