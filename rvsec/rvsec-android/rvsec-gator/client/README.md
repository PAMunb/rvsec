# GATOR Client — RVSec Static Analysis

Unified GATOR analysis client that produces a single JSON file containing components,
reachability, windows, and transitions data for Android applications. This JSON is
consumed by the Python `rv-static-analysis` module in rv-android.

## Purpose

The GATOR client extends the [GATOR](https://github.com/nicetester/gator) static analysis
framework (sootandroid) with an RVSec-specific analysis client, decomposed into an
orchestrator (`RvsecAnalysisClient`) plus `target/` (`TargetResolver`,
`MopSpecsTargetSource`, `SignatureFileTargetSource`), `reach/` (`ReachabilityEngine`,
`ReachabilityIndex`, `ReachabilityEnricher`), and `json/` (`JsonReportWriter`,
`JsonSchema`) packages, that produces structured JSON output for the rv-android testing
framework. It replaces three separate tools (GESDA, GATOR WTG Client, REACH) with a
unified pipeline.

## Architecture

```
sootandroid (GATOR server)    →  RvsecAnalysisClient (our client)  →  JSON output
   - Soot/CallGraph                - Class enumeration                  - components{}
   - WTG construction              - MOP signature resolution           - reachability{}
   - GUI analysis                  - Multi-source BFS                   - windows{}
                                   - WTG edge extraction                - transitions{}
                                                                          - complete
```

### Analysis Pipeline

1. **Class enumeration**: Filter application classes by package name
2. **MOP signature loading**: Load monitored operation signatures from `.mop` spec files
3. **Reachability analysis**: Multi-source BFS on Soot CallGraph (forward from entry points,
   reverse from MOP methods) using JGraphT
4. **WTG construction**: Build Window Transition Graph via GATOR's WTGBuilder
5. **JSON output**: Write sections in priority order (components first, then reachability,
   windows, transitions), with flush between each section and a `"complete": true`
   sentinel written last for partial-output recovery on timeout

### JSON Output Format

```json
{
  "package": "com.example.app",
  "mainActivity": "com.example.app.MainActivity",
  "components": {
    "broadcasts": [...],
    "services": [...],
    "activities": [...]
  },
  "reachability": [
    {
      "className": "com.example.app.CryptoHelper",
      "methods": [
        {
          "name": "encrypt",
          "signature": "void encrypt(byte[])",
          "reachable": true,
          "reachesTarget": true,
          "directlyReachesTarget": false
        }
      ]
    }
  ],
  "windows": [...],
  "transitions": [...],
  "complete": true
}
```

### Priority-Ordered Sections

Sections are written in priority order with flush between each. On timeout, partial
JSON preserves the most critical data first:

1. **components** — Broadcast receivers, services, activities (manifest-derived, cheap;
   promoted first so a transitions timeout cannot drop the windows->activity lookup)
2. **reachability** — Coverage denominator (most critical for rv-coverage)
3. **windows** — Widget inventory (needed for MOP scoring in APE-RV)
4. **transitions** — WTG edges (needed for navigation guidance)

A final `"complete": true` sentinel is written last; its absence signals the parser that
the sample is incomplete (e.g. a WTG timeout truncated the run).

## Integration with rv-android

The JSON output is consumed by these Python modules:

| Consumer | Section | Purpose |
|----------|---------|---------|
| `rv-static-analysis` | All | Parses JSON into StaticAnalysisData domain model |
| `rv-coverage` | reachability | Uses as coverage denominator (total methods to cover) |
| `aperv-tool` | All (pushed to device) | APE-RV reads for MOP scoring and WTG navigation |
| `rv-agent` | reachability, windows | Navigation guidance and MOP prioritization |

## Build

Built as part of the rvsec-gator Maven module:

```bash
cd rvsec-gator
mvn package -DskipTests
```

The client is packaged into the GATOR JAR along with the sootandroid server.

## Source Structure

```
client/
  src/main/java/presto/android/gui/clients/
    RvsecAnalysisClient.java     — Orchestrator (class enumeration, MOP resolution,
                                    section writer entry points)
    target/
      TargetResolver.java             — Resolves target methods (MOP/JCA)
      MopSpecsTargetSource.java       — Loads targets from .mop spec files
      SignatureFileTargetSource.java  — Loads targets from a signature file
    reach/
      ReachabilityEngine.java         — Multi-source BFS reachability
      ReachabilityIndex.java          — Reachability lookup structure
      ReachabilityEnricher.java       — Enriches methods with reachesTarget flags
    json/
      JsonReportWriter.java           — Section-ordered JSON writer + complete sentinel
      JsonSchema.java                 — Centralized JSON key constants (nested `.Keys`)
      JsonSchemaKeysDump.java         — Dumps schema keys for cross-checking
    MenuExtractor.java            — Menu widget extraction
    SpinnerItemExtractor.java     — Spinner widget extraction
    wtg/model/
      Event.java                 — WTG event types
      Window.java                — Window (activity/dialog) model
      Result.java                — Analysis result container
      Transition.java            — WTG edge model
    wtg/writer/
      Writer.java                — legacy, unreferenced (superseded by json/JsonReportWriter.java)
  src/test/java/                 — Unit and integration tests

commons/
  src/main/java/presto/android/
    Timer.java                   — Execution timing utility
    Logger.java                  — Structured logging
```

## Key Classes

### RvsecAnalysisClient

Orchestrator implementing `GUIAnalysisClient`. Drives the full pipeline (class
enumeration, target resolution, BFS reachability, WTG construction) and delegates JSON
output to `JsonReportWriter`. Uses multi-source BFS on JGraphT `DefaultDirectedGraph`
for efficient reachability.

### Target Resolution (target/)

`TargetResolver` resolves the set of target methods to track (JCA/MOP), sourced either
from `.mop` spec files (`MopSpecsTargetSource`) or a plain signature file
(`SignatureFileTargetSource`). Fields on resolved methods are named `reachesTarget` /
`directlyReachesTarget` (renamed from the earlier MOP-prefixed names).

### Reachability (reach/)

`ReachabilityEngine` runs the multi-source BFS; `ReachabilityIndex` holds the resulting
lookup structure; `ReachabilityEnricher` annotates methods with `reachesTarget` /
`directlyReachesTarget` flags for JSON output.

### WTG Model (Event, Window, Result, Transition)

Domain model for Window Transition Graph data. `Window` represents an activity or
dialog. `Transition` represents a UI event that navigates between windows. `Event`
captures the trigger type (click, menu, etc.). `Result` wraps the complete analysis output.

### JsonReportWriter (json/)

JSON serialization using Gson `JsonWriter`. Writes sections in priority order
(`components → reachability → windows → transitions`) with explicit flush calls between
each, then emits the `"complete": true` sentinel last to enable partial-output recovery
on timeout.
