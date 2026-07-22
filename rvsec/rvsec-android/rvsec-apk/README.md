# rvsec-apk

APK metadata extraction utilities for the RVSec framework.

## Purpose

Provides utilities for reading and processing Android APK metadata: package names,
component declarations (activities, services, receivers), permissions, and manifest
parsing. Used by the static analysis pipeline to enumerate application components
before GATOR analysis.

## Key Components

- APK manifest reader
- Package name extraction
- Component enumeration (activities, services, broadcast receivers, content providers)
- Apktool integration for APK decompilation

## Build

```bash
mvn clean install
```

## Dependencies

- Apktool (for APK decompilation)
- Gson (for JSON serialization)
