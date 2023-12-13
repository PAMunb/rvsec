package br.unb.cic.cryptoapp.cipher;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.SecretKeySpec;

public class CipherUtil {

    public void encrypt(String plainText){

    }

    private byte[] aes(String plainText) throws Exception {
        KeyGenerator keyGenerator = KeyGenerator.getInstance("AES");
        keyGenerator.init(128);

        SecretKey secretKey = keyGenerator.generateKey();
        byte[] byteKey = secretKey.getEncoded();
        SecretKeySpec secretKeySpec = new SecretKeySpec(byteKey, "AES");

        Cipher aesCipher = Cipher.getInstance("AES/GCM/NoPadding");
        aesCipher.init(Cipher.ENCRYPT_MODE, secretKeySpec);

        return aesCipher.doFinal(plainText.getBytes("UTF-8"));
    }

}
