<!-- All groups are independent and can run sequentially. Total: ~12 files touched. -->

## 1. Config Defaults

- [x] 1.1 Change `DEFAULT_TARPIT_THRESHOLD` from 15 to 50 in `Config.java`
- [x] 1.2 Change `DEFAULT_RETRY_SATURATION_THRESHOLD` from 0.8f to 0.95f in `Config.java`
- [x] 1.3 Update `ConfigTest.java`: `testRetrySaturationThresholdDefaultIs0_8` → assert 0.95f
- [x] 1.4 Update `ConfigTest.java`: `tarpitThresholdDefault` → assert 50

## 2. PhaseController: Fix Premature PHASE_3 Transition (Bug 1)

- [x] 2.1 In `PhaseController.hasUntestedActionsInAnyReachableState()`, filter BACK/RESTART signatures from `executedActions` before comparing against `totalActions`. Filter signatures starting with "back@" or "restart@".
- [x] 2.2 Raise `CLUSTER_FORCE_THRESHOLD` from 20 to 50 in `PhaseController.java` (Bug 4)
- [x] 2.3 Add unit test `PhaseControllerTest.testSystemActionsExcludedFromUntestedCheck` — verify that BACK/RESTART signatures are not counted in the untested check
- [x] 2.4 Add unit test `PhaseControllerTest.testClusterForceThresholdIs50` — verify the new threshold value

## 3. TarpitDetector: Add hadEffect Reset (Bug 2)

- [x] 3.1 Add `hadEffect` boolean parameter to `TarpitDetector.recordIteration()`. Reset counter when `hadEffect=true` (in addition to existing reset conditions: hashChanged, hasNewState, hasNewMop).
- [x] 3.2 Update `AgentLoop` caller of `tarpitDetector.recordIteration()` to pass `hadEffect` (computed from pre/post action hash comparison, already available in the iteration logic).
- [x] 3.3 Add unit test `TarpitDetectorTest.testResetOnHadEffect` — verify counter resets when hadEffect=true
- [x] 3.4 Add unit test `TarpitDetectorTest.testThreshold50` — verify tarpit fires at 50 iterations, not 15
- [x] 3.5 Update any existing TarpitDetector tests that call recordIteration() with 3 args to pass the 4th arg

## 4. AgentLoop: Fix Retry Saturation Gate (Bug 3)

- [x] 4.1 Verify the retry gate in `AgentLoop` uses `config.getRetrySaturationThreshold()` (should already — just confirm the Config default change in Group 1 is sufficient)

## 5. Build and Validate

- [x] 5.1 Run `mvn test` in the rvsmart project to ensure all existing + new tests pass
- [x] 5.2 Run `mvn install` to rebuild the JAR and copy to `modules/rvsmart-tool/src/rvsmart_tool/tools/rvsmart/rvsmart.jar`
