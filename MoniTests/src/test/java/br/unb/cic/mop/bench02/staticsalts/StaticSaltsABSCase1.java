package br.unb.cic.mop.bench02.staticsalts;

import javax.crypto.spec.PBEParameterSpec;

public class StaticSaltsABSCase1 {
    CryptoStaticSalt1 crypto;
    public static void main(String args[]) {
        StaticSaltsABSCase1 m = new StaticSaltsABSCase1();
        byte[] salt = {(byte) 0xa2};
        m.crypto = new CryptoStaticSalt1(salt);
        m.crypto.method1(null);
    }
}


class CryptoStaticSalt1 {
    byte[] defSalt;

    public CryptoStaticSalt1(byte [] salt) {
        defSalt = salt;
    }

    public void method1(byte[] passedSalt)  {

        passedSalt = defSalt;
        int count = 1020;
        PBEParameterSpec pbeParamSpec = null;
        pbeParamSpec = new PBEParameterSpec(passedSalt, count);

    }
}
