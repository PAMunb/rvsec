# G-PARAM fixtures

The collapse this gate exists to catch has never happened in the tree, because no
specification of any set declares a primitive-array parameter yet — the first one
lands with the junction specifications of task 5.1. Waiting for it would mean
writing the gate against the first real generation, which is exactly the run where
a wrong gate is most expensive.

So the pairs live here: one `.mop` under `specs/` and the `.rvm` a generator
would write for it under `monitors/`, transcribed from the measured behaviour —
the parameter is gone from the header, everything else is intact, and the
generator returned 0.

| Pair | What it shows |
|---|---|
| `ByteArrayJunction` | `byte[] iv` deleted from the generated header |
| `IntArrayJunction` | `int[] sizes` deleted — the collapse is about the array, not the element type |
| `CharArrayJunction` | `char[] password` deleted, the PBE-chain shape |
| `ObjectIdiomJunction` | `Object iv` survives: the idiom that bypasses the grammar branch |
