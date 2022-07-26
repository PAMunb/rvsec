package br.unb.cic.mop.eh.logger;

import br.unb.cic.mop.eh.ErrorDescription;

@FunctionalInterface
public interface ILogger {

    void logError(ErrorDescription err);

}
