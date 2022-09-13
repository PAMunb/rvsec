package br.unb.cic.mop.bench02.predictableseeds;

import javax.crypto.BadPaddingException;
import javax.crypto.IllegalBlockSizeException;
import javax.crypto.NoSuchPaddingException;
import java.io.UnsupportedEncodingException;
import java.security.InvalidKeyException;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;

public class PredictableSeedsABSCase2 {
    CryptoPredictableSeed2 crypto;
    public static void main(String args[]) throws NoSuchAlgorithmException, NoSuchPaddingException, IllegalBlockSizeException, BadPaddingException, InvalidKeyException, UnsupportedEncodingException {
        PredictableSeedsABSCase2 m = new PredictableSeedsABSCase2();
        byte seed = 100;
        m.crypto = new CryptoPredictableSeed2(seed);
        m.crypto.method1((byte) 20);
    }
}

class CryptoPredictableSeed2 {
    byte defSeed;

    public CryptoPredictableSeed2(byte seed) throws NoSuchPaddingException, NoSuchAlgorithmException {
        defSeed = seed;
    }

    public void method1(byte passedSeed) throws UnsupportedEncodingException, InvalidKeyException, BadPaddingException, IllegalBlockSizeException, NoSuchAlgorithmException, NoSuchPaddingException {

        passedSeed = defSeed;
        SecureRandom sr = new SecureRandom(new byte[]{passedSeed});
        int v = sr.nextInt();
        System.out.println(v);
    }
}
