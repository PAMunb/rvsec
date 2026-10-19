package com.example.app;

import androidx.preference.Preference;

/** Its field type's class file is deleted after compilation, so reading its fields fails. */
public class UnreadablePreference extends Preference {
    AbsentAtRunTime absent;
}
