/**
 * Layered validation harness operationalizing {@code docs/20260423_plano_validacao.md}.
 *
 * <p>Components, one per layer / static check:
 * <ul>
 *   <li>{@link br.unb.cic.rv.validator.ConstructionInventoryGenerator} —
 *       regenerates {@code docs/AJ_CONSTRUCTIONS_INVENTORY.md} from the
 *       RVSEC spec corpus (INV-INS-54).</li>
 *   <li>{@link br.unb.cic.rv.validator.FeatureMappingChecker} — enforces
 *       inventory ⊆ (mapping ∪ limitations) (INV-INS-54).</li>
 *   <li>{@link br.unb.cic.rv.validator.DescriptorAjParityChecker} —
 *       asserts JSON descriptor mirrors .aj semantically (INV-INS-56).</li>
 *   <li>{@link br.unb.cic.rv.validator.OracleLoader} — loads ≥3 oracle
 *       YAMLs for Layer-3 (INV-INS-59).</li>
 *   <li>{@link br.unb.cic.rv.validator.MethodRefAuditor} — Layer-4
 *       preflight: projects post-weaving method-ref counts per DEX,
 *       flags overflow candidates (INV-INS-62).</li>
 *   <li>{@link br.unb.cic.rv.validator.Layer1BaksmaliDiffer} / Layer2BootValidator /
 *       Layer3TraceComparator / Layer4BatchValidator / Layer5CoverageValidator
 *       — skeletons with clear gate semantics; full execution deferred
 *       to Phase 5 infra run.</li>
 * </ul>
 *
 * <p>Spec-set agnostic: every check works identically for JCA and Generic
 * specifications.
 */
package br.unb.cic.rv.validator;
