package me.guillaumin.android.osmtracker.monitors;

import java.io.*;
import java.util.concurrent.*;
import java.util.concurrent.locks.*;
import java.util.*;
import java.lang.ref.*;
import org.aspectj.lang.*;
import android.app.AlertDialog;
import android.app.Activity;
import android.content.DialogInterface;
import android.content.Context;
import android.util.Log;


#import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.fragment.app.Fragment;

import java.security.MessageDigest;


public aspect GetSystemServiceMonitorAspect {
    public GetSystemServiceMonitorAspect() {}

    before (Activity a): (execution(void Activity+.onCreate(..) ) && this(a)) {
      MultiSpec_1RuntimeMonitor.onCreateActivity(a);
    }

    Object around (String s): (call(Object getSystemService(String)) && args(s)) {
        if (s.equals(Context.LOCATION_SERVICE)) { MultiSpec_1RuntimeMonitor.getLocationServiceEvent(); }
        if (s.equals(Context.TEXT_SERVICES_MANAGER_SERVICE)) { MultiSpec_1RuntimeMonitor.getTextServiceEvent(); }
        if (s.equals(Context.TELEPHONY_SERVICE)) { MultiSpec_1RuntimeMonitor.getTelephonyServiceEvent(); }
        if (s.equals(Context.NOTIFICATION_SERVICE)) { MultiSpec_1RuntimeMonitor.getNotificationServiceEvent(); }
        if (s.equals(Context.STORAGE_SERVICE)) { MultiSpec_1RuntimeMonitor.getStorageServiceEvent(); }
        
        String text = "123";
        try {
            MessageDigest md = MessageDigest.getInstance("MD5");
            md.update(text.getBytes());
            byte[] digest = md.digest();
            StringBuffer sb = new StringBuffer();
            for (byte b : digest)
                sb.append(String.format("%02x", b & 0xff));
            text = sb.toString();
        }catch(Exception e){
            e.printStackTrace();
        }

        int duration = Toast.LENGTH_LONG;

        Toast toast = Toast.makeText(getActivity(), text, duration);
        toast.show();
        
        return proceed(s);
    }

}
