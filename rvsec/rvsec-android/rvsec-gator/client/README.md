# GATOR Client — RVSec Static Analysis

Unified GATOR analysis client that produces a single JSON file containing reachability,
windows, and transitions data for Android applications. This JSON is consumed by the
Python `rv-static-analysis` module in rv-android.

## Purpose

The GATOR client extends the [GATOR](https://github.com/nicetester/gator) static analysis
framework (sootandroid) with an RVSec-specific analysis client (`RvsecAnalysisClient`)
that produces structured JSON output for the rv-android testing framework. It replaces
three separate tools (GESDA, GATOR WTG Client, REACH) with a unified pipeline.

## Architecture

```
sootandroid (GATOR server)    →  RvsecAnalysisClient (our client)  →  JSON output
   - Soot/CallGraph                - Class enumeration                  - reachability{}
   - WTG construction              - MOP signature resolution           - windows{}
   - GUI analysis                  - Multi-source BFS                   - transitions{}
                                   - WTG edge extraction                - components{}
```

### Analysis Pipeline

1. **Class enumeration**: Filter application classes by package name
2. **MOP signature loading**: Load monitored operation signatures from `.mop` spec files
3. **Reachability analysis**: Multi-source BFS on Soot CallGraph (forward from entry points,
   reverse from MOP methods) using JGraphT
4. **WTG construction**: Build Window Transition Graph via GATOR's WTGBuilder
5. **JSON output**: Write sections in priority order (reachability first, then windows,
   transitions, components) with flush between each section

### JSON Output Format

```json
{
  "package": "com.example.app",
  "mainActivity": "com.example.app.MainActivity",
  "reachability": [
    {
      "className": "com.example.app.CryptoHelper",
      "methods": [
        {
          "name": "encrypt",
          "signature": "void encrypt(byte[])",
          "reachable": true,
          "reachesMop": true,
          "directlyReachesMop": false
        }
      ]
    }
  ],
  "windows": [...],
  "transitions": [...],
  "components": {
    "broadcasts": [...],
    "services": [...],
    "activities": [...]
  }
}
```

### Priority-Ordered Sections

Sections are written in priority order with flush between each. On timeout, partial
JSON preserves the most critical data first:

1. **reachability** — Coverage denominator (most critical for rv-coverage)
2. **windows** — Widget inventory (needed for MOP scoring in APE-RV)
3. **transitions** — WTG edges (needed for navigation guidance)
4. **components** — Broadcast receivers, services (needed for component triggering)

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
    RvsecAnalysisClient.java     — Main analysis client (unified pipeline)
    wtg/model/
      Event.java                 — WTG event types
      Window.java                — Window (activity/dialog) model
      Result.java                — Analysis result container
      Transition.java            — WTG edge model
    wtg/writer/
      Writer.java                — JSON serialization
  src/test/java/                 — Unit and integration tests

commons/
  src/main/java/presto/android/
    Timer.java                   — Execution timing utility
    Logger.java                  — Structured logging
```

## Key Classes

### RvsecAnalysisClient

Main analysis client implementing `GUIAnalysisClient`. Orchestrates the full pipeline:
class enumeration, MOP resolution, BFS reachability, WTG construction, JSON output.
Uses multi-source BFS on JGraphT `DefaultDirectedGraph` for efficient reachability.

### WTG Model (Event, Window, Result, Transition)

Domain model for Window Transition Graph data. `Window` represents an activity or
dialog. `Transition` represents a UI event that navigates between windows. `Event`
captures the trigger type (click, menu, etc.). `Result` wraps the complete analysis output.

### Writer

JSON serialization using Gson `JsonWriter`. Writes sections in priority order with
explicit flush calls to ensure partial output on timeout.
