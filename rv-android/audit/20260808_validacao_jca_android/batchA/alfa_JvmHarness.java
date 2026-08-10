// ALFA batch A -- JVM harness (D-piloto-2 style; no emulator, no weaving).
// Purpose (per test, mapped to claims in alfa_claims.csv / alfa_report.md):
//  T1 IvParameterSpec(byte[],int,int) throwing envelope: proves the extra conjuncts
//     of IVP c2 (offset>=0 && len>=0 && iv.length>=offset+len) are vacuously true at
//     the after-returning join point (ALFA-IVP-02).
//  T2 SecretKeySpec(byte[],int,int,String) throwing envelope: proves SKS c4's
//     length disjunct is unreachable at after-returning and c2/c4 partition reduces
//     to the whitelist test (ALFA-SKS-07).
//  T3 PBEParameterSpec(salt, 100) and (salt, 100, ivSpec) both return normally:
//     the 3-arg misuse (iterationCount < 10000) is realizable and, having no
//     violating carrier, is silently suppressed by the spec (ALFA-PBE-03).
//  T4 DHGenParameterSpec(1024,1024) and (512,1024) return normally: the traces that
//     the api30 oracle accepts and the MOP condition suppresses are realizable
//     (ALFA-DHG-02/03).
//  T5 folding x JCA (D-piloto-2 test (a), adapted: these specs have no getInstance
//     event; the only algorithm-string constraint is SKS's whitelist): JCA treats
//     the SecretKeySpec algorithm case-insensitively downstream (Mac.init/Cipher.init
//     accept a lower-case name), so toUpperCase folding in SKS c1 is
//     behavior-consistent with the platform. Does not change ALFA-SKS-02's verdict
//     (the whitelist itself is extra-oracle).
// Threat recorded: this runs on the host JDK (Temurin 25). android.jar API 30 is a
// stub jar; the ART/libcore implementation is separate code with the same documented
// contract. The throwing envelopes used here are the documented API contract of the
// two constructors.
import javax.crypto.spec.*;
import javax.crypto.*;

public class alfa_JvmHarness {
    static int pass = 0, fail = 0;
    static void check(String id, boolean cond, String note) {
        System.out.printf("  %-6s %-4s %s%n", id, cond ? "PASS" : "FAIL", note);
        if (cond) pass++; else fail++;
    }
    interface Thrower { void run() throws Exception; }
    static Throwable thrown(Thrower t) {
        try { t.run(); return null; } catch (Throwable e) { return e; }
    }

    public static void main(String[] args) throws Exception {
        byte[] b16 = new byte[16];

        System.out.println("T1 IvParameterSpec(byte[],int,int) envelope:");
        check("T1a", thrown(() -> new IvParameterSpec(b16, -1, 4)) != null,
              "offset=-1 throws: " + cls(thrown(() -> new IvParameterSpec(b16, -1, 4))));
        check("T1b", thrown(() -> new IvParameterSpec(b16, 0, -1)) != null,
              "len=-1 throws: " + cls(thrown(() -> new IvParameterSpec(b16, 0, -1))));
        check("T1c", thrown(() -> new IvParameterSpec(b16, 14, 4)) != null,
              "iv.length<offset+len throws: " + cls(thrown(() -> new IvParameterSpec(b16, 14, 4))));
        check("T1d", thrown(() -> new IvParameterSpec(b16, 12, 4)) == null,
              "valid (12,4) returns normally");

        System.out.println("T2 SecretKeySpec(byte[],int,int,String) envelope:");
        check("T2a", thrown(() -> new SecretKeySpec(b16, 0, 17, "AES")) != null,
              "key.length<offset+len throws: " + cls(thrown(() -> new SecretKeySpec(b16, 0, 17, "AES"))));
        check("T2b", thrown(() -> new SecretKeySpec(b16, -1, 8, "AES")) != null,
              "offset=-1 throws: " + cls(thrown(() -> new SecretKeySpec(b16, -1, 8, "AES"))));
        check("T2c", thrown(() -> new SecretKeySpec(b16, 0, -1, "AES")) != null,
              "len=-1 throws: " + cls(thrown(() -> new SecretKeySpec(b16, 0, -1, "AES"))));
        check("T2d", thrown(() -> new SecretKeySpec(b16, 0, 16, "AES")) == null,
              "valid (0,16) returns normally");

        System.out.println("T3 PBEParameterSpec with iterationCount=100 (misuse under the oracle):");
        check("T3a", thrown(() -> new PBEParameterSpec(b16, 100)) == null,
              "2-arg returns normally (2-arg misuse HAS a carrier: c3 reports)");
        check("T3b", thrown(() -> new PBEParameterSpec(b16, 100, new IvParameterSpec(b16))) == null,
              "3-arg returns normally => realizable misuse with NO carrier: silent");

        System.out.println("T4 DHGenParameterSpec values valid under the api30 oracle, suppressed by the MOP condition:");
        check("T4a", thrown(() -> new DHGenParameterSpec(1024, 1024)) == null,
              "(1024,1024) returns normally; MOP condition exponentSize<primeSize false => c1 suppressed");
        check("T4b", thrown(() -> new DHGenParameterSpec(512, 1024)) == null,
              "(512,1024) returns normally; also suppressed (exponent>prime)");

        System.out.println("T5 folding x JCA (adapted test (a)): lower-case key algorithm accepted downstream:");
        SecretKeySpec skLower = new SecretKeySpec(b16, "aes");
        Throwable tMac = thrown(() -> { Mac m = Mac.getInstance("HmacSHA256");
                                        m.init(new SecretKeySpec(b16, "hmacsha256")); });
        check("T5a", tMac == null, "Mac(HmacSHA256).init(key alg 'hmacsha256'): " +
              (tMac == null ? "accepted" : cls(tMac)));
        Throwable tCip = thrown(() -> { Cipher c = Cipher.getInstance("AES/CBC/PKCS5Padding");
                                        c.init(Cipher.ENCRYPT_MODE, skLower,
                                               new IvParameterSpec(b16)); });
        check("T5b", tCip == null, "Cipher(AES).init(key alg 'aes'): " +
              (tCip == null ? "accepted" : cls(tCip)));
        Throwable tGet = thrown(() -> Cipher.getInstance("aes/cbc/pkcs5padding"));
        System.out.printf("  T5c   INFO getInstance(\"aes/cbc/pkcs5padding\"): %s%n",
              tGet == null ? "resolved (case-insensitive)" : cls(tGet));

        System.out.printf("%nsummary: %d PASS, %d FAIL%n", pass, fail);
        System.out.println("java.version=" + System.getProperty("java.version"));
        if (fail > 0) System.exit(1);
    }
    static String cls(Throwable t) { return t == null ? "no exception" : t.getClass().getSimpleName() + ": " + t.getMessage(); }
}
