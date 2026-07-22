package br.unb.cic.cryptoapp.messagedigest;

import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;

import android.content.Context;
import android.content.DialogInterface;
import android.os.Bundle;
import android.util.Log;
import android.view.View;
import android.widget.EditText;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;

import br.unb.cic.cryptoapp.R;

public class MessageDigestActivity extends AppCompatActivity {

    private Spinner spinnerAlgorithm;
    private EditText editTextInput;
    private TextView textViewResult;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_message_digest);

        spinnerAlgorithm = (Spinner) findViewById(R.id.spinnerMessageDigest);
        editTextInput = (EditText) findViewById(R.id.editTextMessageDigest);
        textViewResult = (TextView) findViewById(R.id.textViewMessageDigestResult);
    }

    public void generateHash(View v) {
        String algorithm = spinnerAlgorithm.getSelectedItem().toString();
        String input = editTextInput.getText().toString();

        Log.i("CryptoApp", "algorithm=" + algorithm);
        Log.i("CryptoApp", "input=" + input);

        if (validateAlgorithm(algorithm) & validateInput(input)) {
            clearErrors();
            MessageDigestUtil util = new MessageDigestUtil();
            try {
                String result = util.hash(input, algorithm);
                Log.i("CryptoApp", "result=" + result);
                textViewResult.setText(result);
                Toast.makeText(this, getString(R.string.msgHashGenerated), Toast.LENGTH_SHORT);
            } catch (Exception e) {
                Log.w("CryptoApp", "Error: " + e.getMessage());
                showErrorDialog(e.getMessage());
            }
        } else {
            Log.w("CryptoApp", "Invalid inputs");
            textViewResult.setText("");
            Toast.makeText(this, getString(R.string.msgInvalidInput), Toast.LENGTH_LONG);
        }
    }

    private boolean validateAlgorithm(String algorithm) {
        boolean valid = true;
        if ("Select".equalsIgnoreCase(algorithm)) {
            ((TextView) spinnerAlgorithm.getSelectedView()).setError("Select an algorithm ...");
            valid = false;
        }
        return valid;
    }

    private boolean validateInput(String input) {
        boolean valid = true;
        if (input.isEmpty()) {
            editTextInput.setError("Please, insert a text");
            valid = false;
        }
        return valid;
    }

    private void clearErrors() {
        ((TextView) spinnerAlgorithm.getSelectedView()).setError(null);
        editTextInput.setError(null);
    }

    private void showErrorDialog(String text) {
        AlertDialog.Builder dialog = new AlertDialog.Builder(this);
        dialog.setTitle(getString(R.string.msgError))
                .setMessage(text)
                .setIcon(android.R.drawable.ic_dialog_alert)
                .setCancelable(true)
                .show();
    }

}