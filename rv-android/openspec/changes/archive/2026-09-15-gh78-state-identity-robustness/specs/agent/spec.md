## Purpose

The rv-agent explores an Android app by driving the UI and recording each distinct screen as a node in a dynamic Window Transition Graph (WTG). State identity is the foundation of exploration: if two different screens collapse to the same identity, the agent believes it is stuck; if one screen splits into many identities, the graph explodes and progress metrics become noise. Today identity is a single SHA-256 **structural hash** of the UIAutomator dump over nine structural attributes (class, resource-id, package, and the clickable/scrollable/checkable/enabled/long-clickable/editable flags), deliberately ignoring `text`, `content-desc`, and `bounds` (`modules/rv-agent/src/rv_agent/agent/dynamic_state_graph.py:41,82-92`). The graph is keyed by this hash (`dynamic_state_graph.py:187,207`).

This delta strengthens state identity and dump quality without changing the primary key. It adds a **secondary content signal** that answers "did this action change the screen?" (used for progress and scroll decisions, never as a node key, so no state explosion is possible by construction); reconnects a **dead plateau-progress signal**; makes dump acquisition robust to animations and transient frames; extends the **system-package filter** to permission dialogs; turns single-shot scrolling into a **content-driven fixpoint**; and adds a **perceptual fallback** for apps whose UIAutomator tree is degenerate (Canvas/SurfaceView/Compose without semantics), guarded so that screenshot-blocked screens (FLAG_SECURE) degrade to the structural hash. All requirements here are additive concerns layered on the existing agent capability (FR23, FR26, FR27, FR29); the structural hash remains authoritative for graph node identity.

## Data Contracts

### Input
- `screen_desc.items: list[ViewItem]` — interactive elements already filtered by the UIAutomator parser (source of both the structural and the secondary content hash).
- `view.text: str`, `view.content_description: str`, `view.checked: bool`, `view.selected: bool` — per-element content attributes read for the secondary content hash (source: UIAutomator dump).
- `callback_signature: str` — the executed action's statically resolved handler signature (source: static analysis via `rvagent_visitor`), used as the MOP-progress proxy fed to the plateau detector.
- `screenshot: PIL.Image` — on-demand screenshot (source: `parse_node.py:171-175`), read only for the perceptual fallback.

### Output
- `content_hash: str` — secondary 12-hex digest; consumed by plateau/scroll logic only, never used as a graph node key.
- `state_signature: str` — the state identity used for the graph node: the structural hash normally, or the perceptual hash only under a detected-degenerate-tree condition.

### Side-Effects
- **[Device]**: `settings put global window_animation_scale 0` (and matching transition/animator scales) applied before exploration to reduce mid-animation dumps; the existing `settings put` path is reused (`device_interface.py:406`).

### Error
- No new exceptions. Under FLAG_SECURE the screenshot is a valid black bitmap (not an exception); it is handled by the near-uniform-frame guard, not by error handling.

## Invariants

- **INV-AGT-50**: The `content_hash` MUST NOT be used as a graph node key; graph node identity remains the structural hash (or, under a degenerate tree, the perceptual hash). This guarantees the secondary content signal cannot cause state explosion.
- **INV-AGT-51**: Digit normalization for the content hash MUST apply only to digit runs of length ≥ 3, so that short tokens carrying domain meaning (e.g. `MD5`, `SHA-1`, `SHA-256`, `4 players`) are preserved while timestamps and large counters are neutralized.
- **INV-AGT-52**: The perceptual hash MUST be computed only when the degenerate-tree condition holds AND the screenshot frame is not near-uniform; otherwise the structural hash MUST be used.
- **INV-AGT-53**: The content hash MUST read the `content_description` attribute (not a `content_desc` key), consistent with the parsed view model.

## ADDED Requirements

### Requirement: Plateau MOP-Progress Signal (FR29)

The plateau detector SHALL receive the executed action's monitored-operation proxy so that plateau resets on MOP progress, not only on structural-hash change. Today `RVAgentStrategy` passes `new_mop_method=None` unconditionally (`rvagent_strategy.py:672`) even though `PlateauDetector` already supports the argument (`plateau_detector.py:75-105`), leaving the signal dead.

#### Scenario: New MOP-reaching method resets plateau
- **WHEN** an executed action's `callback_signature` resolves to a method flagged `directly_reaches_target` or `reaches_target` by static analysis that has not been seen this episode
- **THEN** `record_iteration` SHALL be called with `new_mop_method` set to that signature
- **AND** the plateau counter SHALL reset even if the structural hash did not change

#### Scenario: No MOP progress leaves plateau accounting unchanged
- **WHEN** an executed action resolves to no MOP-reaching method
- **THEN** `record_iteration` SHALL be called with `new_mop_method=None`
- **AND** plateau accounting SHALL behave exactly as today (structural-hash delta only)

### Requirement: Secondary Content Hash (FR26)

The agent SHALL compute a secondary `content_hash` that answers "did this action change the screen content?" from normalized `text`, `content_description`, `checked`, and `selected` over the same interactive items used by the structural hash. It SHALL NOT be a graph node key (INV-AGT-50). Text SHALL be lower-cased and capped in length, and digit runs of length ≥ 3 SHALL be normalized to a placeholder (INV-AGT-51), so dynamic content (timestamps, counters) does not defeat the signal while domain tokens survive.

#### Scenario: Real content change flips the hash
- **WHEN** the same structural screen transitions from an empty password field (`text="Input"`) to a filled one (`text="••••"`)
- **THEN** the `content_hash` SHALL differ between the two dumps
- **AND** the structural hash SHALL remain identical

#### Scenario: Identical recapture collapses
- **WHEN** the same screen is dumped twice with byte-identical interactive content
- **THEN** the `content_hash` SHALL be identical across both dumps

#### Scenario: Digit normalization preserves algorithm names
- **WHEN** a screen contains the labels `MD5`, `SHA-1`, and `SHA-256`
- **THEN** normalization SHALL leave these tokens distinguishable in the `content_hash` (only runs of ≥ 3 digits are collapsed)

### Requirement: Dump Robustness (FR23)

The agent SHALL wait for UI idle before dumping and SHALL disable window/transition/animator animations for the session, reducing transient or mid-animation dumps. A double-dump consensus MAY be used only conditionally (e.g. when a dump appears unstable), not on every step (P1).

#### Scenario: Idle wait precedes dump
- **WHEN** the agent is about to capture a UIAutomator dump after an action
- **THEN** it SHALL wait for UI idle first

#### Scenario: Animations disabled for the session
- **WHEN** an exploration session starts
- **THEN** `window_animation_scale`, `transition_animation_scale`, and `animator_duration_scale` SHALL be set to 0 via the existing `settings put` path

### Requirement: Extended System-Package Filter (FR23)

The visitor's system-package exclusion (`abstract_visitor.py:279 should_exclude_system_button`) SHALL additionally recognize permission-dialog packages (`permissioncontroller`, `packageinstaller`) with an explicit grant/deny routing policy coherent with the strategy's `SYSTEM_DIALOG_PACKAGES` (`rvagent_strategy.py:136-145`), so runtime permission prompts are handled deterministically rather than treated as app UI.

#### Scenario: Permission dialog routed by policy
- **WHEN** the current screen belongs to `com.google.android.permissioncontroller`
- **THEN** the visitor SHALL classify it as a system dialog
- **AND** the strategy SHALL route it to the configured grant/deny action rather than exploring it as app content

### Requirement: Scroll Fixpoint (FR26)

Scrolling SHALL continue on a container while the `content_hash` keeps changing, up to a maximum step cap, replacing the current one-scroll-per-`(screen_hash, container, direction)` dedup (`base_strategy.py:381`). This depends on the Secondary Content Hash requirement.

#### Scenario: Scroll stops at content fixpoint
- **WHEN** a container is scrolled and the `content_hash` is unchanged after a scroll step
- **THEN** scrolling of that container in that direction SHALL stop (fixpoint reached)

#### Scenario: Scroll stops at step cap
- **WHEN** a container's `content_hash` keeps changing on every scroll step
- **THEN** scrolling SHALL stop once the configured maximum step count is reached

### Requirement: Perceptual Fallback for Degenerate Trees (FR23)

When the UIAutomator tree is degenerate — at most two interactive nodes, or a dominant `SurfaceView`/`ComposeView` — the agent SHALL derive the state signature from a perceptual hash (aHash/dHash over the on-demand screenshot, using the existing Pillow dependency), because otherwise every screen of such an app collapses to the same structural hash. A mandatory guard SHALL detect a near-uniform (e.g. black) frame first and fall back to the structural hash (INV-AGT-52), because under FLAG_SECURE the screenshot is a valid black bitmap; the structural hash remains fully usable in that case.

#### Scenario: Degenerate tree uses perceptual hash
- **WHEN** a dump yields a single dominant `SurfaceView` and ≤ 2 interactive nodes, and the screenshot frame is not near-uniform
- **THEN** the state signature SHALL be the perceptual hash of the screenshot
- **AND** two visually distinct screens of that app SHALL receive distinct signatures

#### Scenario: FLAG_SECURE screen falls back to structural hash
- **WHEN** the degenerate-tree condition holds but the screenshot frame is near-uniform (black, as returned under FLAG_SECURE)
- **THEN** the perceptual hash SHALL NOT be used
- **AND** the state signature SHALL be the structural hash (status quo)

#### Scenario: Conventional app never triggers the fallback
- **WHEN** a dump exposes more than two interactive nodes with resource-ids (a conventional widget tree)
- **THEN** the degenerate-tree condition SHALL be false
- **AND** the state signature SHALL be the structural hash
