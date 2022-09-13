package br.unb.cic.mop.bench02.predictablekeystorepassword;

import java.io.File;
import java.io.IOException;
import java.net.URL;
import java.security.KeyStore;
import java.security.KeyStoreException;
import java.security.NoSuchAlgorithmException;
import java.security.cert.CertificateException;

public class PredictableKeyStorePasswordABSCase1 {
    CryptoPredictableKeyStorePassword1 crypto;
    public static void main(String args[]) throws CertificateException, NoSuchAlgorithmException, KeyStoreException, IOException {
        PredictableKeyStorePasswordABSCase1 m = new PredictableKeyStorePasswordABSCase1();
        String key = "password";
        m.crypto = new CryptoPredictableKeyStorePassword1(key);
        m.crypto.method1("");
    }
}

class CryptoPredictableKeyStorePassword1 {
    String defKey;
    URL cacerts;

    public CryptoPredictableKeyStorePassword1(String key){
        defKey = key;
    }

    public void method1(String passedKey) throws KeyStoreException, IOException, CertificateException, NoSuchAlgorithmException {

        passedKey = defKey;

        String type = "JKS";
        KeyStore ks = KeyStore.getInstance(type);
        cacerts = new File("./target/test-classes/testInput-ks").toURI().toURL();
        ks.load(cacerts.openStream(), passedKey.toCharArray());
    }
}
