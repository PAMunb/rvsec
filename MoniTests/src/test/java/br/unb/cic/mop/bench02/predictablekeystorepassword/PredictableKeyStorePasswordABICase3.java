package br.unb.cic.mop.bench02.predictablekeystorepassword;

import java.io.File;
import java.io.IOException;
import java.net.URL;
import java.security.KeyStore;
import java.security.KeyStoreException;
import java.security.NoSuchAlgorithmException;
import java.security.cert.CertificateException;

public class PredictableKeyStorePasswordABICase3 {
    URL cacerts;
    public static void main(String args[]) throws KeyStoreException, IOException, CertificateException, NoSuchAlgorithmException {
        PredictableKeyStorePasswordABICase3 pkspac = new PredictableKeyStorePasswordABICase3();
        String key = "password";
        pkspac.method1(key);
    }

    public void method1(String k) throws KeyStoreException, IOException, CertificateException, NoSuchAlgorithmException {
        String key2 = k;
        method2(key2);
    }

    public void method2(String key) throws KeyStoreException, IOException, CertificateException, NoSuchAlgorithmException {
        String type = "JKS";
        KeyStore ks = KeyStore.getInstance(type);
        cacerts = new File("./target/test-classes/testInput-ks").toURI().toURL();
        ks.load(cacerts.openStream(), key.toCharArray());
    }
}
