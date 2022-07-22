package br.unb.cic.mop.bench02.brokencrypto;

import javax.crypto.*;
import java.io.UnsupportedEncodingException;
import java.security.InvalidKeyException;
import java.security.NoSuchAlgorithmException;

public class BrokenCryptoABSCase1 {

    /* Note: It must be a main method for running on our Bench02 driver.
      *  since this is a static method for now, we have to move the field instance
      *  crypto to a local variable.
      *  We also have to fix the string key algorithm and cipher transformation... since
      *  they must be compatible */
    public static void main(String args[]) throws NoSuchAlgorithmException, NoSuchPaddingException, IllegalBlockSizeException, BadPaddingException, InvalidKeyException, UnsupportedEncodingException {
        Crypto2 crypto = new Crypto2("AES/ECB/PKCS5Padding");
        crypto.encrypt("abc","");
    }
}

class Crypto2 {
    Cipher cipher;
    String defaultAlgo;
    public Crypto2(String defAlgo) throws NoSuchPaddingException, NoSuchAlgorithmException {
        defaultAlgo = defAlgo;
    }

    public byte[] encrypt(String txt, String passedAlgo) throws UnsupportedEncodingException, InvalidKeyException, BadPaddingException, IllegalBlockSizeException, NoSuchAlgorithmException, NoSuchPaddingException {
        if(passedAlgo.isEmpty()){
            passedAlgo = defaultAlgo;
        }

        KeyGenerator keyGen = KeyGenerator.getInstance("AES"); // it cannot be "AES/ECB/PKCS5Padding"
        SecretKey key = keyGen.generateKey();
        Cipher cipher = Cipher.getInstance(defaultAlgo);
        cipher.init(Cipher.ENCRYPT_MODE, key);

        byte [] txtBytes = txt.getBytes();
        return cipher.doFinal(txtBytes);
    }
}

