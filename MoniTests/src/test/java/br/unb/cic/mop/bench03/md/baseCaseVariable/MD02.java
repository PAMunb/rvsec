package br.unb.cic.mop.bench03.md.baseCaseVariable;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

public class MD02 {

    public static void main(String[] args) {
        MessageDigest digest;
        String algorithmName = "MD5";
        try {
            digest = MessageDigest.getInstance(algorithmName);
            byte[] out = digest.digest("password".getBytes());
        } catch (NoSuchAlgorithmException e) {
            // TODO Auto-generated catch block
            e.printStackTrace();
        }
    }
}
