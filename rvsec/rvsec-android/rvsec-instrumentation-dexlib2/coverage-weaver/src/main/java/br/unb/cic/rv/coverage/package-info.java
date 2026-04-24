/**
 * Coverage weaver — injects the {@code mop.Coverage.log(signature)} catch-all
 * at every non-excluded application method entry, reproducing the semantics
 * of the legacy {@code Coverage.aj}. Spec-set agnostic.
 */
package br.unb.cic.rv.coverage;
