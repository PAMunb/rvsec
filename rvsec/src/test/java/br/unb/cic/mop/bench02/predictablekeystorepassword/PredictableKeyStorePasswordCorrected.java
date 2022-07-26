package br.unb.cic.mop.bench02.predictablekeystorepassword;

import java.io.File;
import java.io.IOException;
import java.net.URL;
import java.security.KeyStore;
import java.security.KeyStoreException;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.security.cert.CertificateException;

public class PredictableKeyStorePasswordCorrected {
    URL cacerts;
    public static void main(String args[]) throws KeyStoreException, IOException, CertificateException, NoSuchAlgorithmException {
        PredictableKeyStorePasswordCorrected pksp = new PredictableKeyStorePasswordCorrected();
        pksp.go();
    }

    public void go() throws KeyStoreException, IOException, CertificateException, NoSuchAlgorithmException {
        String type = "JKS";
        KeyStore ks = KeyStore.getInstance(type);
        cacerts = new File("./target/test-classes/testInput-ks").toURI().toURL();

        SecureRandom random = new SecureRandom();
        String password = String.valueOf(random.ints());

        ks.load(cacerts.openStream(), password.toCharArray());
    }
}
