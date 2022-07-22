package br.unb.cic.mop.bench03.cipher.aesGCMNoPaddingReplaceDES;
import java.security.Key;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;

public class CipherExample02 {
    public static void main(String[] args)  throws Exception {
        Cipher c = Cipher.getInstance("AES/GCM/NoPadding".replace("AES/GCM/NoPadding", "DES"));
        runCipher(c);
    }

    public static void runCipher(Cipher c) throws Exception {
        Key key = KeyGenerator.getInstance("DES").generateKey();
        c.init(Cipher.ENCRYPT_MODE, key);
        byte[] cipherText = c.doFinal("password".getBytes());
    }
}
