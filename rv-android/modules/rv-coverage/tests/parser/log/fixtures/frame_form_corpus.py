"""Shared corner-case corpus for stack-frame (frame-form) parsing — gh89, issue #89.

Every value below is taken verbatim from the frozen 2026-07-06 dataset
(``ase-journal/dataset/results/errors.csv`` and ``errors_unit_tests.csv``) unless it is
marked synthetic. The Java monitor (``ErrorDescription``) and this Python parser
(``logcat_parser._normalize_frame``) implement the *same* algorithm, so they are tested
against the *same* values: this list is mirrored, line for line, by
``rvsec/rvsec-core/src/test/resources/frame-form-corpus.txt`` in the sibling ``rvsec``
reactor. ``test_frame_form_corpus_parity`` asserts the two agree whenever that repository
is present, so a case added on one side and forgotten on the other fails a test rather than
passing review.

``FRAME_FORM_CASES`` holds values that MUST be normalized, as
``(value, expected_class, expected_method, expected_source)``. ``PASS_THROUGH_CASES`` holds
values that MUST NOT be touched — normalization returns ``None`` and the caller keeps its
fields byte-identical (INV-ANA-51).
"""

from typing import List, Tuple

FRAME_FORM_CASES: List[Tuple[str, str, str, str]] = [
    # Kotlin $-mangled internals (okio digest) - campaign data, 39018 rows
    (
        "okio.ByteString.digest$okio(ByteString.kt:83)",
        "okio.ByteString",
        "digest$okio",
        "ByteString.kt:83",
    ),
    (
        "okio.ByteString.digest$okio(ByteString.kt:84)",
        "okio.ByteString",
        "digest$okio",
        "ByteString.kt:84",
    ),
    (
        "okio.ByteString.digest$jvm(ByteString.kt:103)",
        "okio.ByteString",
        "digest$jvm",
        "ByteString.kt:103",
    ),
    # Kotlin lambda mangling ($lambda$N) - campaign data
    (
        "me.diamondforge.tokn.security.KeystoreManager.keystore_delegate$lambda$0(KeystoreManager.kt:23)",
        "me.diamondforge.tokn.security.KeystoreManager",
        "keystore_delegate$lambda$0",
        "KeystoreManager.kt:23",
    ),
    (
        "com.craxiom.networksurvey.util.CryptoManager.keyStore_delegate$lambda$0(CryptoManager.kt:31)",
        "com.craxiom.networksurvey.util.CryptoManager",
        "keyStore_delegate$lambda$0",
        "CryptoManager.kt:31",
    ),
    (
        "io.matthewnelson.kmp.tor.runtime.FileID$Companion.createFID$lambda$0(FileID.kt:57)",
        "io.matthewnelson.kmp.tor.runtime.FileID$Companion",
        "createFID$lambda$0",
        "FileID.kt:57",
    ),
    (
        "io.matthewnelson.kmp.tor.runtime.FileID$Companion.createFID$lambda$0(FileID.kt:58)",
        "io.matthewnelson.kmp.tor.runtime.FileID$Companion",
        "createFID$lambda$0",
        "FileID.kt:58",
    ),
    # Kotlin inline-class hyphen mangling - campaign data
    (
        "io.ktor.util.DigestImpl.plusAssign-impl(CryptoJvm.kt:51)",
        "io.ktor.util.DigestImpl",
        "plusAssign-impl",
        "CryptoJvm.kt:51",
    ),
    (
        "io.ktor.util.DigestImpl.build-impl(CryptoJvm.kt:58)",
        "io.ktor.util.DigestImpl",
        "build-impl",
        "CryptoJvm.kt:58",
    ),
    (
        "dev.leonlatsch.photok.encryption.domain.ChangePasswordUseCase.invoke-gIAlu-s(ChangePasswordUseCase.kt:55)",
        "dev.leonlatsch.photok.encryption.domain.ChangePasswordUseCase",
        "invoke-gIAlu-s",
        "ChangePasswordUseCase.kt:55",
    ),
    # Robolectric shadow with double $$ - unit-test data, 186 rows
    (
        "android.os.SystemProperties.$$robo$$android_os_SystemProperties$digestOf(SystemProperties.java:318)",
        "android.os.SystemProperties",
        "$$robo$$android_os_SystemProperties$digestOf",
        "SystemProperties.java:318",
    ),
    (
        "android.os.SystemProperties.$$robo$$android_os_SystemProperties$digestOf(SystemProperties.java:320)",
        "android.os.SystemProperties",
        "$$robo$$android_os_SystemProperties$digestOf",
        "SystemProperties.java:320",
    ),
    (
        "android.os.SystemProperties.$$robo$$android_os_SystemProperties$digestOf(SystemProperties.java:330)",
        "android.os.SystemProperties",
        "$$robo$$android_os_SystemProperties$digestOf",
        "SystemProperties.java:330",
    ),
    (
        "android.os.SystemProperties.$$robo$$android_os_SystemProperties$digestOf(SystemProperties.java:332)",
        "android.os.SystemProperties",
        "$$robo$$android_os_SystemProperties$digestOf",
        "SystemProperties.java:332",
    ),
    (
        "android.os.SystemProperties.$$robo$$android_os_SystemProperties$digestOf(SystemProperties.java:350)",
        "android.os.SystemProperties",
        "$$robo$$android_os_SystemProperties$digestOf",
        "SystemProperties.java:350",
    ),
    (
        "android.os.SystemProperties.$$robo$$android_os_SystemProperties$digestOf(SystemProperties.java:352)",
        "android.os.SystemProperties",
        "$$robo$$android_os_SystemProperties$digestOf",
        "SystemProperties.java:352",
    ),
    # Kotlin backtick test names with spaces - unit-test data
    (
        "dev.leonlatsch.photok.encryption.crypto.CryptoEnginesTest.CBC engine decrypts V1-format files written by the 2xx app(CryptoEnginesTest.kt:135)",
        "dev.leonlatsch.photok.encryption.crypto.CryptoEnginesTest",
        "CBC engine decrypts V1-format files written by the 2xx app",
        "CryptoEnginesTest.kt:135",
    ),
    (
        "dev.leonlatsch.photok.encryption.crypto.CryptoEnginesTest.CBC engine decrypts V1-format files written by the 2xx app(CryptoEnginesTest.kt:136)",
        "dev.leonlatsch.photok.encryption.crypto.CryptoEnginesTest",
        "CBC engine decrypts V1-format files written by the 2xx app",
        "CryptoEnginesTest.kt:136",
    ),
    (
        "dev.leonlatsch.photok.encryption.integration.CryptoMigrationV1ToV3Test.migrated file has V2 header byte(CryptoMigrationV1ToV3Test.kt:90)",
        "dev.leonlatsch.photok.encryption.integration.CryptoMigrationV1ToV3Test",
        "migrated file has V2 header byte",
        "CryptoMigrationV1ToV3Test.kt:90",
    ),
    (
        "dev.leonlatsch.photok.encryption.integration.CryptoMigrationV1ToV3Test.migrated file has V2 header byte(CryptoMigrationV1ToV3Test.kt:91)",
        "dev.leonlatsch.photok.encryption.integration.CryptoMigrationV1ToV3Test",
        "migrated file has V2 header byte",
        "CryptoMigrationV1ToV3Test.kt:91",
    ),
    (
        "dev.leonlatsch.photok.encryption.integration.CryptoMigrationV2CompatibilityTest.CbcCryptoEngine decrypts a V1-header file produced by the 2xx format(CryptoMigrationV2CompatibilityTest.kt:69)",
        "dev.leonlatsch.photok.encryption.integration.CryptoMigrationV2CompatibilityTest",
        "CbcCryptoEngine decrypts a V1-header file produced by the 2xx format",
        "CryptoMigrationV2CompatibilityTest.kt:69",
    ),
    (
        "dev.leonlatsch.photok.encryption.integration.CryptoMigrationV2CompatibilityTest.CbcCryptoEngine decrypts a V1-header file produced by the 2xx format(CryptoMigrationV2CompatibilityTest.kt:70)",
        "dev.leonlatsch.photok.encryption.integration.CryptoMigrationV2CompatibilityTest",
        "CbcCryptoEngine decrypts a V1-header file produced by the 2xx format",
        "CryptoMigrationV2CompatibilityTest.kt:70",
    ),
    (
        "dev.leonlatsch.photok.encryption.integration.CryptoMigrationV2CompatibilityTest.CbcCryptoEngine decrypts a large V1-header file(CryptoMigrationV2CompatibilityTest.kt:97)",
        "dev.leonlatsch.photok.encryption.integration.CryptoMigrationV2CompatibilityTest",
        "CbcCryptoEngine decrypts a large V1-header file",
        "CryptoMigrationV2CompatibilityTest.kt:97",
    ),
    (
        "dev.leonlatsch.photok.encryption.integration.CryptoMigrationV2CompatibilityTest.CbcCryptoEngine decrypts a large V1-header file(CryptoMigrationV2CompatibilityTest.kt:98)",
        "dev.leonlatsch.photok.encryption.integration.CryptoMigrationV2CompatibilityTest",
        "CbcCryptoEngine decrypts a large V1-header file",
        "CryptoMigrationV2CompatibilityTest.kt:98",
    ),
    # Kotlin backtick test names with NESTED parentheses - unit-test data (INV-ANA-52)
    (
        "dev.leonlatsch.photok.encryption.integration.CryptoMigrationV2CompatibilityTest.V2-header files (3xx format) are still decryptable after reading a V1-header file(CryptoMigrationV2CompatibilityTest.kt:131)",
        "dev.leonlatsch.photok.encryption.integration.CryptoMigrationV2CompatibilityTest",
        "V2-header files (3xx format) are still decryptable after reading a V1-header file",
        "CryptoMigrationV2CompatibilityTest.kt:131",
    ),
    (
        "dev.leonlatsch.photok.encryption.integration.CryptoMigrationV2CompatibilityTest.V2-header files (3xx format) are still decryptable after reading a V1-header file(CryptoMigrationV2CompatibilityTest.kt:132)",
        "dev.leonlatsch.photok.encryption.integration.CryptoMigrationV2CompatibilityTest",
        "V2-header files (3xx format) are still decryptable after reading a V1-header file",
        "CryptoMigrationV2CompatibilityTest.kt:132",
    ),
    # Synthetic: JVM special method names (absent from the frozen data)
    (
        "com.example.Crypto.<init>(Crypto.java:15)",
        "com.example.Crypto",
        "<init>",
        "Crypto.java:15",
    ),
    (
        "com.example.Crypto.<clinit>(Crypto.java:9)",
        "com.example.Crypto",
        "<clinit>",
        "Crypto.java:9",
    ),
]

PASS_THROUGH_CASES: List[str] = [
    # Well-formed values already split by a corrected monitor - MUST pass through byte-identical
    "okhttp3.internal.platform.Platform",
    "newSSLContext",
    "okio.ByteString",
    "digest$okio",
    "V2-header files (3xx format) are still decryptable after reading a V1-header file",
    # Guard boundaries: a trailing group that is not a source position is NOT stripped
    "com.example.Crypto.getInstance(String)",
    "com.example.Foo.bar(Unknown Source)",
    "java.security.MessageDigest.getInstance(Native Method)",
    "com.example.Foo.bar(Foo.java:12) trailing text",
    # Guard hits but the remainder has no dot: refuse to mangle, keep the value (warns)
    "digest$okio(ByteString.kt:83)",
]
