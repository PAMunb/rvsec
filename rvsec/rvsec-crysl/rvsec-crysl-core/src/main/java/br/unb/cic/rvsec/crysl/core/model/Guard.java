package br.unb.cic.rvsec.crysl.core.model;

import java.util.Objects;

/**
 * A side condition attached to an event or to an order transition, kept as the raw text it was
 * declared with.
 *
 * <p>It stays text at this level because deciding a guard is a metric's job, not the model's: M2
 * refuses with {@code Unknown{OverlappingDispatch}} exactly when a guard separating two labels is
 * not statically decidable, and it can only make that call over the text as written.
 */
public record Guard(String text) {

    public Guard {
        Objects.requireNonNull(text, "Guard.text is mandatory");
    }
}
