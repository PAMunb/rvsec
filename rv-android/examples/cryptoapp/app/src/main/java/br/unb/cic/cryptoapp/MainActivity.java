package br.unb.cic.cryptoapp;

import android.content.Intent;
import android.os.Bundle;
import android.view.View;

import androidx.appcompat.app.AppCompatActivity;

import br.unb.cic.cryptoapp.cipher.CipherActivity;
import br.unb.cic.cryptoapp.messagedigest.MessageDigestActivity;

public class MainActivity extends AppCompatActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
    }

    public void showScreenMessageDigest(View view) {
        showScreen(MessageDigestActivity.class);
    }

    public void showScreenCipher(View view) {
        showScreen(CipherActivity.class);
    }

    private void showScreen(Class clazz) {
        Intent intent = new Intent(this, clazz);
        startActivity(intent);
    }

}