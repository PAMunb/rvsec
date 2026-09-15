package br.unb.cic.mop.eh;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.security.cert.X509Certificate;

import javax.net.ssl.TrustManager;
import javax.net.ssl.TrustManagerFactory;
import javax.net.ssl.X509TrustManager;

import org.junit.Test;

public class EvidenceTest {

    /** A trust manager whose class the test's class loader defines, as an application's would be. */
    static final class TrustAll implements X509TrustManager {
        @Override
        public void checkClientTrusted(X509Certificate[] chain, String authType) {
        }

        @Override
        public void checkServerTrusted(X509Certificate[] chain, String authType) {
        }

        @Override
        public X509Certificate[] getAcceptedIssuers() {
            return new X509Certificate[0];
        }
    }

    @Test
    public void nullAndOtherObjectsCarryNoEvidence() {
        assertEquals("", Evidence.keysFor(null));
        assertEquals("", Evidence.keysFor("AES"));
        assertEquals("", Evidence.keysFor(new char[] {'a'}));
    }

    @Test
    public void byteArrayCarriesATruncatedSha256() {
        byte[] key = new byte[16];
        for (int i = 0; i < key.length; i++) {
            key[i] = (byte) (i + 1);
        }
        // sha256 of the bytes 0x01..0x10 begins 5dfbabeedf318bf3
        assertEquals("sha256:5dfbabeedf318bf3", Evidence.fingerprint(key));
        assertEquals(" vfp='sha256:5dfbabeedf318bf3'", Evidence.keysFor(key));
        assertEquals(Evidence.keysFor(key), Evidence.keysFor(key.clone()));
    }

    @Test
    public void trustManagerArrayCarriesElementClassesInOrder() throws Exception {
        TrustManagerFactory factory = TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm());
        factory.init((java.security.KeyStore) null);
        TrustManager platform = factory.getTrustManagers()[0];
        TrustManager[] mixed = {platform, new TrustAll(), null};

        assertEquals(" vcls='" + platform.getClass().getName() + ","
                + TrustAll.class.getName() + ",null'", Evidence.keysFor(mixed));
    }

    @Test
    public void applicationDefinedIsDecidedByTheClassLoader() throws Exception {
        TrustManagerFactory factory = TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm());
        factory.init((java.security.KeyStore) null);
        TrustManager platform = factory.getTrustManagers()[0];

        assertTrue(Evidence.isApplicationDefined(new TrustAll(), TrustManager.class));
        assertFalse(Evidence.isApplicationDefined(platform, TrustManager.class));
        assertFalse(Evidence.isApplicationDefined(null, TrustManager.class));
    }

    @Test
    public void quotesAreEscapedAndValuesBounded() {
        TrustManager[] many = new TrustManager[200];
        for (int i = 0; i < many.length; i++) {
            many[i] = new TrustAll();
        }
        String suffix = Evidence.keysFor(many);
        String value = suffix.substring(" vcls='".length(), suffix.length() - 1);
        assertEquals(512, value.length());
        assertFalse(value.contains("'"));
        assertEquals("a\\'b", Evidence.quote("a'b"));
    }
}
