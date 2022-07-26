package br.unb.cic.mop.bench02.predictablekeystorepassword;

import java.io.File;
import java.io.IOException;
import java.net.MalformedURLException;
import java.net.URL;
import java.security.KeyStore;
import java.security.KeyStoreException;
import java.security.NoSuchAlgorithmException;
import java.security.cert.CertificateException;

public class PredictableKeyStorePasswordABMC1 {
    URL cacerts;
    public void go(String key) throws KeyStoreException, IOException, CertificateException, NoSuchAlgorithmException {
        String type = "JKS";
        KeyStore ks = KeyStore.getInstance(type);
        cacerts = new File("./target/test-classes/testInput-Ks").toURI().toURL();
        ks.load(cacerts.openStream(), key.toCharArray());
    }
}
