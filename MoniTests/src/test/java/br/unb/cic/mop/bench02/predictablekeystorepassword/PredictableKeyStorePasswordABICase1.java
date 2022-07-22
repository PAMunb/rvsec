package br.unb.cic.mop.bench02.predictablekeystorepassword;

import java.io.File;
import java.io.IOException;
import java.net.URL;
import java.security.KeyStore;
import java.security.KeyStoreException;
import java.security.NoSuchAlgorithmException;
import java.security.cert.CertificateException;

public class PredictableKeyStorePasswordABICase1 {
    URL cacerts;
    public static void main(String args[]) throws KeyStoreException, IOException, CertificateException, NoSuchAlgorithmException {
        PredictableKeyStorePasswordABICase1 pksp = new PredictableKeyStorePasswordABICase1();
        String key = "password";
        pksp.go(key);
    }

    public void go(String key) throws KeyStoreException, IOException, CertificateException, NoSuchAlgorithmException {
        String type = "JKS";
        KeyStore ks = KeyStore.getInstance(type);
        cacerts = new File("./target/test-classes/testInput-ks").toURI().toURL();
        ks.load(cacerts.openStream(), key.toCharArray());
    }
}
