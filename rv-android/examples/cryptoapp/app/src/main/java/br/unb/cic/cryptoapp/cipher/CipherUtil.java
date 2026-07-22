package br.unb.cic.cryptoapp.cipher;

import static br.unb.cic.cryptoapp.util.Utils.bytesToHex;

import java.nio.charset.StandardCharsets;
import java.util.Random;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.SecretKeySpec;

public class CipherUtil {

    public String encrypt(String plainText) throws Exception {
        Random random = new Random();
        String alg = "";
        byte[] data = null;
        if (random.nextInt(10) > 6) {
            data = aes(plainText);
            alg = "AES: ";
        } else {
            data = des(plainText);
            alg = "DES: ";
        }
        return alg + bytesToHex(data);
    }

    public String unreachableEncrypt(String plainText) throws Exception {
        byte[] data = des(plainText);
        return bytesToHex(data);
    }

    private byte[] aes(String plainText) throws Exception {
        KeyGenerator keyGenerator = KeyGenerator.getInstance("AES");
        keyGenerator.init(128);

        SecretKey secretKey = keyGenerator.generateKey();
        byte[] byteKey = secretKey.getEncoded();
        SecretKeySpec secretKeySpec = new SecretKeySpec(byteKey, "AES");

        Cipher aesCipher = Cipher.getInstance("AES/GCM/NoPadding");
        aesCipher.init(Cipher.ENCRYPT_MODE, secretKeySpec);

        return aesCipher.doFinal(plainText.getBytes(StandardCharsets.UTF_8));
    }

    private byte[] des(String plainText) throws Exception {
        KeyGenerator keyGenerator = KeyGenerator.getInstance("DES");

        SecretKey secretKey = keyGenerator.generateKey();

        Cipher cipher = Cipher.getInstance("DES");
        cipher.init(Cipher.ENCRYPT_MODE, secretKey);

        return cipher.doFinal(plainText.getBytes(StandardCharsets.UTF_8));
    }

}
