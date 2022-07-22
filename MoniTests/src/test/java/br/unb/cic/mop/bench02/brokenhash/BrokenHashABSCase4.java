package br.unb.cic.mop.bench02.brokenhash;

import javax.crypto.BadPaddingException;
import javax.crypto.IllegalBlockSizeException;
import javax.crypto.NoSuchPaddingException;
import java.io.UnsupportedEncodingException;
import java.security.InvalidKeyException;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

public class BrokenHashABSCase4 {
    public static void main(String args[]) throws NoSuchAlgorithmException, NoSuchPaddingException, IllegalBlockSizeException, BadPaddingException, InvalidKeyException, UnsupportedEncodingException {
        CryptoHash4 crypto = new CryptoHash4("MD2");
        crypto.encrypt("abc","");
    }
}

class CryptoHash4 {
    String crypto;

    public CryptoHash4(String defCrypto) throws NoSuchPaddingException, NoSuchAlgorithmException {
        crypto = defCrypto;
    }

    public void encrypt(String str, String passedAlgo) throws UnsupportedEncodingException, InvalidKeyException, BadPaddingException, IllegalBlockSizeException, NoSuchAlgorithmException, NoSuchPaddingException {
        if(passedAlgo.isEmpty()){
            passedAlgo = crypto;
        }

        MessageDigest md = MessageDigest.getInstance(crypto);
        md.update(str.getBytes());
        System.out.println(md.digest());

    }
}
