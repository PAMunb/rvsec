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
import mop.*;

public aspect GetSystemServiceMonitorAspect {
    public GetSystemServiceMonitorAspect() {}

    before (Activity a): (execution(void Activity+.onCreate(..) ) && this(a)) {
      MultiSpec_1RuntimeMonitor.onCreateActivity(a);
    }

    Object around (String s): (call(Object getSystemService(String)) && args(s)) {
        if (s.equals(Context.LOCATION_SERVICE)) { MultiSpec_1RuntimeMonitor.GetSystemService_getLocationServiceEvent(); }
        if (s.equals(Context.TEXT_SERVICES_MANAGER_SERVICE)) { MultiSpec_1RuntimeMonitor.GetSystemService_getTextServiceEvent(); }
        if (s.equals(Context.TELEPHONY_SERVICE)) { MultiSpec_1RuntimeMonitor.GetSystemService_getTelephonyServiceEvent(); }
        if (s.equals(Context.NOTIFICATION_SERVICE)) { MultiSpec_1RuntimeMonitor.GetSystemService_getNotificationServiceEvent(); }
        if (s.equals(Context.STORAGE_SERVICE)) { MultiSpec_1RuntimeMonitor.GetSystemService_getStorageServiceEvent(); }
        return proceed(s);
    }

}
