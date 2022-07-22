package br.unb.cic.mop.eh.report;

import java.util.Set;

import br.unb.cic.mop.eh.ErrorDescription;

@Deprecated
public class STDOutputReport implements IErrorReport {
    @Override
    public void exportErrors(Set<ErrorDescription> errors) throws Exception {
        errors.stream().forEach(System.out::println);
    }
}
