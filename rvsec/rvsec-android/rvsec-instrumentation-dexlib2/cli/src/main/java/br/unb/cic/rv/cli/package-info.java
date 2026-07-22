/**
 * Picocli entry point that orchestrates the complete DEX-native weaving
 * pipeline end-to-end. Consumed by the Python wrapper
 * ({@code rv-android/modules/rv-instrumentation-dexlib2/}) via subprocess.
 *
 * <p>Spec-set agnostic — weaves whichever specification set the descriptor
 * JSON declares; JCA or Generic.
 */
package br.unb.cic.rv.cli;
