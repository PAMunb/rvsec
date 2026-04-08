# rvsec-mop-extractor

Extracts method signatures from `.mop` specification files for use in static analysis.

## Purpose

Parses MOP specifications to extract the Java method signatures being monitored
(e.g., `javax.crypto.Cipher.init`, `java.security.SecureRandom.setSeed`). These
signatures are used by the GATOR client (`RvsecAnalysisClient`) to determine which
application methods transitively reach monitored APIs (MOP reachability analysis).

## Key Class

- **JavamopFacade**: Loads `.mop` files and extracts `MopMethod` instances containing
  the class name, method name, and parameter types of each monitored API call.

## Integration

```
.mop specs (rvsec-mop)
    -> JavamopFacade (this module)
    -> Set<MopMethod> signatures
    -> RvsecAnalysisClient (rvsec-gator/client)
    -> Reachability BFS marks methods reaching MOP signatures
```

## Build

```bash
mvn clean install
```
