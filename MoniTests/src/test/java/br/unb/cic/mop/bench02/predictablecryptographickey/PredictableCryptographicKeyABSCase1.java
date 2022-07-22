package br.unb.cic.mop.bench02.predictablecryptographickey;

import javax.crypto.BadPaddingException;
import javax.crypto.Cipher;
import javax.crypto.IllegalBlockSizeException;
import javax.crypto.NoSuchPaddingException;
import javax.crypto.spec.SecretKeySpec;
import java.io.UnsupportedEncodingException;
import java.security.InvalidKeyException;
import java.security.NoSuchAlgorithmException;
import java.util.Arrays;

public class PredictableCryptographicKeyABSCase1 {
    PredictableCryptographicKeyABSCase1Internal crypto;
    public static void main(String args[]) throws NoSuchAlgorithmException, NoSuchPaddingException, UnsupportedEncodingException {
        PredictableCryptographicKeyABSCase1 m = new PredictableCryptographicKeyABSCase1();
        String passKey = PredictableCryptographicKeyABSCase1.getKey("pass.key");

        if(passKey == null) {
            byte defaultKey[] = {20,10,30,5,5,6,8,7};
            m.crypto = new PredictableCryptographicKeyABSCase1Internal(defaultKey);
        }
        else {
            m.crypto = new PredictableCryptographicKeyABSCase1Internal(passKey.getBytes("UTF-8"));
        }
    }

    byte[] encryptPass(String pass, String src) throws IllegalBlockSizeException, BadPaddingException, InvalidKeyException, UnsupportedEncodingException {
        String keyStr = PredictableCryptographicKeyABSCase1.getKey(src);
        return crypto.method1(pass, keyStr.getBytes("UTF-8"));
    }

    public static String getKey(String s) {
        return System.getProperty(s);
    }
}

class PredictableCryptographicKeyABSCase1Internal {
    Cipher cipher;
    String algoSpec = "AES/CBC/PKCS5Padding";
    String algo = "AES";
    byte [] defaultKey;
    public PredictableCryptographicKeyABSCase1Internal(byte [] defkey) throws NoSuchPaddingException, NoSuchAlgorithmException {
        cipher = Cipher.getInstance(algoSpec);
        defaultKey = defkey;
    }

    public byte[] method1(String txt, byte [] key) throws UnsupportedEncodingException, InvalidKeyException, BadPaddingException, IllegalBlockSizeException {
        if(key == null){
            key = defaultKey;
        }
        byte[] keyBytes = key;
        byte [] txtBytes = txt.getBytes();
        keyBytes = Arrays.copyOf(keyBytes,16);

        SecretKeySpec keySpec = new SecretKeySpec(keyBytes,algo);
        cipher.init(Cipher.ENCRYPT_MODE,keySpec);
        return cipher.doFinal(txtBytes);
    }
}
