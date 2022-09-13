package br.unb.cic.mop.bench03.cipher.baseCaseInterProc;
import java.security.Key;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;

public class CipherExample05 {
    private String cipherName = "AES/GCM/NoPadding";

    public CipherExample05 methodA() {
        cipherName = "AES/GCM/NoPadding";
        return this;
    }

    public CipherExample05 methodB() {
        cipherName = "DES";
        return this;
    }

    public String getCipherName(){
        return cipherName;
    }

    public static void main(String[] args) throws Exception {
        Cipher c = Cipher.getInstance(new CipherExample05().methodA().methodB().getCipherName());
        runCipher(c);
    }

    public static void runCipher(Cipher c) throws Exception {
        Key key = KeyGenerator.getInstance("DES").generateKey();
        c.init(Cipher.ENCRYPT_MODE, key);
        byte[] cipherText = c.doFinal("password".getBytes());
    }
}
