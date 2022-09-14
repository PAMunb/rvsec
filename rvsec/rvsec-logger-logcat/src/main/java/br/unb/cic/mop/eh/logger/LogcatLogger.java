package br.unb.cic.mop.eh.logger;

import android.util.Log;
import br.unb.cic.mop.eh.ErrorDescription;

public class LogcatLogger implements ILogger {

    @Override
    public void logError(ErrorDescription err) {
        Log.v("RVSEC", err.getErrorSummary() + "," + err.getExpecting().trim());
    }

}
