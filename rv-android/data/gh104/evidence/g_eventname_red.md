# Task 3.1 — `EventNameMacroTest` red before the generator emits `__EVENTNAME`

INV-INS-108: the test is written and run before the change that makes it pass.

- date: 2026-08-19T10:16:22-03:00
- generator commit under test: `41539390` (`rv-monitor/rv-monitor` untouched by gh104 at this point)
- JDK: $JAVA_HOME=$HOME/.sdkman/candidates/java/21.0.12-tem (`openjdk version "21.0.12" 2026-07-21 LTS`)
- command, from the reactor root `rvsec/`:

```
export JAVA_HOME=$HOME/.sdkman/candidates/java/21.0.12-tem; export PATH=$JAVA_HOME/bin:$PATH
mvn test -pl rv-monitor/rv-monitor -Dtest=EventNameMacroTest
```

## The red

The failure is a **test-compilation** failure, and that is the honest shape of the red here: the macro does not exist in any form, so the test names five generator members that are not there. Each missing symbol is one clause of INV-INS-120.

| missing member | the clause it carries |
|---|---|
| `BaseMonitor.expandEventNameToLiteral(String, String)` | `__EVENTNAME` in an **event body** becomes the string literal of the event name |
| `BaseMonitor.expandEventNameToHelperCall(String)` | `__EVENTNAME` in a **handler body** becomes the call `RVM_eventName()`, never a table lookup |
| `BaseMonitor.eventNameTableCode(List<String>)` | the per-class name table, indexed by the event index |
| `BaseMonitor.eventNameHelperCode(boolean, boolean)` | the per-class helper that decodes the last-event index **per monitor shape** |
| `Main.checkNoUnexpandedEventNameMacro(String, String)` | generation fails closed, naming file and line, if the literal survives |

Confirmation that the macro is genuinely absent from the generator today:

```
$ grep -rE '__EVENTNAME' rv-monitor/rv-monitor/src/main/java | wc -l
0
```

## Raw output

```
[ERROR] /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-monitor/rv-monitor/src/test/java/com/runtimeverification/rvmonitor/java/rvj/output/monitor/EventNameMacroTest.java:[74,38] cannot find symbol
  symbol:   method expandEventNameToLiteral(java.lang.String,java.lang.String)
  location: class com.runtimeverification.rvmonitor.java.rvj.output.monitor.BaseMonitor
[ERROR] /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-monitor/rv-monitor/src/test/java/com/runtimeverification/rvmonitor/java/rvj/output/monitor/EventNameMacroTest.java:[92,38] cannot find symbol
  symbol:   method expandEventNameToHelperCall(java.lang.String)
  location: class com.runtimeverification.rvmonitor.java.rvj.output.monitor.BaseMonitor
[ERROR] /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-monitor/rv-monitor/src/test/java/com/runtimeverification/rvmonitor/java/rvj/output/monitor/EventNameMacroTest.java:[109,17] cannot find symbol
  symbol:   method checkNoUnexpandedEventNameMacro(java.lang.String,java.lang.String)
  location: class com.runtimeverification.rvmonitor.java.rvj.Main
[ERROR] /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-monitor/rv-monitor/src/test/java/com/runtimeverification/rvmonitor/java/rvj/output/monitor/EventNameMacroTest.java:[123,13] cannot find symbol
  symbol:   method checkNoUnexpandedEventNameMacro(java.lang.String,java.lang.String)
  location: class com.runtimeverification.rvmonitor.java.rvj.Main
[ERROR] /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-monitor/rv-monitor/src/test/java/com/runtimeverification/rvmonitor/java/rvj/output/monitor/EventNameMacroTest.java:[131,35] cannot find symbol
  symbol:   method eventNameTableCode(java.util.List<java.lang.String>)
  location: class com.runtimeverification.rvmonitor.java.rvj.output.monitor.BaseMonitor
[ERROR] /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-monitor/rv-monitor/src/test/java/com/runtimeverification/rvmonitor/java/rvj/output/monitor/EventNameMacroTest.java:[236,30] cannot find symbol
  symbol:   method eventNameTableCode(java.util.List<java.lang.String>)
  location: class com.runtimeverification.rvmonitor.java.rvj.output.monitor.BaseMonitor
[ERROR] /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-monitor/rv-monitor/src/test/java/com/runtimeverification/rvmonitor/java/rvj/output/monitor/EventNameMacroTest.java:[237,30] cannot find symbol
  symbol:   method eventNameHelperCode(boolean,boolean)
  location: class com.runtimeverification.rvmonitor.java.rvj.output.monitor.BaseMonitor
[INFO] BUILD FAILURE
[ERROR] /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-monitor/rv-monitor/src/test/java/com/runtimeverification/rvmonitor/java/rvj/output/monitor/EventNameMacroTest.java:[74,38] cannot find symbol
[ERROR] /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-monitor/rv-monitor/src/test/java/com/runtimeverification/rvmonitor/java/rvj/output/monitor/EventNameMacroTest.java:[92,38] cannot find symbol
[ERROR] /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-monitor/rv-monitor/src/test/java/com/runtimeverification/rvmonitor/java/rvj/output/monitor/EventNameMacroTest.java:[109,17] cannot find symbol
[ERROR] /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-monitor/rv-monitor/src/test/java/com/runtimeverification/rvmonitor/java/rvj/output/monitor/EventNameMacroTest.java:[123,13] cannot find symbol
[ERROR] /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-monitor/rv-monitor/src/test/java/com/runtimeverification/rvmonitor/java/rvj/output/monitor/EventNameMacroTest.java:[131,35] cannot find symbol
[ERROR] /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-monitor/rv-monitor/src/test/java/com/runtimeverification/rvmonitor/java/rvj/output/monitor/EventNameMacroTest.java:[236,30] cannot find symbol
[ERROR] /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-monitor/rv-monitor/src/test/java/com/runtimeverification/rvmonitor/java/rvj/output/monitor/EventNameMacroTest.java:[237,30] cannot find symbol
```
