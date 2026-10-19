package com.example.app;

import android.app.Activity;
import androidx.core.view.MenuHostHelper;

/** Declares onOptionsItemSelected(int), which is not the platform's callback. */
public class IntMenuActivity extends Activity {
    private MenuHostHelper menuHostHelper;

    public boolean onOptionsItemSelected(int id) {
        return false;
    }
}
