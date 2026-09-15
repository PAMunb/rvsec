# Artifact updates owed to /opsx:update (collected during apply)

1. `Evidence.suffix(Object)` renamed to `Evidence.keysFor(Object)`: `suffix` is a reserved token of
   the JavaMOP grammar (`javamop.jj`, `<SUFFIX: "suffix">`, a specification modifier), so a `.mop`
   calling `Evidence.suffix(` does not parse. Update design D10, API Design (`br.unb.cic.mop.eh.Evidence`),
   the Key Components table and the instrumentation delta spec wherever the helper is named.
