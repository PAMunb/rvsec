## ADDED Requirements

### Requirement: APE Built-in Starts APE With the APE-RV Heap Growth Limit (FR19, NFR04)

`APETool.execute_tool_specific_logic()` SHALL set `dalvik.vm.heapgrowthlimit` to `APE_HEAP_GROWTH_LIMIT`
(`rv_android_core.constants`, `512m`) through `Android.set_ape_heap_growth_limit`, after the pushes and before
the `adb shell` command. When the read-back is not `512m`, APE SHALL NOT start (INV-TOOL-30). `aperv` makes the
same call in every cell, so `aperv:base` stays the APE in heap as in host time (INV-TOOL-27).

What is measured and what is only inferred about the heap: design D12.

#### Scenario: the limit is set before APE starts
- **WHEN** `APETool.execute_tool_specific_logic()` runs on `emulator-5554`
- **THEN** `adb -s emulator-5554 shell su 0 setprop dalvik.vm.heapgrowthlimit 512m` and then
  `adb -s emulator-5554 shell getprop dalvik.vm.heapgrowthlimit` SHALL run after the pushes of the jar and of
  `ape.properties`
- **AND** both SHALL run before the `app_process` command

#### Scenario: a limit that does not hold stops the task
- **WHEN** `getprop dalvik.vm.heapgrowthlimit` reads `192m` after the setprop
- **THEN** `RVToolExecutionError` SHALL be raised naming the value read back and the tool `ape`
- **AND** no `app_process` command SHALL be executed
