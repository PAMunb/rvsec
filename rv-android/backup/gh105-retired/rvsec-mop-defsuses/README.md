# rvsec-mop-defsuses

Definitions-uses analysis for MOP specification properties.

## Purpose

Analyzes `.mop` specifications to extract definition and use points of monitored
properties. This information supports the static analysis pipeline by identifying
which code locations define or consume values relevant to runtime verification
properties (e.g., where a Cipher key is defined vs where it is used for encryption).

## Build

```bash
mvn clean install
```

## Dependencies

- `rvsec-mop-extractor`: MOP method signature extraction
