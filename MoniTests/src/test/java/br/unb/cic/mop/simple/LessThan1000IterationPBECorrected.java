package br.unb.cic.mop.simple;

import org.junit.Test;

import br.unb.cic.misc.Assertions;

import javax.crypto.spec.PBEParameterSpec;
import java.security.SecureRandom;

public class LessThan1000IterationPBECorrected {
    @Test
    public void test(){
        br.unb.cic.mop.bench02.pbeiteration.LessThan1000IterationPBECorrected lt = new br.unb.cic.mop.bench02.pbeiteration.LessThan1000IterationPBECorrected();
        lt.key2();
        Assertions.expectingEmptySetOfErrors();
    }
    public void key2(){
        SecureRandom random = new SecureRandom();
        PBEParameterSpec pbeParamSpec = null;
        byte[] salt = new byte[32];
        random.nextBytes(salt);
        int count = 1020;
        pbeParamSpec = new PBEParameterSpec(salt, count);
    }
}