package br.unb.cic.mop.eh.report;

import java.util.Set;

import br.unb.cic.mop.eh.ErrorDescription;

/**
 * An interface for exporting errors in different formats.
 */
@Deprecated
public interface IErrorReport {

    void exportErrors(Set<ErrorDescription> errors) throws Exception;

}
