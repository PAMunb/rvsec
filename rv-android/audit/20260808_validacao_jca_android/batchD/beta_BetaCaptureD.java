import javax.crypto.Mac;
import java.security.MessageDigest;
import java.security.KeyPairGenerator;
import java.security.SecureRandom;
import java.security.Signature;
import javax.crypto.KeyGenerator;
import java.security.Provider;
import java.security.Key;
import java.security.PrivateKey;
import java.security.PublicKey;
import java.security.cert.Certificate;
import java.security.spec.AlgorithmParameterSpec;
import java.nio.ByteBuffer;

/**
 * Agent Beta batch D - ajc capture matrix driver. One method per call site;
 * NEVER EXECUTED. Woven by ajc 1.9.25.1 (lib_tmp/aspectjtools.jar) with the
 * generated MultiSpec_1MonitorAspect.aj; capture facts are read from
 * -showWeaveInfo output. Sites are exactly the members the android-30 member
 * table publishes for the five owners (extracted class bytes, javap).
 */
public class BetaCaptureD {
    // --- MAC ---
    static void site_mac_gi1() throws Exception { Mac.getInstance("HmacSHA256"); }
    static void site_mac_gi2s() throws Exception { Mac.getInstance("HmacSHA256", "BC"); }
    static void site_mac_gi2p(Provider p) throws Exception { Mac.getInstance("HmacSHA256", p); }
    static void site_mac_init_k(Mac m, Key k) throws Exception { m.init(k); }
    static void site_mac_init_kaps(Mac m, Key k, AlgorithmParameterSpec s) throws Exception { m.init(k, s); }
    static void site_mac_up_b(Mac m) { m.update((byte) 1); }
    static void site_mac_up_arr(Mac m, byte[] b) { m.update(b); }
    static void site_mac_up_arr3(Mac m, byte[] b) { m.update(b, 0, 1); }
    static void site_mac_up_buf(Mac m, ByteBuffer bb) { m.update(bb); }
    static void site_mac_df0(Mac m) { m.doFinal(); }
    static void site_mac_df_arr(Mac m, byte[] b) { m.doFinal(b); }
    static void site_mac_df_out(Mac m, byte[] b) throws Exception { m.doFinal(b, 0); }
    static void site_n_mac_reset(Mac m) { m.reset(); }
    // --- MDG ---
    static void site_mdg_gi1() throws Exception { MessageDigest.getInstance("SHA-256"); }
    static void site_mdg_gi2s() throws Exception { MessageDigest.getInstance("SHA-256", "BC"); }
    static void site_mdg_gi2p(Provider p) throws Exception { MessageDigest.getInstance("SHA-256", p); }
    static void site_mdg_up_b(MessageDigest d) { d.update((byte) 1); }
    static void site_mdg_up_arr(MessageDigest d, byte[] b) { d.update(b); }
    static void site_mdg_up_arr3(MessageDigest d, byte[] b) { d.update(b, 0, 1); }
    static void site_mdg_up_buf(MessageDigest d, ByteBuffer bb) { d.update(bb); }
    static void site_mdg_d0(MessageDigest d) { d.digest(); }
    static void site_mdg_d_arr(MessageDigest d, byte[] b) { d.digest(b); }
    static void site_mdg_d3(MessageDigest d, byte[] b) throws Exception { d.digest(b, 0, 16); }
    static void site_n_mdg_reset(MessageDigest d) { d.reset(); }
    // --- KPG ---
    static void site_kpg_gi1() throws Exception { KeyPairGenerator.getInstance("RSA"); }
    static void site_kpg_gi2s() throws Exception { KeyPairGenerator.getInstance("RSA", "BC"); }
    static void site_kpg_gi2p(Provider p) throws Exception { KeyPairGenerator.getInstance("RSA", p); }
    static void site_kpg_init_i(KeyPairGenerator k) { k.initialize(2048); }
    static void site_kpg_init_isr(KeyPairGenerator k, SecureRandom sr) { k.initialize(2048, sr); }
    static void site_kpg_init_aps(KeyPairGenerator k, AlgorithmParameterSpec s) throws Exception { k.initialize(s); }
    static void site_kpg_init_apsr(KeyPairGenerator k, AlgorithmParameterSpec s, SecureRandom sr) throws Exception { k.initialize(s, sr); }
    static void site_kpg_gen(KeyPairGenerator k) { k.generateKeyPair(); }
    static void site_kpg_genkp(KeyPairGenerator k) { k.genKeyPair(); }
    static void site_n_kgn_gi1() throws Exception { KeyGenerator.getInstance("AES"); }
    // --- SRD ---
    static void site_srd_c0() { new SecureRandom(); }
    static void site_srd_cb(byte[] b) { new SecureRandom(b); }
    static void site_srd_gi1() throws Exception { SecureRandom.getInstance("SHA1PRNG"); }
    static void site_srd_gi2s() throws Exception { SecureRandom.getInstance("SHA1PRNG", "BC"); }
    static void site_srd_gi2p(Provider p) throws Exception { SecureRandom.getInstance("SHA1PRNG", p); }
    static void site_srd_gstrong() throws Exception { SecureRandom.getInstanceStrong(); }
    static void site_srd_setseed_l(SecureRandom sr) { sr.setSeed(123L); }
    static void site_srd_setseed_b(SecureRandom sr, byte[] b) { sr.setSeed(b); }
    static void site_srd_genseed(SecureRandom sr) { sr.generateSeed(16); }
    static void site_srd_nextint_b(SecureRandom sr) { sr.nextInt(100); }
    static void site_srd_nextint0(SecureRandom sr) { sr.nextInt(); }
    static void site_srd_nextbytes(SecureRandom sr, byte[] b) { sr.nextBytes(b); }
    static void site_srd_ints0(SecureRandom sr) { sr.ints(); }
    static void site_srd_ints_l(SecureRandom sr) { sr.ints(5L); }
    static void site_srd_ints_ii(SecureRandom sr) { sr.ints(1, 10); }
    static void site_srd_ints_lii(SecureRandom sr) { sr.ints(5L, 1, 10); }
    static void site_n_srd_nextlong(SecureRandom sr) { sr.nextLong(); }
    static void site_n_srd_nextdouble(SecureRandom sr) { sr.nextDouble(); }
    // --- SIG ---
    static void site_sig_gi1() throws Exception { Signature.getInstance("SHA256withRSA"); }
    static void site_sig_gi2s() throws Exception { Signature.getInstance("SHA256withRSA", "BC"); }
    static void site_sig_gi2p(Provider p) throws Exception { Signature.getInstance("SHA256withRSA", p); }
    static void site_sig_isign(Signature s, PrivateKey k) throws Exception { s.initSign(k); }
    static void site_sig_isign_sr(Signature s, PrivateKey k, SecureRandom sr) throws Exception { s.initSign(k, sr); }
    static void site_sig_iver_c(Signature s, Certificate c) throws Exception { s.initVerify(c); }
    static void site_sig_iver_p(Signature s, PublicKey k) throws Exception { s.initVerify(k); }
    static void site_sig_up_b(Signature s) throws Exception { s.update((byte) 1); }
    static void site_sig_up_arr(Signature s, byte[] b) throws Exception { s.update(b); }
    static void site_sig_up_arr3(Signature s, byte[] b) throws Exception { s.update(b, 0, 1); }
    static void site_sig_up_buf(Signature s, ByteBuffer bb) throws Exception { s.update(bb); }
    static void site_sig_sign0(Signature s) throws Exception { s.sign(); }
    static void site_sig_sign3(Signature s, byte[] b) throws Exception { s.sign(b, 0, 10); }
    static void site_sig_ver(Signature s, byte[] b) throws Exception { s.verify(b); }
    static void site_sig_ver3(Signature s, byte[] b) throws Exception { s.verify(b, 0, 10); }
}
