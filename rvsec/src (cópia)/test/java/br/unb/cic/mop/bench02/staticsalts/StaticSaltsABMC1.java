package br.unb.cic.mop.bench02.staticsalts;

import javax.crypto.spec.PBEParameterSpec;

public class StaticSaltsABMC1 {
    public void key2(byte[] salt, int count) {
        PBEParameterSpec pbeParamSpec = null;
        pbeParamSpec = new PBEParameterSpec(salt, count);
    }
}
