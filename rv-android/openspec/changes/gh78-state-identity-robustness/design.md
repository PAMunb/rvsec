# Design: rv-agent state-identity robustness

## Context

State identity drives rv-agent exploration (see `proposal.md`, GitHub Issue #78; FR23 dump/parse, FR26 coverage-optimized DFS, FR27 reward, FR29 stuck/plateau). The primary identity is a structural SHA-256 hash of the interactive items in the UIAutomator dump (`dynamic_state_graph.py:41,82-92`), and the graph is keyed by it (`:187,207`). The 2026-07-13 investigation (report `docs/20260713_relatorio_ape_sata_cegar_gator_30curse.md`) confirmed six independent weaknesses in code. This design keeps the structural hash as the authoritative node key and adds secondary signals and one conditional fallback around it. All six items are additive and share fixtures; none introduces a new dependency.

## Architecture

```
UIAutomator dump ──► UIAutomator2Parser (interactive items)
        │                     │
        │            ┌────────┴─────────┐
        ▼            ▼                  ▼
 structural hash   content hash    degeneracy check ──► (if degenerate & frame not near-uniform)
 (node key)        (progress/scroll)                      perceptual hash (aHash/dHash, Pillow)
        │            │                                          │
        ▼            ▼                                          ▼
 DynamicStateGraph  PlateauDetector / scroll fixpoint     state_signature (node key override)
                     ▲
                     │ new_mop_method = callback_signature (static proxy)
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `dynamic_state_graph.compute_screen_hash_from_description` | Structural hash (unchanged) | `screen_desc` | `str` (node key) |
| `dynamic_state_graph.compute_content_hash` (new) | Secondary "did content change?" hash | `screen_desc` | `str` (not a node key) |
| `dynamic_state_graph.is_degenerate_tree` (new) | Detect Canvas/SurfaceView/Compose degeneracy | `screen_desc` | `bool` |
| `dynamic_state_graph.perceptual_hash` (new) | aHash/dHash over screenshot, with near-uniform guard | `PIL.Image` | `str \| None` |
| `rvagent_strategy` (S1) | Feed `new_mop_method` to plateau detector | `callback_signature` | plateau reset |
| `base_strategy` scroll (S6) | Scroll-while-content-changes fixpoint | `content_hash` | scroll steps |
| `abstract_visitor.should_exclude_system_button` (S5) | Permission-dialog filter + routing | screen package | exclude/route |
| `device_interface` (S4) | Idle wait + disable animations | — | robust dump |

## Mapping: Spec → Implementation → Test

| Requirement | Implementation | Test |
|-------------|---------------|------|
| Plateau MOP-Progress Signal | `rvagent_strategy.py:672` passes `callback_signature` (or None) to `PlateauDetector.record_iteration` | `test_plateau_mop_signal_resets`, `test_plateau_no_mop_unchanged` |
| Secondary Content Hash | `compute_content_hash` (normalize text, ≥3-digit runs, cap, `content_description`) | `test_content_hash_flips_on_real_change`, `test_content_hash_collapses_recapture`, `test_digit_norm_preserves_algo_names` |
| INV-AGT-50 (content hash never a key) | Graph keying untouched at `:187,207`; content hash only read by plateau/scroll | `test_content_hash_not_graph_key` |
| INV-AGT-51 (≥3-digit runs) | Regex in `compute_content_hash` | `test_digit_norm_runs_ge_3` |
| INV-AGT-53 (`content_description`) | Attribute read in `compute_content_hash` | covered by content-hash tests |
| Dump Robustness | `device_interface` idle-wait + `settings put ... _scale 0` (reuse `:406`) | `test_dump_waits_idle`, `test_animations_disabled` |
| Extended System-Package Filter | `abstract_visitor.py:279` + strategy routing | `test_permissioncontroller_routed` |
| Scroll Fixpoint | `base_strategy.py:381` loop on `content_hash` with cap | `test_scroll_stops_at_fixpoint`, `test_scroll_stops_at_cap` |
| Perceptual Fallback + INV-AGT-52 | `is_degenerate_tree` + `perceptual_hash` + near-uniform guard | `test_degenerate_uses_perceptual`, `test_flag_secure_falls_back`, `test_conventional_no_fallback` |

## Goals / Non-Goals

**Goals:**
- Make the six weaknesses observable/actionable without changing the primary node key.
- Zero new dependency; reuse existing Pillow, `settings put`, and the parser's interactive-item filtering.
- Each item independently testable with existing fixtures (`tests/fixtures/screenshots/*`).

**Non-Goals:**
- Runtime MOP/coverage feed (that is #79 — this change's S1 uses only the static `callback_signature` proxy).
- Changing the structural hash attribute set or the graph keying.
- Solving action selection inside Canvas apps (S7 gives identity only, not actionable widgets).

## Decisions

- **Content hash outside the primary dedup (D1).** The content hash is read only by plateau/scroll logic; the graph stays keyed by the structural hash. Alternative (fold content into the node key) was rejected: it risks state explosion on dynamic screens (feeds/clocks). The investigation confirmed 13 structural hashes over 16 dumps with no explosion when content is kept secondary.
- **Digit normalization only on runs ≥3 (D2).** Naive `digit→#` collapses `MD5`→`md#`, `SHA-256`→`sha-#` — destroying JCA algorithm identity, which is central to this project. Restricting to ≥3-digit runs neutralizes timestamps/counters while preserving `MD5`/`SHA-1`/`4 players`. Alternative (timestamp-specific regex) is more precise but more code; ≥3-digit runs is the P1 choice and was validated against the fixtures.
- **Perceptual hash only when degenerate (D3).** Computing a perceptual hash always would add screenshot cost and animation noise for every app. Gating on ≤2 interactive nodes / dominant SurfaceView/ComposeView keeps it dormant for conventional apps (confirmed: cryptoapp/hashpass/ludo fixtures are non-degenerate).
- **Near-uniform frame guard (D4).** FLAG_SECURE returns a valid black bitmap (not an exception; static scan: 23/219 APKs use it in app code). Without the guard, all secure screens would collide on one perceptual hash. The guard falls back to the structural hash, which stays legible under FLAG_SECURE.
- **aHash/dHash over Pillow (D5).** ~30 lines, no new dependency (Pillow already in `rv-agent`), Hamming-distance comparable. Alternative (pHash via DCT / a CV library) rejected on P1 and dependency grounds.

## API Design

### `compute_content_hash(screen_desc) -> str`
Precondition: `screen_desc.items` populated. Reads `text` (lower-cased, digit-runs ≥3 → placeholder, length-capped), `content_description`, `checked`, `selected` over the same interactive items as the structural hash. Postcondition: 12-hex digest; deterministic for identical content; never used as a graph node key.

### `is_degenerate_tree(screen_desc) -> bool`
Returns True when interactive nodes ≤ 2 or a `SurfaceView`/`ComposeView` dominates. Pure function over `screen_desc`.

### `perceptual_hash(image) -> str | None`
Returns aHash/dHash of the screenshot, or None when the frame is near-uniform (variance below threshold). Caller uses None to fall back to the structural hash.

### `PlateauDetector.record_iteration(..., new_mop_method: str | None)`
Existing signature (`plateau_detector.py:75-105`); this change starts passing the real value from `rvagent_strategy.py:672` instead of a constant None.

## Data Flow

Per exploration step: dump → parser produces interactive items → structural hash (node key) and content hash computed → if `is_degenerate_tree` and screenshot not near-uniform, `perceptual_hash` overrides the node signature → action executed → `content_hash` delta drives scroll fixpoint and (with `callback_signature`) the plateau detector.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| Black/near-uniform screenshot | FLAG_SECURE screen | Detected by variance guard | Fall back to structural hash |
| Missing screenshot | Screenshot capture failure | `perceptual_hash` receives None-equivalent | Fall back to structural hash |
| No new exceptions introduced | — | — | — |

## Risks / Trade-offs

- [Perceptual hash noisy under continuous Canvas animation] → S4 disables animations; Hamming threshold tolerates minor render noise.
- [Fixtures lack dynamic/degenerate screens] → content-hash normalization and degeneracy detection validated on available fixtures; dynamic-screen normalization is a documented follow-up (collect repeated dumps of live-content screens) but not a blocker, since the content hash is secondary by construction.
- [Permission-dialog packages vary by OEM/API level] → policy keyed on known package prefixes; unknown system packages keep current behavior.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit | content hash flip/collapse/normalization; degeneracy detection; near-uniform guard; plateau signal; scroll fixpoint | Existing dump fixtures + synthetic images | ~12 tests |
| Integration | dump idle-wait + animation-disable; permission-dialog routing | Device-interface + visitor with staged screens | ~3 tests |

## Open Questions

- None blocking. The dynamic-screen normalization dataset (repeated dumps of live-content screens) is a follow-up refinement to the digit/normalization thresholds, not a prerequisite — the content hash is secondary and cannot explode the graph.
