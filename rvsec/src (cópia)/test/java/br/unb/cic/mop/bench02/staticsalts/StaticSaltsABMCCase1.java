package br.unb.cic.mop.bench02.staticsalts;

public class StaticSaltsABMCCase1 {
    public static void main(String [] args){
        StaticSaltsABMC1 cs = new StaticSaltsABMC1();
        byte[] salt = {(byte) 0xa2};
        int count = 1020;
        cs.key2(salt,count);

    }
}
