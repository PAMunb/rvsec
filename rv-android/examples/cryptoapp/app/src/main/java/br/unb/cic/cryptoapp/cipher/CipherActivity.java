package br.unb.cic.cryptoapp.cipher;

import android.os.Bundle;
import android.util.Log;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;

import androidx.appcompat.app.AppCompatActivity;

import br.unb.cic.cryptoapp.R;

public class CipherActivity extends AppCompatActivity {

    private Button btnEncrypt;
    private EditText editTextEncrypt;
    private TextView textViewEncryptResult;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_cipher);

        editTextEncrypt = (EditText) findViewById(R.id.editTextCipherEncrypt);
        textViewEncryptResult = (TextView) findViewById(R.id.textViewCypherEncryptResult);
        btnEncrypt = (Button) findViewById(R.id.btn_cipher_encrypt);
        btnEncrypt.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                encrypt();
            }
        });
    }

    private void encrypt() {
        Log.i("CryptoApp", "Encrypting ...");
        CipherUtil util = new CipherUtil();
        String text = editTextEncrypt.getText().toString();
        try {
            String result = util.encrypt(text);
            textViewEncryptResult.setText(result);
        } catch (Exception e) {
            Log.e("CryptoApp", "Error: " + e.getMessage());
        }
    }
}