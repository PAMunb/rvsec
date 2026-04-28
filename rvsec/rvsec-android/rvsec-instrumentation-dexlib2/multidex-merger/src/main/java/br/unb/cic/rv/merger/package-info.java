/**
 * Repacks woven DEX files into the target APK, runs {@code zipalign} for
 * 4-byte alignment, and signs with {@code apksigner v3}.
 *
 * <p>Spec-set agnostic: the signing pipeline is identical for APKs carrying
 * JCA-derived monitors, Generic-derived monitors, or both.
 */
package br.unb.cic.rv.merger;
