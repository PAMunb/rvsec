# Piloto da cadeia do IV — decisor do D4 (mecanismo A vs B)

**Agente I, segunda passada de auditoria — 2026-08-20.**
Executado inteiramente em scratchpad; nenhum arquivo do repositório foi tocado.
Ferramentas: javamop e rv-monitor de `target/release` (as mesmas do pipeline), eventos
injetados pelos despachantes estáticos do monitor gerado — o contrato do `TraceRunner`
da gh104 (`MultiSpec_1RuntimeMonitor.<Spec>_<event>Event(...)`), sem tecelagem AspectJ.

## O que o mecanismo B realmente é

O plano (§7.4) define B como **specs de junção multiparamétricas**: a cadeia inteira numa
única spec, com os elos de predicado virando elos de parâmetro. O piloto confirmou que essa
é a única forma possível de B: duas specs separadas compartilhando o `byte[]` **não têm
canal algum** — no `MultiSpec_1RuntimeMonitor.java` gerado para o par
`IvGenSpec(Object iv)` + `IvWrapUseSpec(IvParameterSpec spec, Cipher c)`, cada spec tem
seus próprios mapas (`IvGenSpec_iv_Map`, `IvWrapUseSpec_spec_c_Map`), monitores e sets,
com zero referências cruzadas; a spec consumidora sequer consegue *nomear* o `iv`.
"Specs separadas se comunicando" = estado Java externo compartilhado = `ExecutionContext`
= mecanismo A. Não há terceira via.

## Experimentos e resultados

Cadeia: `SecureRandom.nextBytes(iv)` → `new IvParameterSpec(iv)` → `Cipher.init(_,_,spec)`.
Driver com três cenários: (1) BOM — iv randomizado, cadeia completa; (2) RUIM — iv estático
(zeros), wrap + init; (3) RUIM — só o consumidor observado (spec de origem invisível).
Dois `byte[]` distintos vivos no mesmo processo — o teste de distinção de instâncias.

### E1 — `IvChainSpec` (ere `gen mk use`, os TRÊS eventos como creation)
- G-PARAM sobrevive: `.rvm` = `IvChainSpec(Object iv, IvParameterSpec spec, Cipher c)`.
- Monitor com fatiamento real: 21 `CachedWeakReference`, árvores (iv,spec,c), (spec,c),
  (spec)→(iv,spec), ()→(iv).
- Distingue as instâncias: cenário 1 dá MATCH com os identityHashCode certos; cenário 2 dá
  FAIL no iv não randomizado. **Mas**: o cenário BOM também produz
  `FAIL ev=use iv=- spec=... c=...` — a instância parcial θ=(spec1,c1), criada porque `use`
  é creation, não enxerga `gen`/`mk` (os bindings deles não são sub-instâncias dela) e falha.
  E o cenário 2 ganha dois FAILs extras de produto-cruzado ((iv1,spec2,c2) com o iv da
  cadeia boa). **B ingênuo acusa no caso correto.**

### E2 — `IvChainFsmSpec` (fsm; `use` NÃO-creation; laço benigno `got_gen[use]`) — o design que decide
```
start [ gen -> got_gen ]
got_gen [ gen -> got_gen ; use -> got_gen ; mk -> got_mk ]
got_mk [ use -> ok ]
ok [ use -> ok ]        alias match = ok
```
Saída, na íntegra:
```
cenario 1: MATCH iv=<iv1> spec=<spec1> c=<c1>            (1 match, ZERO fail)
cenario 2: FAIL ev=mk  iv=<iv2> spec=<spec2> c=-         (IvParameterSpec REQUIRES randomized)
           FAIL ev=use iv=<iv2> spec=<spec2> c=<c2>      (Cipher REQUIRES preparedIV)
cenario 3: (silêncio)                                     (= "não observado")
```
- O bom não acusa; o ruim acusa **duas vezes, nos dois REQUIRES da cadeia, na instância
  certa, com os bindings certos** (`__EVENTNAME` permite um código por evento).
- O cenário 3 silencioso é exatamente a lógica de três valores da §5 do plano
  ("REQUIRES só acusa com evidência de que teria visto o ENSURES") — **B a implementa
  estruturalmente**, sem mudança de tipo de retorno em lugar nenhum.

### E3 — diagnóstico sem o laço benigno (`IvChainFsmNoLoopSpec`)
Os joins produto-cruzado acontecem **mesmo com `use` não-creation**: sem `use -> got_gen`,
o cenário 2 ganha `FAIL ev=use iv=<iv1> spec=<spec2>` (o iv randomizado de OUTRA cadeia)
e o cenário 3 acusa com evidência alheia. **O laço benigno para instâncias desconexas é
obrigatório, não estilo.**

### E4 — controle §7.5 na cadeia real (`IvChainByteSpec`, `byte[] iv` declarado)
Reproduzido no próprio piloto: `.rvm` sai `IvChainByteSpec()` — a lista **inteira** apagada,
`rc=0`, mensagem de sucesso, monitor global com **zero** `CachedWeakReference`. O achado da
auditoria vale literalmente para a cadeia do IV; sem G-PARAM, a versão quebrada é
indistinguível da sã por código de saída.

### E5 — o que o runtime dá de graça no B
`WeakReference` nos três parâmetros + `TerminatedMonitorCleaner` (sem vazamento) e
`AbstractSynchronizedMonitor` (thread-safe) — os três defeitos do §4.3 do plano
(referências fortes, sem expurgo, sem sincronização) não existem no caminho B.

## Custos e atritos registrados

1. **Parâmetros da spec não são visíveis em `@match`/`@fail`** — erro de compilação só na
   compilação do monitor (javamop e rv-monitor passam). O idioma das specs reais (copiar
   para campos do monitor no corpo do evento) é obrigatório, e a falha é tardia.
2. **Idioma `Object` obrigatório** para o elo `byte[]` (E4) + gate G-PARAM.
3. **Disciplina de creation**: produtor/elo intermediário creation; consumidor **nunca**
   (senão FP no caso bom, E1). Isso contradiz a intuição do §7.4 ("acusar a ausência exige
   que o consumidor também seja criador") — a resposta certa é o silêncio de três valores.
4. **Laços benignos para joins desconexos** em todo estado alcançável por instâncias
   parciais (E3). Regra de construção do autômato, não opção.
5. Custo do gerador: trivial — 3 eventos, k=3, fsm de 4 estados, geração sub-segundo;
   coenable com `@fail` = 3·(2³−1) = 21 entradas (contra 2.228.207 do CipherSpec n=17).
   O k=4 do esboço do plano é desnecessário: `SecureRandom r` pode ser parâmetro só do
   evento — k=3 basta.
6. Joins desconexos criam monitores reais (custo de memória O(#gen × #use) no pior caso);
   o laço os mantém calados, não os elimina. Não medido em escala.
7. Atritos conhecidos confirmados: javamop deixa o `.rvm` no diretório da `.mop`;
   `@fail` absorvente re-acusa a cada evento seguinte (aqui desejável: um código por
   REQUIRES via `__EVENTNAME`, que funcionou no javamop patched).

## O que NÃO foi testado (limitações honestas)

- **Sem tecelagem**: eventos injetados nos despachantes estáticos. O `.aj` gerado preserva
  `args(iv)` com `Object iv` contra `nextBytes(byte[])` e `IvParameterSpec.new(byte[])`
  (mesmo caso TObj validado na auditoria), mas ajc/dexlib2 de ponta a ponta não rodou aqui.
- **Coexistência com `CipherSpec`** (dois monitores no mesmo joinpoint, dedup de relato) —
  dificuldade 2 do §7.4, não exercitada.
- **Memória em escala** (muitos ivs × muitos inits) — só o raciocínio do item 6.
- Sobrecargas restantes (`IvParameterSpec(byte[],int,int)`, `Cipher.init` com outras
  assinaturas) e o re-embrulho por getter (§4.2, limitação idêntica em A e B).
- Integração com `ErrorCollector`/envelope gh104 — o piloto usou `System.out`.

## Recomendação sobre o D4

**Híbrido, como o §7.6 revisto — agora decidido de fato, não no papel.** B aprovado para a
cadeia do IV (o caso difícil): o fatiamento por identidade do próprio JavaMOP atravessa o
elo `byte[]` via idioma `Object`, distingue os dois arrays no mesmo processo, acusa os dois
REQUIRES na instância certa e cala no caso bom e no não-observado. Com quatro regras de
design que o piloto descobriu e que precisam entrar no design e nos gates:
(a) consumidor nunca é creation; (b) laço benigno para toda instância desconexa alcançável;
(c) idioma de campos para handlers; (d) G-PARAM obrigatório (E4 mostra a falha silenciosa).

A fica com: posições de valor (`alg`, comparadas no corpo — como o oráculo), arestas sem
cadeia de eventos co-observável numa única spec, e o conjunto `jca` congelado (intocado).
O argumento novo a favor de B que o plano ainda não tem: **B implementa a lógica de três
valores estruturalmente** — silêncio = não observado — enquanto A precisa mudar o tipo de
retorno de `validate()` e tocar 27 sítios para obter o mesmo.

## Artefatos

- `specs_b/IvChainSpec.mop` (+ `out_b/`, E1) — ere, tudo creation
- `specs_b2/IvChainFsmSpec.mop` (+ `out_b2/`, E2) — o design recomendado
- `specs_b3/IvChainFsmNoLoopSpec.mop` (+ `out_b3/`, E3) — diagnóstico
- `specs_byte/IvChainByteSpec.mop` (+ `out_byte/`, E4) — controle §7.5
- `specs_split/IvGenSpec.mop`, `IvWrapUseSpec.mop` (+ `out_split/`, E5/canal)
- `driver/DriverB*.java`, `classes_b*/` — drivers e classes compiladas
