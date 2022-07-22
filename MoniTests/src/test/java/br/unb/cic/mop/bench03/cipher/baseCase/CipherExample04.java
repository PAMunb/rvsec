package br.unb.cic.mop.bench03.cipher.baseCase;
import java.security.Key;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;

public class CipherExample04 {
    public static void main(String[] args)  throws Exception {
        Cipher c = Cipher.getInstance("AES");
        runCipher(c);
    }

    public static void runCipher(Cipher c) throws Exception {
        Key key = KeyGenerator.getInstance("AES").generateKey();
        c.init(Cipher.ENCRYPT_MODE, key);
        byte[] cipherText = c.doFinal("password".getBytes());
    }

}
