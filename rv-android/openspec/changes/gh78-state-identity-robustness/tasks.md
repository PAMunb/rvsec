<!-- Six independent-ish items sharing dynamic_state_graph.py + strategy files.
     S6 depends on S2 (uses content_hash). Groups 1-6 map to S1,S2,S4,S5,S6,S7.
     Single primary module (rv-agent) + minor rv-screen-parser/rv-uiautomator touches —
     no subagent orchestration needed (<20 files). TDD: write tests first per group. -->

## 1. S1 — Plateau MOP-progress signal (rv-agent)

- [ ] 1.1 Write failing tests: plateau resets when `callback_signature` is a new MOP-reaching method; unchanged when None (`test_plateau_mop_signal_resets`, `test_plateau_no_mop_unchanged`)
- [ ] 1.2 In `rvagent_strategy.py:672`, pass the executed action's `callback_signature` (or None) as `new_mop_method` to `PlateauDetector.record_iteration`
- [ ] 1.3 Run `uv run pytest modules/rv-agent --import-mode=importlib -o "addopts=" -k plateau`

## 2. S2 — Secondary content hash (rv-agent)

- [ ] 2.1 Write failing tests using `tests/fixtures/screenshots/*`: flip on real change (hashpass empty→filled), collapse on identical recapture (cryptoapp/003-005-009), digit-norm preserves `MD5`/`SHA-256`, content hash is never a graph key (INV-AGT-50/51/53)
- [ ] 2.2 Add `compute_content_hash(screen_desc)` in `dynamic_state_graph.py`: normalize `text` (lower-case, digit runs ≥3 → placeholder, length cap) + `content_description` + `checked` + `selected` over the interactive items; return 12-hex digest
- [ ] 2.3 Wire the content hash into the state record WITHOUT touching graph keying at `:187,207` (read-only signal for plateau/scroll)
- [ ] 2.4 Run `/rv-doc-code modules/rv-agent/src/rv_agent/agent/dynamic_state_graph.py`
- [ ] 2.5 Run `uv run pytest modules/rv-agent --import-mode=importlib -o "addopts=" -k content_hash`

## 3. S4 — Dump robustness (rv-uiautomator / rv-agent device layer)

- [ ] 3.1 Write tests: dump waits for idle before capture; session disables the three animation scales (`test_dump_waits_idle`, `test_animations_disabled`)
- [ ] 3.2 Add `waitForIdle` before the dump and set `window_animation_scale`/`transition_animation_scale`/`animator_duration_scale` to 0 via the existing `settings put` path (`device_interface.py:406`)
- [ ] 3.3 Run `uv run pytest modules/rv-agent modules/rv-uiautomator --import-mode=importlib -o "addopts=" -k "dump or animation"`

## 4. S5 — Extended system-package filter (rv-screen-parser + rv-agent strategy)

- [ ] 4.1 Write test: a `permissioncontroller` screen is classified as a system dialog and routed by grant/deny policy (`test_permissioncontroller_routed`)
- [ ] 4.2 Extend `abstract_visitor.py:279 should_exclude_system_button` to recognize `permissioncontroller`/`packageinstaller`; wire the grant/deny routing in the strategy coherent with `SYSTEM_DIALOG_PACKAGES` (`rvagent_strategy.py:136-145`)
- [ ] 4.3 Run `uv run pytest modules/rv-agent modules/rv-screen-parser --import-mode=importlib -o "addopts=" -k "system or permission"`

## 5. S6 — Scroll fixpoint (rv-agent) — depends on Group 2

- [ ] 5.1 Write tests: scroll stops at content fixpoint; scroll stops at step cap (`test_scroll_stops_at_fixpoint`, `test_scroll_stops_at_cap`)
- [ ] 5.2 Replace the one-scroll-per-`(screen_hash, container, direction)` dedup in `base_strategy.py:381` with a loop that scrolls while `content_hash` changes, capped at a configured maximum
- [ ] 5.3 Run `uv run pytest modules/rv-agent --import-mode=importlib -o "addopts=" -k scroll`

## 6. S7 — Perceptual fallback for degenerate trees (rv-agent)

- [ ] 6.1 Write tests: degenerate tree (dominant SurfaceView, ≤2 interactive nodes) uses perceptual hash; near-uniform/black frame (FLAG_SECURE) falls back to structural hash; conventional app never triggers the fallback (`test_degenerate_uses_perceptual`, `test_flag_secure_falls_back`, `test_conventional_no_fallback`) (INV-AGT-52)
- [ ] 6.2 Add `is_degenerate_tree(screen_desc)` and `perceptual_hash(image)` (aHash/dHash over Pillow, near-uniform-variance guard returns None) in `dynamic_state_graph.py`; override the state signature only when degenerate AND frame not near-uniform, reusing the on-demand screenshot (`parse_node.py:171-175`)
- [ ] 6.3 Run `/rv-doc-code modules/rv-agent/src/rv_agent/agent/dynamic_state_graph.py`
- [ ] 6.4 Run `uv run pytest modules/rv-agent --import-mode=importlib -o "addopts=" -k "degenerate or perceptual"`

## 7. Integration & Verification

- [ ] 7.1 Add integration tests: idle-wait + animation-disable on a staged dump; permission-dialog routing end to end
- [ ] 7.2 Confirm no new dependency introduced (grep pyproject; Pillow already present)
- [ ] 7.3 Run `/rv-qa-lint-fix rv-agent`
- [ ] 7.4 Run `/rv-verify rv-agent`
- [ ] 7.5 Invoke `/rv-code-reviewer` via Skill tool for the gh78 implementation
- [ ] 7.6 Run `/opsx:verify gh78-state-identity-robustness`
