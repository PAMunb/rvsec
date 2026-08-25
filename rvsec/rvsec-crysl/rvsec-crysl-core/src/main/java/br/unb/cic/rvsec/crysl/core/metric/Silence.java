package br.unb.cic.rvsec.crysl.core.metric;

import br.unb.cic.rvsec.crysl.core.model.Provenance;
import java.util.Objects;

/**
 * One measured reason a specification can stay quiet, with the evidence that identified it.
 *
 * <p>A finding is only useful if the reader can tell which of the three causes it is, so the cause
 * is a {@link SilenceCause} rather than a sentence: the disposition follows from it mechanically,
 * and the counts per cause are countable per corpus. {@code detail} is the part that is specific to
 * this file — the formula, the absent class, the handler that is empty — and it is required, because
 * a silence finding that names no evidence cannot be checked against the file.
 *
 * @param specification the specification the finding is about
 * @param cause         which of the three causes of silence this is
 * @param detail        the file-specific evidence, e.g. the {@code ere} and the live prefix
 * @param site          where in the file the evidence was found
 */
public record Silence(String specification, SilenceCause cause, String detail, Provenance site) {

    public Silence {
        Objects.requireNonNull(specification, "Silence.specification is mandatory");
        Objects.requireNonNull(cause, "Silence.cause is mandatory");
        Objects.requireNonNull(site, "Silence.site is mandatory");
        if (detail == null || detail.isBlank()) {
            throw new IllegalArgumentException("Silence.detail is mandatory: a silence finding "
                    + "that names no evidence cannot be checked against the file");
        }
    }

    /** True when this finding stops M1-M4 from emitting a verdict (INV-CONF-09). */
    public boolean refusal() {
        return cause.disposition() == SilenceCause.Disposition.REFUSAL;
    }

    /** The full statement: the cause's written reason, then this file's evidence. */
    public String statement() {
        return cause.reason() + " — " + detail;
    }
}
