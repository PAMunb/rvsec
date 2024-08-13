package br.unb.cic.cryptoapp;

import android.content.Intent;
import android.os.Bundle;
import android.view.Menu;
import android.view.MenuInflater;
import android.view.MenuItem;
import android.view.View;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;

import br.unb.cic.cryptoapp.cipher.CipherActivity;
import br.unb.cic.cryptoapp.messagedigest.MessageDigestActivity;

public class MainActivity extends AppCompatActivity {
    private MenuItem menuItemMessageDigest;
    private MenuItem menuItemMessageCipher;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

//        menuItemMessageDigest = (MenuItem) findViewById(R.id.menu_item_message_digest);
//        menuItemMessageCipher = (MenuItem) findViewById(R.id.menu_item_cipher);
//
//        menuItemMessageDigest.setIntent(new Intent(this, MessageDigestActivity.class));
//        menuItemMessageDigest.setIntent(new Intent(this, CipherActivity.class));
    }

    public void showScreenMessageDigest(View view) {
        showScreen(MessageDigestActivity.class);
    }

    public void showScreenCipher(View view) {
        showScreen(CipherActivity.class);
    }

    @Override
    public boolean onCreateOptionsMenu(Menu menu) {
        MenuInflater inflater = getMenuInflater();
        inflater.inflate(R.menu.cryptoapp_menu, menu);
        menuItemMessageDigest = menu.findItem(R.id.menu_item_message_digest);
        menuItemMessageDigest.setOnMenuItemClickListener(new MenuItem.OnMenuItemClickListener() {
            @Override
            public boolean onMenuItemClick(@NonNull MenuItem menuItem) {
                Intent intent = new Intent(null, MessageDigestActivity.class);
                startActivity(intent);
                return true;
            }
        });
        return super.onCreateOptionsMenu(menu);
    }

    @Override
    public boolean onOptionsItemSelected(MenuItem item) {
//        if (item.getItemId() == R.id.menu_item_message_digest) {
//            Intent intent = new Intent(this, MessageDigestActivity.class);
//            startActivity(intent);
//        }
        if (item.getItemId() == R.id.menu_item_cipher) {
            Intent intent = new Intent(this, CipherActivity.class);
            startActivity(intent);
        }
        return super.onOptionsItemSelected(item);
    }

    private void showScreen(Class clazz) {
        Intent intent = new Intent(this, clazz);
        startActivity(intent);
    }

}