package br.unb.cic.mop.bench02.predictablepbepassword;

import javax.crypto.spec.PBEKeySpec;
import javax.crypto.spec.PBEParameterSpec;
import java.security.SecureRandom;

public class PredictablePBEPasswordABSCase1 {
    CryptoPredictablePBE crypto;
    public static void main(String args[]){
        PredictablePBEPasswordABSCase1 m = new PredictablePBEPasswordABSCase1();
        String password = "sagar";
        m.crypto = new CryptoPredictablePBE(password);
        m.crypto.method1("");
    }
}


class CryptoPredictablePBE {
    String defPassword;
    private PBEKeySpec pbeKeySpec = null;
    private PBEParameterSpec pbeParamSpec = null;

    public CryptoPredictablePBE(String password){

        defPassword = password;
    }

    public void method1(String passedPassword) {

        if(passedPassword.isEmpty()){
            passedPassword = defPassword;
        }
        byte [] salt = new byte[16];
        SecureRandom sr = new SecureRandom();
        sr.nextBytes(salt);
        int iterationCount = 11010;
        int keyLength = 16;
        pbeKeySpec = new PBEKeySpec(passedPassword.toCharArray(),salt,iterationCount,keyLength);
    }
}