package br.unb.cic.rvsec.crysl.core.model;

import java.util.Objects;

/**
 * Where an item of a model was declared, as {@code file:line}.
 *
 * <p>Provenance is stamped by the lifter, at the moment it reads the item, and is never parsed back
 * out of emitted text: text is a rendering of the model, so recovering positions from it would make
 * the report its own source of truth.
 *
 * @param file the file the item was read from
 * @param line the 1-based line within that file
 */
public record Provenance(String file, int line) {

    public Provenance {
        Objects.requireNonNull(file, "Provenance.file is mandatory");
        if (line < 1) {
            throw new IllegalArgumentException("Provenance.line is 1-based, got " + line);
        }
    }

    @Override
    public String toString() {
        return file + ":" + line;
    }
}
