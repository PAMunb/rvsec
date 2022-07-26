package br.unb.cic.mop.bench03.md.interprocedureCase;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

public class MD05 {
    private String digestName = "SHA-256";
    public MD05 A(){
        digestName = "SHA-256";
        return this;
    }
    public MD05 B(){
        digestName = "MD5";
        return this;
    }
    public String getName(){
        return digestName;
    }
    public static void main(String[] args) {
        MessageDigest cryptoDigest;
        try {
            cryptoDigest = MessageDigest.getInstance(new MD05().A().B().getName());
            byte[] out = cryptoDigest.digest("password".getBytes());
        } catch (NoSuchAlgorithmException e) {
            System.out.println("Error");
        }
    }
}
