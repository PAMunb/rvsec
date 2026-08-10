import javax.crypto.KeyGenerator;
import javax.crypto.SecretKeyFactory;
import javax.net.ssl.KeyManagerFactory;
import javax.net.ssl.TrustManagerFactory;
import javax.net.ssl.SSLContext;
import javax.net.ssl.ManagerFactoryParameters;
import javax.net.ssl.KeyManager;
import javax.net.ssl.TrustManager;
import java.security.KeyPairGenerator;
import java.security.KeyStore;
import java.security.Provider;
import java.security.SecureRandom;
import java.security.Key;
import java.security.cert.Certificate;
import java.security.spec.AlgorithmParameterSpec;
import java.io.InputStream;
import java.io.OutputStream;

/**
 * Agent Beta batch C - ajc capture matrix driver. One method per call site;
 * NEVER EXECUTED. Woven by ajc 1.9.25.1 (lib_tmp/aspectjtools.jar) with the
 * generated MultiSpec_1MonitorAspect.aj; capture facts are read from
 * -showWeaveInfo output and javap -c of the woven class.
 */
public class BetaCaptureC {
    // --- KGN (Esperado: g1|g3 on gi1; g2 on gi2s/gi2p; i1..i5; gk1) ---
    static void site_kgn_gi1() throws Exception { KeyGenerator.getInstance("AES"); }
    static void site_kgn_gi2s() throws Exception { KeyGenerator.getInstance("AES", "SunJCE"); }
    static void site_kgn_gi2p(Provider p) throws Exception { KeyGenerator.getInstance("AES", p); }
    static void site_kgn_init_i(KeyGenerator k) { k.init(128); }
    static void site_kgn_init_isr(KeyGenerator k, SecureRandom sr) { k.init(128, sr); }
    static void site_kgn_init_aps(KeyGenerator k, AlgorithmParameterSpec s) throws Exception { k.init(s); }
    static void site_kgn_init_apsr(KeyGenerator k, AlgorithmParameterSpec s, SecureRandom sr) throws Exception { k.init(s, sr); }
    static void site_kgn_init_sr(KeyGenerator k, SecureRandom sr) { k.init(sr); }
    static void site_kgn_genkey(KeyGenerator k) { k.generateKey(); }
    static void site_n_kpg_gi1() throws Exception { KeyPairGenerator.getInstance("EC"); }
    static void site_n_skf_gi1() throws Exception { SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256"); }
    static void site_n_kgn_getalg(KeyGenerator k) { k.getAlgorithm(); }
    // --- KMF ---
    static void site_kmf_gi1() throws Exception { KeyManagerFactory.getInstance("PKIX"); }
    static void site_kmf_gi2s() throws Exception { KeyManagerFactory.getInstance("PKIX", "SunJSSE"); }
    static void site_kmf_gi2p(Provider p) throws Exception { KeyManagerFactory.getInstance("PKIX", p); }
    static void site_kmf_init_ks(KeyManagerFactory f, KeyStore ks, char[] pw) throws Exception { f.init(ks, pw); }
    static void site_kmf_init_mfp(KeyManagerFactory f, ManagerFactoryParameters p) throws Exception { f.init(p); }
    static void site_kmf_getkm(KeyManagerFactory f) { f.getKeyManagers(); }
    static void site_n_kmf_defalg() { KeyManagerFactory.getDefaultAlgorithm(); }
    // --- TMF ---
    static void site_tmf_gi1() throws Exception { TrustManagerFactory.getInstance("PKIX"); }
    static void site_tmf_gi2s() throws Exception { TrustManagerFactory.getInstance("PKIX", "SunJSSE"); }
    static void site_tmf_gi2p(Provider p) throws Exception { TrustManagerFactory.getInstance("PKIX", p); }
    static void site_tmf_init_ks(TrustManagerFactory f, KeyStore ks) throws Exception { f.init(ks); }
    static void site_tmf_init_mfp(TrustManagerFactory f, ManagerFactoryParameters p) throws Exception { f.init(p); }
    static void site_tmf_gettm(TrustManagerFactory f) { f.getTrustManagers(); }
    static void site_n_tmf_defalg() { TrustManagerFactory.getDefaultAlgorithm(); }
    // --- SSL ---
    static void site_ssl_gi1() throws Exception { SSLContext.getInstance("TLS"); }
    static void site_ssl_gi2s() throws Exception { SSLContext.getInstance("TLS", "SunJSSE"); }
    static void site_ssl_gi2p(Provider p) throws Exception { SSLContext.getInstance("TLS", p); }
    static void site_ssl_init(SSLContext c, KeyManager[] km, TrustManager[] tm, SecureRandom sr) throws Exception { c.init(km, tm, sr); }
    static void site_ssl_cse0(SSLContext c) { c.createSSLEngine(); }
    static void site_ssl_cse2(SSLContext c) { c.createSSLEngine("h", 443); }
    static void site_n_ssl_getdef() throws Exception { SSLContext.getDefault(); }
    static void site_n_ssl_sockf(SSLContext c) { c.getSocketFactory(); }
    // --- KST ---
    static void site_kst_gi1() throws Exception { KeyStore.getInstance("PKCS12"); }
    static void site_kst_gi2s() throws Exception { KeyStore.getInstance("PKCS12", "SunJSSE"); }
    static void site_kst_gi2p(Provider p) throws Exception { KeyStore.getInstance("PKCS12", p); }
    static void site_kst_load_is(KeyStore ks, InputStream in, char[] pw) throws Exception { ks.load(in, pw); }
    static void site_kst_load_p(KeyStore ks, KeyStore.LoadStoreParameter p) throws Exception { ks.load(p); }
    static void site_kst_store_os(KeyStore ks, OutputStream os, char[] pw) throws Exception { ks.store(os, pw); }
    static void site_kst_store_p(KeyStore ks, KeyStore.LoadStoreParameter p) throws Exception { ks.store(p); }
    static void site_kst_getentry(KeyStore ks, KeyStore.ProtectionParameter p) throws Exception { ks.getEntry("a", p); }
    static void site_kst_setentry(KeyStore ks, KeyStore.Entry e, KeyStore.ProtectionParameter p) throws Exception { ks.setEntry("a", e, p); }
    static void site_kst_getkey(KeyStore ks, char[] pw) throws Exception { ks.getKey("a", pw); }
    static void site_n_kst_setcert(KeyStore ks, Certificate c) throws Exception { ks.setCertificateEntry("a", c); }
    static void site_n_kst_setkeyE(KeyStore ks, Key k, char[] pw, Certificate[] ch) throws Exception { ks.setKeyEntry("a", k, pw, ch); }
    static void site_n_kst_aliases(KeyStore ks) throws Exception { ks.aliases(); }
}
