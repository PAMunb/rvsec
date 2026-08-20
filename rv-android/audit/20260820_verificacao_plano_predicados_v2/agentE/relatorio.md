# Agente E — 2a passada de auditoria da alegação D1 (venn RV×CC)

Data: 2026-08-20. Scripts: `venn_d1.py`, `task4.py` (neste diretório). Executados com o
Python do venv do rv-android (`uv run python`, pandas 3.0.0).

Fontes usadas (nenhuma aproximação — lógica traduzida linha a linha e citada nos scripts):
- `ase-journal/dataset/{cc.csv,cc_rv_mapping.csv,cc_summary.csv,results/errors.csv}`
- `ase-journal/data-analysis/rvsec/rq1_rv_cc.py:45-143` (política do merge)
- `rvsec/rvsec-core/.../jca/util/{CipherTransformationUtil,Api30CipherTransformationUtil,ConscryptAliasTable}.java`
- `rv-android/data/jca_android/alias_table.csv` (158 linhas; a fonte das linhas do ConscryptAliasTable)
- `rvsec/rvsec-mop/src/main/resources/jca_android/*.mop` (allow-lists api30)
- `rvsec/rvsec-mop/src/main/resources/jca/*.mop` (specs congeladas que produziram o dataset)

## TAREFA 1 — linha-base: SUSTENTADO

Reproduzida dígito a dígito em pandas puro, seguindo `rq1_rv_cc.py` (keep_default_na=False,
merge interno com o mapping, descarte pós-merge das regras None-mapeadas, regex fixada de
method_name, dedup por (apk, class, method, spec)):

**RV=454, CC=423, both=112, só-RV=342, só-CC=311.** Assert passa.

## TAREFA 2 — allow-lists sozinhas: SUSTENTADO

Inventário completo dos 15.444 eventos `UnsafeAlgorithm` (spec × valor observado, extraído de
`message` "but found X."):

| spec | valor | n | literal (fold) | + alias |
|---|---|---:|---|---|
| CipherSpec | RSA/ECB/OAEPWithSHA1AndMGF1Padding | 109 | rejeita | rejeita |
| MessageDigestSpec | (vazio) | 156 | rejeita | rejeita |
| MessageDigestSpec | MD5 | 3.552 | admite | admite |
| MessageDigestSpec | SHA-1 | 1.915 | admite | admite |
| MessageDigestSpec | SHA | 1 | rejeita | admite |
| MessageDigestSpec | SHA1 | 424 | rejeita | admite |
| MacSpec | (vazio) | 31 | rejeita | rejeita |
| SignatureSpec | (vazio) | 234 | rejeita | rejeita |
| SignatureSpec | NONEWITHRSA | 4 | admite* | admite |
| SignatureSpec | SHA256WITHRSA | 4 | admite* | admite |
| TrustManagerFactorySpec | (vazio) | 8.371 | rejeita | rejeita |
| TrustManagerFactorySpec | X509 | 643 | rejeita | admite |

*A auditoria disse que esses dois "só casam sob alias" — na verdade casam por **fold de case
direto** no `matches()`; o passo "literal" da auditoria foi case-sensitive (é assim que os
5.467 dela se reproduzem: MD5+SHA-1 = 3.552+1.915 = 5.467 exatos; sob o fold real do
`matches()` o literal silencia 5.475; com alias, 6.543). Divergência de modelagem interna,
sem efeito no resultado.

Removendo **só** os eventos silenciados (chave sobrevive se restar 1 evento):
- literal: **342/311** (venn inalterado) ✓
- com alias: **342/311** (venn inalterado) ✓

Zero células movidas, como a auditoria alegou. `CipherSpec` de fato não contribui: as duas
classes Java rejeitam o único valor observado (confirmado com `CipherTransformationUtil.isValid`
e `Api30CipherTransformationUtil.isValid` traduzidos fielmente — o hífen não é dobrado no api30
e a forma sem hífen não está na lista).

## TAREFA 3 — leitura mais agressiva: REFINADO (300, não 299; e 299 NÃO é o teto)

**(a)** Alias + "a chave cai se QUALQUER evento UnsafeAlgorithm seu foi silenciado":
**só-RV=300 / só-CC=322** (RV=401, both=101; 53 chaves caem, 11 delas em both).
A auditoria publicou 299/322 — **off-by-one diagnosticado**: 299 sai exatamente se a única
chave do MacSpec (31 eventos UA com valor observado **vazio**, only-RV) também cair. Valor
vazio não é admitido por `matches("Mac","",lista)`; sob a modelagem declarada pela própria
auditoria essa chave sobrevive. O número correto da leitura da auditoria é **300/322**
(−42/+11, margem 22 — não muda nenhuma conclusão qualitativa).

**(b)** Mapeamento spec→serviço reconstruído dos `.mop` de `jca_android` (não à mão):
MessageDigestSpec→`MessageDigest` (lista MessageDigestSpec.mop:28), SignatureSpec→`Signature`
(:35-39, 24 entradas), MacSpec→`Mac` (:24-26, 12), TrustManagerFactorySpec→`TrustManagerFactory`
(["PKIX"], :35), SSLContextSpec→`SSLContext` (:35-36, 7), KeyStoreSpec→`KeyStore` (:35, 5),
CipherSpec→`Api30CipherTransformationUtil.isValid` (sem alias — confirmado no import estático
CipherSpec.mop:15). A auditoria **não lista** o seu mapeamento no documento; o meu é derivado
dos fontes e produz os números acima. Nenhuma divergência detectável além do MacSpec-vazio.

**(c) Existe leitura defensável mais agressiva que chega a ~255 — a alegação "não há folga
além de 299" é REVERTIDA.** A auditoria restringiu o silenciamento à categoria
`UnsafeAlgorithm`. Mas o conjunto `jca_android` re-transcreve as MESMAS allow-lists também em
`SSLContextSpec` (admite `TLS`, `SSL`, `Default`, ... — categoria `UnsafeProtocol`, 8.751 de
8.802 eventos silenciados) e `KeyStoreSpec` (admite `AndroidKeyStore` — categoria
`InvalidKeyStoreType`, todos os 2.005 eventos silenciados). São exatamente os dois casos
ilustrativos do apêndice do artigo (OkHttp `TLS`/`X509`; `MasterKeys`/`AndroidKeyStore`) que o
próprio plano diz que "deixam de ser violações". Estendendo a mesma leitura (alias + descarte
da chave inteira) às três categorias:

| cenário | RV | both | só-RV | só-CC |
|---|---:|---:|---:|---:|
| publicado | 454 | 112 | 342 | 311 |
| UA, chave inteira (auditoria, corrigido) | 401 | 101 | **300** | **322** |
| UA+UP+IKST, chave inteira | 323 | 68 | **255** | **355** |
| UA, por (apk,spec) | 393 | 100 | 293 | 323 |
| UA+UP+IKST, por (apk,spec) | 232 | 38 | 194 | 385 |
| UA+UP+IKST + vazio silencia, chave inteira | 252 | 39 | 213 | 384 |

**O ~255/~354 do plano é recuperado quase exatamente (255/355) pela extensão às categorias
UnsafeProtocol e InvalidKeyStoreType** — que é uma leitura tão "de reparo de allow-list"
quanto a da auditoria, e mais fiel ao conjunto `jca_android` como ele está escrito. O plano
provavelmente calculou isso; a auditoria estreitou a categoria sem declarar.

## TAREFA 4 — atribuição do risco: REFINADO (a atribuição está parcialmente invertida)

Órfãos do `jca` congelado, recomputados dos `.mop` (batem com o plano: **18 em 10 specs**):
IvParameterSpec{c3,c4}, KeyPairGeneratorSpec{initError}, MessageDigestSpec{reset},
PBEKeySpecSpec{err1,err2,err3,f1,f2}, PBEParameterSpecSpec{c3}, SSLContextSpec{unsafe_protocol},
SecretKeySpecSpec{c3,c4}, SecureRandomSpec{c3,g4,setSeed3}, SignatureSpec{g3},
TrustManagerFactorySpec{g3}.

Números de sustentação:
- Linhas de `errors.csv` em specs portadoras de órfãos: **73.930 (76,2% de 97.018)**.
- `InvalidSequenceOfMethodCalls` nessas specs: **49.817 = 70,4% da categoria** — reproduz o
  número da gh101 citado pelo plano, dígito a dígito.
- Chaves do venn nessas specs: **314 de 454** (214 only-RV, 100 both).
- "E5 máximo" (todo ISoMC das 10 specs removido, reports mantidos — limite superior do reparo
  de órfãos, pois inclui ISoMC não-órfão como os 12.400 do `next2` do SecureRandom):
  venn = **247/339**. Combinado com allow-list UA+UP+IKST chave-inteira: **160/383**.

**Onde a auditoria acerta**: o canal que move o venn é de fato o ISoMC acoplado — remover só
os reports (Tarefa 2) move zero; e o reparo estrutural (E5 e afins) tem alcance potencial
maior que as allow-lists (até −95 chaves only-RV no limite superior, contra −42).

**Onde a auditoria erra**: a frase "o risco não vem das allow-lists, vem do reparo E5" atribui
as 53 chaves do cenário máximo ao reparo dos órfãos. A leitura dos fontes congelados mostra o
contrário para essas chaves: o ISoMC delas é **gerado pelo mesmo valor que a allow-list
silencia**, através de guardas — `TrustManagerFactorySpec.g3` só dispara com
`condition(!contains(alg))` (com a lista reparada, `X509` não dispara g3, não crasha o
autômato: co-emissão 643 UA / 642 ISoMC dentro das chaves descartadas, ~1:1); em
`MessageDigestSpec`, o `condition(contains)` de g1 falso para MD5/SHA-1 suprime a transição de
criação (E4) e produz o ISoMC nos consumos — com a lista reparada, g1 transita e o ISoMC some.
Ou seja: **o reparo de allow-list, como está escrito no `jca_android`, remove sozinho tanto o
report quanto o ISoMC acoplado dessas 53 chaves — sem nenhuma absorção de órfão**. O reparo E5
sozinho (reports mantidos) não derruba nenhuma dessas chaves. A atribuição correta é: as
allow-lists movem o venn até 300/322 (comportamentalmente, não no modelo cirúrgico de remoção
de linhas); o reparo estrutural E5+autômatos move um bloco adicional e maior (limite 247/339);
os dois juntos, com UP+IKST, chegam a 160/383. O risco editorial vem de **ambos**, e o do E5 é
o maior — nisso a conclusão prática da auditoria (caminho 1 do D1 não protege a manchete)
permanece válida e até reforçada.

## Vereditos

| tarefa | veredito |
|---|---|
| 1. linha-base 454/423/112/342/311 | **SUSTENTADO** |
| 2. allow-lists sozinhas movem zero células | **SUSTENTADO** (no modelo de remoção de eventos; ver T4) |
| 3. leitura agressiva = 299/322; "299 é o teto" | **REFINADO/REVERTIDO**: o número correto é **300/322** (off-by-one da chave MacSpec-vazia); e 299/300 NÃO é o teto — a extensão defensável a UnsafeProtocol+InvalidKeyStoreType dá **255/355**, recuperando o ~255/~354 do plano |
| 4. risco vem do E5, não das allow-lists | **REFINADO**: a magnitude maior é mesmo do reparo estrutural (E5-máx 247/339; 76,2% das linhas e 314/454 chaves em specs portadoras), mas as 53 chaves do cenário 300/322 caem pelo reparo de allow-list sozinho (as guardas acoplam report e crash ao mesmo valor); a manchete segue desprotegida pelos dois lados |
