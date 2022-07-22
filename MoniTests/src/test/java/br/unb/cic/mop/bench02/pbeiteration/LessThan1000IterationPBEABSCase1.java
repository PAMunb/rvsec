package br.unb.cic.mop.bench02.pbeiteration;

import javax.crypto.BadPaddingException;
import javax.crypto.IllegalBlockSizeException;
import javax.crypto.NoSuchPaddingException;
import javax.crypto.spec.PBEParameterSpec;
import java.io.UnsupportedEncodingException;
import java.security.InvalidKeyException;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;

public class LessThan1000IterationPBEABSCase1 {
    CryptoPBEIteration1 crypto;
    public static void main(String args[]) throws NoSuchAlgorithmException, NoSuchPaddingException, IllegalBlockSizeException, BadPaddingException, InvalidKeyException, UnsupportedEncodingException {
        LessThan1000IterationPBEABSCase1 m = new LessThan1000IterationPBEABSCase1();

        m.crypto = new CryptoPBEIteration1(20);
        m.crypto.method1(0);
    }
}

class CryptoPBEIteration1 {
    int defcount;

    public CryptoPBEIteration1(int count) throws NoSuchPaddingException, NoSuchAlgorithmException {
        defcount = count;
    }

    public void method1(int passedCount) throws UnsupportedEncodingException, InvalidKeyException, BadPaddingException, IllegalBlockSizeException, NoSuchAlgorithmException, NoSuchPaddingException {

        passedCount = defcount;

        SecureRandom random = new SecureRandom();
        PBEParameterSpec pbeParamSpec = null;
        byte[] salt = new byte[16];
        random.nextBytes(salt);

        pbeParamSpec = new PBEParameterSpec(salt,passedCount);
    }
}

