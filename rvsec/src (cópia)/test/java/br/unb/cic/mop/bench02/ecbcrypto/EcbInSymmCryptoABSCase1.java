package br.unb.cic.mop.bench02.ecbcrypto;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.NoSuchPaddingException;
import javax.crypto.SecretKey;
import java.security.InvalidKeyException;
import java.security.NoSuchAlgorithmException;

public class EcbInSymmCryptoABSCase1 {
    CryptoECB1 crypto;
    public static void main(String args[]) throws NoSuchPaddingException, NoSuchAlgorithmException, InvalidKeyException {
        String cryptoAlgo = "AES/ECB/PKCS5Padding";
        EcbInSymmCryptoABSCase1 p = new EcbInSymmCryptoABSCase1();
        p.crypto = new CryptoECB1(cryptoAlgo);
        p.crypto.method1("");
    }
}

class CryptoECB1 {
    String defAlgo;

    public CryptoECB1(String algo) {
        defAlgo = algo;
    }

    public void method1(String passedAlgo) throws NoSuchAlgorithmException, NoSuchPaddingException, InvalidKeyException {

        if(passedAlgo.isEmpty()){
            passedAlgo = defAlgo;
        }

        KeyGenerator keyGen = KeyGenerator.getInstance("AES");
        SecretKey key = keyGen.generateKey();
        Cipher cipher = Cipher.getInstance(passedAlgo);
        cipher.init(Cipher.ENCRYPT_MODE, key);

    }
}
