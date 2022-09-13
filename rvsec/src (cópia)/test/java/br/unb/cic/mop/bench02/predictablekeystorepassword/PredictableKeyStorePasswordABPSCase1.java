package br.unb.cic.mop.bench02.predictablekeystorepassword;

import java.io.File;
import java.io.IOException;
import java.net.URL;
import java.security.KeyStore;
import java.security.KeyStoreException;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.security.cert.CertificateException;

public class PredictableKeyStorePasswordABPSCase1 {
    URL cacerts;
    public static void main(String args[]) throws KeyStoreException, IOException, CertificateException, NoSuchAlgorithmException {
        PredictableKeyStorePasswordABPSCase1 pksp = new PredictableKeyStorePasswordABPSCase1();
        int choice=2;
        pksp.go(choice);
    }

    public void go(int choice) throws KeyStoreException, IOException, CertificateException, NoSuchAlgorithmException {
        String type = "JKS";
        KeyStore ks = KeyStore.getInstance(type);
        cacerts = new File("./target/test-classes/testInput-ks").toURI().toURL();
        String defaultKey = "password";
        if(choice>1){
            SecureRandom random = new SecureRandom();
            defaultKey = String.valueOf(random.ints());
        }
        ks.load(cacerts.openStream(), defaultKey.toCharArray());
    }
}
