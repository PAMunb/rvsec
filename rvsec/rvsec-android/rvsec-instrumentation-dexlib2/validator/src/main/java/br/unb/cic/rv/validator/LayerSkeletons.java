package br.unb.cic.rv.validator;

/**
 * Historical placeholder for Phase-5-pending layer skeletons. Every layer
 * (1-5) is now implemented as a dedicated class; this file remains only as
 * a stable navigational anchor for code archaeology and is intentionally
 * empty of behaviour.
 */
public final class LayerSkeletons {

    private LayerSkeletons() {}

    // Layer 1 (BaksmaliDiffer) is implemented in BaksmaliDiffer.diff;
    // see ValidationCli.Layer1 for the wired CLI path.

    // Layer 2 (BootValidator) is implemented in BootValidator.analyze / .capture;
    // see ValidationCli.Layer2 for the wired CLI path.

    // Layer 3 (TraceComparator) is implemented in TraceComparator.compare;
    // see ValidationCli.Layer3 for the wired CLI path.

    // Layer 4 (BatchValidator) is implemented in BatchValidator.analyze / .orchestrate;
    // see ValidationCli.Layer4 for the wired CLI path.

    // Layer 5 (CoverageValidator) is implemented in CoverageValidator.compare;
    // see ValidationCli.Layer5 for the wired CLI path.
}
