package br.unb.cic.mop.bench01;

import org.junit.Before;
import org.junit.Ignore;
import org.junit.Test;

import br.unb.cic.misc.Assertions;

import javax.crypto.Cipher;
import javax.crypto.IllegalBlockSizeException;
import javax.crypto.NoSuchPaddingException;
import javax.net.ssl.*;
import java.io.File;
import java.io.FileInputStream;
import java.io.InputStream;
import java.security.*;
import java.security.cert.Certificate;

public class SSLContextTest {

    public static final String JKS = "JKS";
    public static final String PASSWORD = "password";

    private TrustManager[] tms;
    private KeyManager[] kms;

    @Before
    public void setUp() throws Exception {
        tms = loadTrustManagers();
        kms = loadKeyManagers();
    }

    private KeyStore loadKeyStore() throws Exception {
        String keyStoreAlgorithm = JKS;
        char[] passwordIn = PASSWORD.toCharArray();

        File ksInputFile = new File(getClass().getClassLoader().getResource("testInput-ks").getFile());
        FileInputStream fileIn = new FileInputStream(ksInputFile);

        KeyStore keyStore0 = KeyStore.getInstance(keyStoreAlgorithm);
        keyStore0.load(fileIn, passwordIn);
        return keyStore0;
    }

    private TrustManager[] loadTrustManagers() throws Exception {
        TrustManagerFactory trustManagerFactory0 = TrustManagerFactory.getInstance("PKIX");
        trustManagerFactory0.init(loadKeyStore());

        return trustManagerFactory0.getTrustManagers();
    }

    private KeyManager[] loadKeyManagers() throws Exception {
        KeyManagerFactory keyManagerFactory =
                KeyManagerFactory.getInstance(KeyManagerFactory.getDefaultAlgorithm());
        keyManagerFactory.init(loadKeyStore(), PASSWORD.toCharArray());

        return keyManagerFactory.getKeyManagers();
    }

    @Test
    public void sSLContextValidTest1() throws Exception {
        SSLContext sSLContext0 = SSLContext.getInstance("TLSv1.2");
        sSLContext0.init(kms, tms, new SecureRandom());
        Assertions.hasEnsuredPredicate(sSLContext0);
        Assertions.mustBeInAcceptingState(sSLContext0);
    }


    @Test
    public void sSLContextValidTest2()
            throws NoSuchAlgorithmException, KeyManagementException, NoSuchProviderException {

        SSLContext sSLContext0 = SSLContext.getInstance("TLSv1.2", "SunJSSE");
        sSLContext0.init(kms, tms, new SecureRandom());
        Assertions.hasEnsuredPredicate(sSLContext0);
        Assertions.mustBeInAcceptingState(sSLContext0);

    }

    @Test
    public void sSLContextValidTest3() throws NoSuchAlgorithmException, KeyManagementException {

        SSLContext sSLContext0 = SSLContext.getInstance("TLSv1.2");
        sSLContext0.init(kms, tms, new SecureRandom());
        SSLEngine sSLEngine = sSLContext0.createSSLEngine();
        Assertions.hasEnsuredPredicate(sSLContext0);
        Assertions.mustBeInAcceptingState(sSLContext0);

    }

    @Test
    public void sSLContextValidTest4()
            throws NoSuchAlgorithmException, KeyManagementException, NoSuchProviderException {

        SSLContext sSLContext0 = SSLContext.getInstance("TLSv1.2", "SunJSSE");
        sSLContext0.init(kms, tms, new SecureRandom());
        SSLEngine sSLEngine = sSLContext0.createSSLEngine();
        Assertions.hasEnsuredPredicate(sSLContext0);
        Assertions.mustBeInAcceptingState(sSLContext0);

    }

    @Test
    public void sSLContextValidTest5() throws NoSuchAlgorithmException, KeyManagementException {

        SSLContext sSLContext0 = SSLContext.getInstance("TLSv1.2");
        sSLContext0.init(kms, tms, (SecureRandom) null);
        SSLEngine sSLEngine = sSLContext0.createSSLEngine("127.0.0.1", 0);
        Assertions.hasEnsuredPredicate(sSLContext0);
        Assertions.mustBeInAcceptingState(sSLContext0);

    }

    @Test
    public void sSLContextInvalidTest1() throws NoSuchAlgorithmException {

        SSLContext sSLContext0 = SSLContext.getInstance("TLSv1.2");
        Assertions.notHasEnsuredPredicate(sSLContext0);
        Assertions.mustNotBeInAcceptingState(sSLContext0);

    }

    @Test
    public void sSLContextInvalidTest2() throws NoSuchAlgorithmException, NoSuchProviderException {

        SSLContext sSLContext0 = SSLContext.getInstance("TLSv1.2", "SunJSSE");
        Assertions.notHasEnsuredPredicate(sSLContext0);
        Assertions.mustNotBeInAcceptingState(sSLContext0);

    }

    @Test(expected = java.lang.IllegalStateException.class)
    public void sSLContextInvalidTest3() throws NoSuchAlgorithmException {

        SSLContext sSLContext0 = SSLContext.getInstance("TLSv1.2");
        SSLEngine sSLEngine = sSLContext0.createSSLEngine();
        Assertions.notHasEnsuredPredicate(sSLEngine);
        Assertions.mustNotBeInAcceptingState(sSLContext0);

    }

    @Test(expected = java.lang.IllegalStateException.class)
    public void sSLContextInvalidTest4() throws NoSuchAlgorithmException, NoSuchProviderException {

        SSLContext sSLContext0 = SSLContext.getInstance("TLSv1.2", "SunJSSE");
        SSLEngine sSLEngine = sSLContext0.createSSLEngine();
        Assertions.notHasEnsuredPredicate(sSLEngine);
        Assertions.mustNotBeInAcceptingState(sSLContext0);

    }

    @Test(expected = java.lang.IllegalStateException.class)
    public void sSLContextInvalidTest5() throws NoSuchAlgorithmException {

        SSLContext sSLContext0 = SSLContext.getInstance("TLSv1.2");
        SSLEngine sSLEngine = sSLContext0.createSSLEngine("127.0.0.1", 0);
        Assertions.notHasEnsuredPredicate(sSLEngine);
        Assertions.mustNotBeInAcceptingState(sSLContext0);

    }

}
