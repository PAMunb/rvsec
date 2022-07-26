package br.unb.cic.mop.bench02.predictableseeds;

public class PredictableSeedsABMCCase2 {
    public static void main (String [] args){
        PredictableSeedsABMC2 ps = new PredictableSeedsABMC2();
        byte seed = 100;
        ps.go(seed);
    }
}
