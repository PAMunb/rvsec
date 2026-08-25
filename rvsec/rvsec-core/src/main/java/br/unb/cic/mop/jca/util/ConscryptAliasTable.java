package br.unb.cic.mop.jca.util;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * What a JCA algorithm string denotes on Android 11, when the string the
 * application passes is not the name the api30 CrySL rule writes.
 *
 * <p>The allow-lists of the {@code jca_android} specification set are literal
 * transcriptions of the {@code CONSTRAINTS} clauses of the pinned expert copy
 * {@code RVSec-replication-package/tools/rules/} (D-15; they were transcriptions
 * of {@code MetaCrySL/generated/api30/} until 2026-08-24). A literal transcription alone leaves
 * roughly three thousand of the measured events unmatched, because the rule
 * writes the JCA standard name and the application writes what the platform
 * provider registers: {@code X509} instead of {@code PKIX},
 * {@code SHA1}/{@code SHA} instead of {@code SHA-1}, {@code SHA256WITHRSA}
 * instead of {@code SHA256withRSA}, an OID instead of a name.
 *
 * <p>So the set declares one normalisation rule and applies it uniformly:
 * <b>comparison is case-insensitive</b>, and an observed value matches a list
 * entry when a row of this table maps it to that entry. Every row carries its
 * primary source -- a line of Conscrypt {@code OpenSSLProvider.java} on branch
 * {@code android11-release} -- and a spelling that no registration in that file
 * explains gets no row at all. The one measured case of that kind is
 * {@code RSA/ECB/OAEPWithSHA1AndMGF1Padding}, unhyphenated, which Conscrypt
 * registers only in its hyphenated form; it is recorded in
 * {@code data/jca_android/divergence_record.csv} with behavioural evidence
 * instead of being normalised here.
 *
 * <p>The table lives here as code and is never read from a file at run time: a
 * monitor woven into an APK has no filesystem contract with this repository, and
 * a specification whose verdict depended on a CSV nobody ships would not be
 * checkable. {@code data/jca_android/alias_table.csv} is the auditable registry
 * of the same 175 rows, and {@code ConscryptAliasTableTest} asserts the two are
 * equal row for row so they cannot drift. The count was 158 until task 11.6
 * (D-15) added the eleven multi-line {@code Alg.Alias} registrations a
 * single-line extraction had missed, and 169 until gh105 task 9.8 added the six
 * the extraction had skipped by service: the five {@code KeyFactory} OIDs
 * ({@code OpenSSLProvider.java:195-197}, {@code :200-201}) and
 * {@code CertificateFactory X.509 -> X509} ({@code :500}). The table now holds
 * every one of the 175 {@code Alg.Alias} registrations of the pinned file, which
 * is what makes the completeness claim below checkable rather than asserted.
 *
 * <p>Each {@code jca_android} specification names this class in its allow-list
 * check. No specification of the frozen {@code jca} names it, so no verdict of
 * the frozen set moves because this class exists.
 *
 * <p>Two limits of the table, stated because a table that hides them invites
 * false confidence. {@code KeyStore} has no alias coverage here:
 * {@code AndroidKeyStore} comes from {@code AndroidKeyStoreProvider} and
 * {@code BKS}/{@code BouncyCastle} from Bouncy Castle, neither of which is this
 * file. And {@code SSLContext.SSL} and {@code SSLContext.TLS}
 * ({@code OpenSSLProvider.java:80-81}) point at the same implementation class
 * but are not {@code Alg.Alias} registrations, so they are behavioural
 * equivalence rather than table rows.
 *
 * <p>The column {@code inApi30Allowlist} has one definition: {@code yes} when
 * the row's canonical name is an entry of the successor set's allow-list for
 * that service. From D-15 (2026-08-24) those lists are the expert-validated
 * ones, so the flag was recomputed against them and 65 rows changed: the
 * aliases whose canonical name is {@code SHA-1}, {@code MD5withRSA},
 * {@code ARC4} and their relatives now read {@code no}, which is the direction
 * that matters -- an alias row resolving to a name the expert list rejects makes
 * the accusation reach the calls that spell it otherwise, rather than excusing
 * them. A row in a service no specification of the set covers
 * ({@code AlgorithmParameters}, {@code SecretKeyFactory}, {@code KeyFactory},
 * {@code CertificateFactory}) is {@code no}, because there is no list for it to be
 * an entry of; it is kept in the table so that the extraction stays complete. No
 * specification calls {@link #matches} with any of those four services, so their
 * rows move no verdict -- they are there so the registry can be audited against
 * the provider file by count as well as by row. It is a property of the record, not an input to
 * {@link #matches}: resolution never consults it.
 */
public final class ConscryptAliasTable {

    /** service, alias, canonical, OpenSSLProvider.java line, inApi30Allowlist. */
    private static final String[][] ROWS = {
        { "AlgorithmParameters", "2.16.840.1.101.3.4.1.2", "AES", "95", "no" },
        { "AlgorithmParameters", "2.16.840.1.101.3.4.1.22", "AES", "96", "no" },
        { "AlgorithmParameters", "2.16.840.1.101.3.4.1.42", "AES", "97", "no" },
        { "AlgorithmParameters", "TDEA", "DESEDE", "102", "no" },
        { "AlgorithmParameters", "1.2.840.113549.3.7", "DESEDE", "103", "no" },
        { "AlgorithmParameters", "2.16.840.1.101.3.4.1.6", "GCM", "106", "no" },
        { "AlgorithmParameters", "2.16.840.1.101.3.4.1.26", "GCM", "107", "no" },
        { "AlgorithmParameters", "2.16.840.1.101.3.4.1.46", "GCM", "108", "no" },
        { "CertificateFactory", "X.509", "X509", "500", "no" },
        { "Cipher", "RSA/None/NoPadding", "RSA/ECB/NoPadding", "332", "no" },
        { "Cipher", "RSA/None/PKCS1Padding", "RSA/ECB/PKCS1Padding", "334", "no" },
        { "Cipher", "RSA/None/OAEPPadding", "RSA/ECB/OAEPPadding", "337", "no" },
        { "Cipher", "RSA/None/OAEPWithSHA-1AndMGF1Padding", "RSA/ECB/OAEPWithSHA-1AndMGF1Padding", "339", "no" },
        { "Cipher", "RSA/None/OAEPWithSHA-224AndMGF1Padding", "RSA/ECB/OAEPWithSHA-224AndMGF1Padding", "343", "yes" },
        { "Cipher", "RSA/None/OAEPWithSHA-256AndMGF1Padding", "RSA/ECB/OAEPWithSHA-256AndMGF1Padding", "347", "yes" },
        { "Cipher", "RSA/None/OAEPWithSHA-384AndMGF1Padding", "RSA/ECB/OAEPWithSHA-384AndMGF1Padding", "351", "yes" },
        { "Cipher", "RSA/None/OAEPWithSHA-512AndMGF1Padding", "RSA/ECB/OAEPWithSHA-512AndMGF1Padding", "355", "yes" },
        { "Cipher", "AES/ECB/PKCS7Padding", "AES/ECB/PKCS5Padding", "375", "no" },
        { "Cipher", "AES/CBC/PKCS7Padding", "AES/CBC/PKCS5Padding", "380", "no" },
        { "Cipher", "AES_128/ECB/PKCS7Padding", "AES_128/ECB/PKCS5Padding", "387", "no" },
        { "Cipher", "AES_128/CBC/PKCS7Padding", "AES_128/CBC/PKCS5Padding", "392", "no" },
        { "Cipher", "PBEWithHmacSHA1AndAES_128", "AES_128/CBC/PKCS5PADDING", "394", "no" },
        { "Cipher", "PBEWithHmacSHA224AndAES_128", "AES_128/CBC/PKCS5PADDING", "395", "no" },
        { "Cipher", "PBEWithHmacSHA256AndAES_128", "AES_128/CBC/PKCS5PADDING", "396", "no" },
        { "Cipher", "PBEWithHmacSHA384AndAES_128", "AES_128/CBC/PKCS5PADDING", "397", "no" },
        { "Cipher", "PBEWithHmacSHA512AndAES_128", "AES_128/CBC/PKCS5PADDING", "398", "no" },
        { "Cipher", "AES_256/ECB/PKCS7Padding", "AES_256/ECB/PKCS5Padding", "404", "no" },
        { "Cipher", "AES_256/CBC/PKCS7Padding", "AES_256/CBC/PKCS5Padding", "409", "no" },
        { "Cipher", "PBEWithHmacSHA1AndAES_256", "AES_256/CBC/PKCS5PADDING", "411", "no" },
        { "Cipher", "PBEWithHmacSHA224AndAES_256", "AES_256/CBC/PKCS5PADDING", "412", "no" },
        { "Cipher", "PBEWithHmacSHA256AndAES_256", "AES_256/CBC/PKCS5PADDING", "413", "no" },
        { "Cipher", "PBEWithHmacSHA384AndAES_256", "AES_256/CBC/PKCS5PADDING", "414", "no" },
        { "Cipher", "PBEWithHmacSHA512AndAES_256", "AES_256/CBC/PKCS5PADDING", "415", "no" },
        { "Cipher", "DESEDE/CBC/PKCS7Padding", "DESEDE/CBC/PKCS5Padding", "421", "no" },
        { "Cipher", "ARCFOUR", "ARC4", "424", "no" },
        { "Cipher", "RC4", "ARC4", "425", "no" },
        { "Cipher", "1.2.840.113549.3.4", "ARC4", "426", "no" },
        { "Cipher", "OID.1.2.840.113549.3.4", "ARC4", "427", "no" },
        { "Cipher", "GCM", "AES/GCM/NoPadding", "430", "no" },
        { "Cipher", "2.16.840.1.101.3.4.1.6", "AES/GCM/NoPadding", "431", "no" },
        { "Cipher", "2.16.840.1.101.3.4.1.26", "AES/GCM/NoPadding", "432", "no" },
        { "Cipher", "2.16.840.1.101.3.4.1.46", "AES/GCM/NoPadding", "433", "no" },
        { "Cipher", "ChaCha20-Poly1305", "ChaCha20/Poly1305/NoPadding", "449", "no" },
        { "KeyFactory", "1.2.840.113549.1.1.1", "RSA", "195", "no" },
        { "KeyFactory", "1.2.840.113549.1.1.7", "RSA", "196", "no" },
        { "KeyFactory", "2.5.8.1.1", "RSA", "197", "no" },
        { "KeyFactory", "1.2.840.10045.2.1", "EC", "200", "no" },
        { "KeyFactory", "1.3.133.16.840.63.0.2", "EC", "201", "no" },
        { "KeyGenerator", "RC4", "ARC4", "141", "no" },
        { "KeyGenerator", "1.2.840.113549.3.4", "ARC4", "142", "no" },
        { "KeyGenerator", "TDEA", "DESEDE", "149", "no" },
        { "KeyGenerator", "1.3.6.1.5.5.8.1.1", "HmacMD5", "152", "no" },
        { "KeyGenerator", "HMAC-MD5", "HmacMD5", "153", "no" },
        { "KeyGenerator", "HMAC/MD5", "HmacMD5", "154", "no" },
        { "KeyGenerator", "1.2.840.113549.2.7", "HmacSHA1", "157", "no" },
        { "KeyGenerator", "1.3.6.1.5.5.8.1.2", "HmacSHA1", "158", "no" },
        { "KeyGenerator", "HMAC-SHA1", "HmacSHA1", "159", "no" },
        { "KeyGenerator", "HMAC/SHA1", "HmacSHA1", "160", "no" },
        { "KeyGenerator", "1.2.840.113549.2.8", "HmacSHA224", "163", "no" },
        { "KeyGenerator", "HMAC-SHA224", "HmacSHA224", "164", "no" },
        { "KeyGenerator", "HMAC/SHA224", "HmacSHA224", "165", "no" },
        { "KeyGenerator", "1.2.840.113549.2.9", "HmacSHA256", "168", "yes" },
        { "KeyGenerator", "2.16.840.1.101.3.4.2.1", "HmacSHA256", "169", "yes" },
        { "KeyGenerator", "HMAC-SHA256", "HmacSHA256", "170", "yes" },
        { "KeyGenerator", "HMAC/SHA256", "HmacSHA256", "171", "yes" },
        { "KeyGenerator", "1.2.840.113549.2.10", "HmacSHA384", "174", "yes" },
        { "KeyGenerator", "HMAC-SHA384", "HmacSHA384", "175", "yes" },
        { "KeyGenerator", "HMAC/SHA384", "HmacSHA384", "176", "yes" },
        { "KeyGenerator", "1.2.840.113549.2.11", "HmacSHA512", "179", "yes" },
        { "KeyGenerator", "HMAC-SHA512", "HmacSHA512", "180", "yes" },
        { "KeyGenerator", "HMAC/SHA512", "HmacSHA512", "181", "yes" },
        { "KeyPairGenerator", "1.2.840.113549.1.1.1", "RSA", "185", "yes" },
        { "KeyPairGenerator", "1.2.840.113549.1.1.7", "RSA", "186", "yes" },
        { "KeyPairGenerator", "2.5.8.1.1", "RSA", "187", "yes" },
        { "KeyPairGenerator", "1.2.840.10045.2.1", "EC", "190", "yes" },
        { "KeyPairGenerator", "1.3.133.16.840.63.0.2", "EC", "191", "yes" },
        { "Mac", "1.3.6.1.5.5.8.1.1", "HmacMD5", "454", "no" },
        { "Mac", "HMAC-MD5", "HmacMD5", "455", "no" },
        { "Mac", "HMAC/MD5", "HmacMD5", "456", "no" },
        { "Mac", "1.2.840.113549.2.7", "HmacSHA1", "463", "no" },
        { "Mac", "1.3.6.1.5.5.8.1.2", "HmacSHA1", "464", "no" },
        { "Mac", "HMAC-SHA1", "HmacSHA1", "465", "no" },
        { "Mac", "HMAC/SHA1", "HmacSHA1", "466", "no" },
        { "Mac", "1.2.840.113549.2.8", "HmacSHA224", "470", "no" },
        { "Mac", "HMAC-SHA224", "HmacSHA224", "471", "no" },
        { "Mac", "HMAC/SHA224", "HmacSHA224", "472", "no" },
        { "Mac", "PBEWITHHMACSHA224", "HmacSHA224", "473", "no" },
        { "Mac", "1.2.840.113549.2.9", "HmacSHA256", "477", "yes" },
        { "Mac", "2.16.840.1.101.3.4.2.1", "HmacSHA256", "478", "yes" },
        { "Mac", "HMAC-SHA256", "HmacSHA256", "479", "yes" },
        { "Mac", "HMAC/SHA256", "HmacSHA256", "480", "yes" },
        { "Mac", "PBEWITHHMACSHA256", "HmacSHA256", "481", "yes" },
        { "Mac", "1.2.840.113549.2.10", "HmacSHA384", "485", "yes" },
        { "Mac", "HMAC-SHA384", "HmacSHA384", "486", "yes" },
        { "Mac", "HMAC/SHA384", "HmacSHA384", "487", "yes" },
        { "Mac", "PBEWITHHMACSHA384", "HmacSHA384", "488", "yes" },
        { "Mac", "1.2.840.113549.2.11", "HmacSHA512", "492", "yes" },
        { "Mac", "HMAC-SHA512", "HmacSHA512", "493", "yes" },
        { "Mac", "HMAC/SHA512", "HmacSHA512", "494", "yes" },
        { "Mac", "PBEWITHHMACSHA512", "HmacSHA512", "495", "yes" },
        { "MessageDigest", "SHA1", "SHA-1", "115", "no" },
        { "MessageDigest", "SHA", "SHA-1", "116", "no" },
        { "MessageDigest", "1.3.14.3.2.26", "SHA-1", "117", "no" },
        { "MessageDigest", "SHA224", "SHA-224", "120", "no" },
        { "MessageDigest", "2.16.840.1.101.3.4.2.4", "SHA-224", "121", "no" },
        { "MessageDigest", "SHA256", "SHA-256", "124", "yes" },
        { "MessageDigest", "2.16.840.1.101.3.4.2.1", "SHA-256", "125", "yes" },
        { "MessageDigest", "SHA384", "SHA-384", "128", "yes" },
        { "MessageDigest", "2.16.840.1.101.3.4.2.2", "SHA-384", "129", "yes" },
        { "MessageDigest", "SHA512", "SHA-512", "132", "yes" },
        { "MessageDigest", "2.16.840.1.101.3.4.2.3", "SHA-512", "133", "yes" },
        { "MessageDigest", "1.2.840.113549.2.5", "MD5", "137", "no" },
        { "SecretKeyFactory", "TDEA", "DESEDE", "205", "no" },
        { "Signature", "MD5withRSAEncryption", "MD5withRSA", "212", "no" },
        { "Signature", "MD5/RSA", "MD5withRSA", "213", "no" },
        { "Signature", "1.2.840.113549.1.1.4", "MD5withRSA", "214", "no" },
        { "Signature", "OID.1.2.840.113549.1.1.4", "MD5withRSA", "215", "no" },
        { "Signature", "1.2.840.113549.2.5with1.2.840.113549.1.1.1", "MD5withRSA", "216", "no" },
        { "Signature", "SHA1withRSAEncryption", "SHA1withRSA", "219", "no" },
        { "Signature", "SHA1/RSA", "SHA1withRSA", "220", "no" },
        { "Signature", "SHA-1/RSA", "SHA1withRSA", "221", "no" },
        { "Signature", "1.2.840.113549.1.1.5", "SHA1withRSA", "222", "no" },
        { "Signature", "OID.1.2.840.113549.1.1.5", "SHA1withRSA", "223", "no" },
        { "Signature", "1.3.14.3.2.26with1.2.840.113549.1.1.1", "SHA1withRSA", "224", "no" },
        { "Signature", "1.3.14.3.2.26with1.2.840.113549.1.1.5", "SHA1withRSA", "225", "no" },
        { "Signature", "1.3.14.3.2.29", "SHA1withRSA", "226", "no" },
        { "Signature", "OID.1.3.14.3.2.29", "SHA1withRSA", "227", "no" },
        { "Signature", "SHA224withRSAEncryption", "SHA224withRSA", "230", "no" },
        { "Signature", "SHA224/RSA", "SHA224withRSA", "231", "no" },
        { "Signature", "1.2.840.113549.1.1.14", "SHA224withRSA", "232", "no" },
        { "Signature", "OID.1.2.840.113549.1.1.14", "SHA224withRSA", "233", "no" },
        { "Signature", "2.16.840.1.101.3.4.2.4with1.2.840.113549.1.1.1", "SHA224withRSA", "234", "no" },
        { "Signature", "2.16.840.1.101.3.4.2.4with1.2.840.113549.1.1.14", "SHA224withRSA", "236", "no" },
        { "Signature", "SHA256withRSAEncryption", "SHA256withRSA", "240", "yes" },
        { "Signature", "SHA256/RSA", "SHA256withRSA", "241", "yes" },
        { "Signature", "1.2.840.113549.1.1.11", "SHA256withRSA", "242", "yes" },
        { "Signature", "OID.1.2.840.113549.1.1.11", "SHA256withRSA", "243", "yes" },
        { "Signature", "2.16.840.1.101.3.4.2.1with1.2.840.113549.1.1.1", "SHA256withRSA", "244", "yes" },
        { "Signature", "2.16.840.1.101.3.4.2.1with1.2.840.113549.1.1.11", "SHA256withRSA", "246", "yes" },
        { "Signature", "SHA384withRSAEncryption", "SHA384withRSA", "250", "yes" },
        { "Signature", "SHA384/RSA", "SHA384withRSA", "251", "yes" },
        { "Signature", "1.2.840.113549.1.1.12", "SHA384withRSA", "252", "yes" },
        { "Signature", "OID.1.2.840.113549.1.1.12", "SHA384withRSA", "253", "yes" },
        { "Signature", "2.16.840.1.101.3.4.2.2with1.2.840.113549.1.1.1", "SHA384withRSA", "254", "yes" },
        { "Signature", "SHA512withRSAEncryption", "SHA512withRSA", "258", "yes" },
        { "Signature", "SHA512/RSA", "SHA512withRSA", "259", "yes" },
        { "Signature", "1.2.840.113549.1.1.13", "SHA512withRSA", "260", "yes" },
        { "Signature", "OID.1.2.840.113549.1.1.13", "SHA512withRSA", "261", "yes" },
        { "Signature", "2.16.840.1.101.3.4.2.3with1.2.840.113549.1.1.1", "SHA512withRSA", "262", "yes" },
        { "Signature", "ECDSA", "SHA1withECDSA", "270", "no" },
        { "Signature", "ECDSAwithSHA1", "SHA1withECDSA", "271", "no" },
        { "Signature", "1.2.840.10045.4.1", "SHA1withECDSA", "273", "no" },
        { "Signature", "1.3.14.3.2.26with1.2.840.10045.2.1", "SHA1withECDSA", "274", "no" },
        { "Signature", "SHA224/ECDSA", "SHA224withECDSA", "278", "no" },
        { "Signature", "1.2.840.10045.4.3.1", "SHA224withECDSA", "280", "no" },
        { "Signature", "OID.1.2.840.10045.4.3.1", "SHA224withECDSA", "281", "no" },
        { "Signature", "2.16.840.1.101.3.4.2.4with1.2.840.10045.2.1", "SHA224withECDSA", "282", "no" },
        { "Signature", "SHA256/ECDSA", "SHA256withECDSA", "286", "yes" },
        { "Signature", "1.2.840.10045.4.3.2", "SHA256withECDSA", "288", "yes" },
        { "Signature", "OID.1.2.840.10045.4.3.2", "SHA256withECDSA", "289", "yes" },
        { "Signature", "2.16.840.1.101.3.4.2.1with1.2.840.10045.2.1", "SHA256withECDSA", "290", "yes" },
        { "Signature", "SHA384/ECDSA", "SHA384withECDSA", "293", "yes" },
        { "Signature", "1.2.840.10045.4.3.3", "SHA384withECDSA", "295", "yes" },
        { "Signature", "OID.1.2.840.10045.4.3.3", "SHA384withECDSA", "296", "yes" },
        { "Signature", "2.16.840.1.101.3.4.2.2with1.2.840.10045.2.1", "SHA384withECDSA", "297", "yes" },
        { "Signature", "SHA512/ECDSA", "SHA512withECDSA", "300", "yes" },
        { "Signature", "1.2.840.10045.4.3.4", "SHA512withECDSA", "302", "yes" },
        { "Signature", "OID.1.2.840.10045.4.3.4", "SHA512withECDSA", "303", "yes" },
        { "Signature", "2.16.840.1.101.3.4.2.3with1.2.840.10045.2.1", "SHA512withECDSA", "304", "yes" },
        { "Signature", "SHA1withRSAandMGF1", "SHA1withRSA/PSS", "307", "no" },
        { "Signature", "SHA224withRSAandMGF1", "SHA224withRSA/PSS", "310", "no" },
        { "Signature", "SHA256withRSAandMGF1", "SHA256withRSA/PSS", "313", "no" },
        { "Signature", "SHA384withRSAandMGF1", "SHA384withRSA/PSS", "316", "no" },
        { "Signature", "SHA512withRSAandMGF1", "SHA512withRSA/PSS", "319", "no" },
        { "TrustManagerFactory", "X509", "PKIX", "90", "yes" },
    };

    /** service (case-folded) -> alias (case-folded) -> canonical name. */
    private static final Map<String, Map<String, String>> BY_SERVICE = index();

    private ConscryptAliasTable() {
    }

    private static Map<String, Map<String, String>> index() {
        Map<String, Map<String, String>> byService = new LinkedHashMap<>();
        for (String[] row : ROWS) {
            byService.computeIfAbsent(fold(row[0]), k -> new LinkedHashMap<>()).put(fold(row[1]), row[2]);
        }
        return byService;
    }

    private static String fold(String s) {
        return s == null ? "" : s.trim().toUpperCase(Locale.ROOT);
    }

    /**
     * The name {@code observed} denotes in {@code service}: the canonical name of
     * its alias row, or {@code observed} itself when no row explains it. Never
     * null unless {@code observed} is.
     */
    public static String canonical(String service, String observed) {
        if (observed == null) {
            return null;
        }
        Map<String, String> aliases = BY_SERVICE.get(fold(service));
        if (aliases == null) {
            return observed;
        }
        String target = aliases.get(fold(observed));
        return target == null ? observed : target;
    }

    /**
     * Whether {@code observed} is admitted by {@code allowList} for {@code service}
     * under the set's one normalisation rule: case-insensitive comparison, plus
     * this table. The allow-list stays exactly the api30 clause -- an alias never
     * enters the list it resolves against.
     */
    public static boolean matches(String service, String observed, List<String> allowList) {
        if (observed == null || allowList == null) {
            return false;
        }
        String direct = fold(observed);
        String resolved = fold(canonical(service, observed));
        for (String entry : allowList) {
            String candidate = fold(entry);
            if (candidate.equals(direct) || candidate.equals(resolved)) {
                return true;
            }
        }
        return false;
    }

    /**
     * The table as it is written, one {@code String[5]} per row in file order:
     * service, alias, canonical, {@code OpenSSLProvider.java} line,
     * {@code inApi30Allowlist}. Read by {@code ConscryptAliasTableTest} to compare
     * the class against {@code data/jca_android/alias_table.csv}.
     */
    public static List<String[]> rows() {
        List<String[]> copy = new ArrayList<>(ROWS.length);
        for (String[] row : ROWS) {
            copy.add(row.clone());
        }
        return copy;
    }
}
