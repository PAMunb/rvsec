# rvsec-mop

MOP (Monitoring-Oriented Programming) specification files for runtime verification
of Android applications.

## Purpose

Contains 168 `.mop` specification files defining properties to monitor at runtime.
These specs are compiled by `mop-maven-plugin` into runtime monitors that detect
API misuse patterns during application execution.

## Specification Sets

### JCA (Java Cryptography Architecture) — 23 specs

Detect misuse of JCA cryptographic APIs:
- Cipher initialization without proper mode/padding
- Key generation with weak parameters
- SecureRandom not properly seeded
- MessageDigest used for password hashing
- SSLContext with permissive TrustManager

Example spec (`CipherSpec.mop`):
```
CipherSpec(Cipher c) {
    event init after(Cipher c) : call(* Cipher.init(int, ..)) && target(c) {}
    event encrypt after(Cipher c) : call(* Cipher.doFinal(..)) && target(c) {}

    ere: init encrypt+

    @fail { System.err.println("[RVSEC] Cipher used without init"); }
}
```

### Generic FSM — 118 specs

Detect violations of general Java API usage patterns:
- Iterator: must call `hasNext()` before `next()`
- Streams: must be closed after use
- Collections: no modification during iteration
- Thread safety: synchronized access patterns

### Generic New — 27 specs

Additional API patterns added for Android-specific verification.

## Directory Structure

```
src/main/resources/
    jca/           — JCA cryptographic specs (23 files)
    generic/       — General API pattern specs (118 files)
    generic_new/   — Additional Android specs (27 files)
```

## Build

Specs are compiled automatically during `mvn install` via `mop-maven-plugin`:

```bash
cd rvsec
mvn clean install -DskipTests
```

The compilation pipeline: `.mop` -> JavaMOP -> `.rvm` -> RV-Monitor -> Java aspects.
