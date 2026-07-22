# Proposal: rv-agent state-identity robustness

GitHub Issue: #78

## Why

The rv-agent identifies each explored state (a WTG node) by a SHA-256 **structural hash** of the UIAutomator dump (`dynamic_state_graph.py:41,82-92`) over nine structural attributes, deliberately ignoring `text`/`content-desc`/`bounds`. This is robust for conventional apps but the 2026-07-13 investigation (report `docs/20260713_relatorio_ape_sata_cegar_gator_30curse.md`, verified against code by subagents) found six points where state identification and dump quality silently degrade exploration: a dead plateau-progress signal, no "did this action change anything?" secondary signal, single-shot scrolling, unfiltered system-package dialogs, and total state collapse on apps whose UIAutomator tree is degenerate (Canvas/SurfaceView/Compose without semantics). Fixing these makes the DFS strategy and reward propagation see progress they currently miss.

## What Changes

- **S1 — Reconnect the plateau MOP signal.** `rvagent_strategy.py:672` always passes `new_mop_method=None` to the `PlateauDetector`, even though the detector already supports the signal (`plateau_detector.py:75-105`). Feed it the executed action's static proxy (`callback_signature`) so plateau resets when a new monitored-operation-reaching method is exercised, instead of only on structural-hash deltas.
- **S2 — Secondary `content_hash`, outside the graph's primary dedup.** A second hash answering "did this action change the screen?" from normalized `text` + `content_description` + `checked`/`selected`. It is **never** a node key — the graph stays keyed by the structural hash (`dynamic_state_graph.py:187,207`), so no state explosion is possible by construction. Quantitative check on 16 real dumps: 13 structural hashes; the content_hash correctly flips on real change (empty→filled password field) and collapses identical recaptures. Digit normalization is restricted to runs of **≥3 digits** so JCA algorithm names (`MD5`, `SHA-256`) are preserved while timestamps/counters are neutralized. Uses the correct key `content_description`.
- **S4 — Dump robustness.** `waitForIdle` before the dump and disabled animations (`settings put global window_animation_scale 0`; the `settings put` path already exists at `device_interface.py:406`), reducing transient/mid-animation dumps. Double-dump consensus only conditionally.
- **S5 — Extend the system-package filter.** In the existing hook (`abstract_visitor.py:279 should_exclude_system_button`), add `permissioncontroller`/`packageinstaller` with an explicit grant/deny routing policy, coherent with the strategy's `SYSTEM_DIALOG_PACKAGES` (`rvagent_strategy.py:136-145`).
- **S6 — Scroll fixpoint (depends on S2).** Replace the one-scroll-per-container dedup (`base_strategy.py:381`, keyed by `(screen_hash, container, direction)`) with "scroll while the content_hash changes," capped at a maximum number of steps.
- **S7 — Perceptual fallback for degenerate trees.** When an app renders in `Canvas`/`SurfaceView`/`ComposeView` without semantics, the dump yields 1–2 generic nodes and every screen collides on the same structural hash (the agent believes it never moves). Detect that degeneracy cheaply (≤2 interactive nodes, or a dominant SurfaceView/ComposeView) and, **only then**, use a perceptual hash (aHash/dHash over the on-demand screenshot from `parse_node.py:171-175`; ~30 lines over the already-present Pillow, no new dependency) as the state signature. A mandatory guard detects a near-uniform/black frame first (under `FLAG_SECURE` UIAutomator returns a valid black bitmap, not an exception) and falls back to the structural hash; a static scan of the 219-APK dataset found 23 (10.5%) use FLAG_SECURE in app code (ceiling; profile: authenticators/password managers/vaults, many per-screen and preference-gated).

No **BREAKING** changes: the structural hash remains the primary state key; all additions are secondary signals or conditional fallbacks.

## Capabilities

### New Capabilities
<!-- None. This change modifies the existing agent capability; it introduces no new spec domain. -->

### Modified Capabilities
- `agent`: state identification and exploration requirements change — the structural screen hash gains a secondary content-hash companion and a conditional perceptual fallback for degenerate trees; plateau/stuck detection (FR29) consumes the MOP-progress signal; the coverage-optimized DFS strategy's scroll behavior (FR26) becomes a content-hash fixpoint; and dump acquisition (FR23) adds idle-wait/animation-disable robustness plus an extended system-package filter.

## Impact

- **Modules**: `rv-agent` (primary — strategy, plateau detector, state graph, parse/learn nodes, base strategy); `rv-screen-parser` (`abstract_visitor` system-package filter, S5); `rv-uiautomator` (dump idle-wait/animation-disable, S4).
- **Dependencies**: none added — S7's perceptual hash uses the existing Pillow dependency; no new package.
- **Requirements**: `agent` domain — FR23 (UI parsing/dump), FR26 (coverage-optimized DFS / scroll), FR27 (ranking/reward, via S1 plateau signal), FR29 (stuck/plateau detection). See `docs/PRD.md`.
- **Cross-references**: S1's static `callback_signature` proxy is superseded at runtime by the separate change #79 (runtime MOP signal); S6 depends on S2 within this change.
