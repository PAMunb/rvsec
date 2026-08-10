# GAMA — errors.csv: estatística com unidades explícitas + hipóteses

Agente Gama · 2026-08-08. Fonte:
`/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal/dataset/results/errors.csv`
SHA-256 `78023defec078353bbd1f64331edb7992a2c34e29570e6ceb064fb57f37dea69` (**confere com o manifesto** `78023def…`), 26.323.122 bytes.
Scripts: `<scratch>/gama/analyze_errors.py`, `<scratch>/gama/analyze_errors2.py` (pandas via `uv run python`).

**Regime de leitura obrigatório**: dados **anteriores** a GH100/GH101 (truncamento de emissão,
colisão de wrapper, all-fail events presentes na campanha). Tudo abaixo é GERADOR DE HIPÓTESES.
Ausência de linhas nunca é evidência de conformidade; redução futura de erros nunca é evidência
de correção.

## 1. Schema congelado

`apk, rep, timeout, tool, time, spec, class, method, message, unique_msg` (10 colunas).
`unique_msg = class:::method:::spec:::error_type:::message` — **o tipo de erro só existe dentro
de `unique_msg`**; a posição de fonte (file:line do `__LOC`) **não existe em coluna alguma**.

Validação de malformados: 97.018 linhas de dados; 0 campos vazios; `unique_msg` com exatamente
5 campos `:::` em 97.018/97.018; `time` 100% numérico; `rep ∈ {1,2,3}`; `timeout ∈ {60,180,300}`;
11 tools; 0 registros em frame-form não normalizado (classe contendo `(` ou `:`). **Dataset limpo.**

## 2. Unidades — sempre separadas (proibido agregar sem declarar)

| Unidade | Valor |
|---|---|
| linhas (observação por execução×sítio×mensagem) | **97.018** |
| `unique_msg` distintos | **225** |
| APKs | **113** |
| sítios `(apk, classe, método, spec)` | **454** |
| execuções `(apk, rep, timeout, tool)` | **8.147** |

Razão linhas/sítios ≈ 214: o dataset é dominado por re-observação do mesmo sítio através de
11 tools × reps × timeouts — **pseudorreplicação massiva**; qualquer estatística por linha é inválida.

Tools (linhas): qtesting 28.221, ape 12.004, ares 9.152, droidmate 8.403, fastbot 7.950,
droidbot:bfs_greedy 6.460, droidbot:dfs_greedy 5.926, humanoid 5.381, monkey 4.759,
droidbot:bfs_naive 4.506, droidbot:dfs_naive 4.256.

## 3. Estratificação por spec (linhas / unique_msg / APKs / sítios)

| spec | linhas | unique_msg | APKs | sítios |
|---|---|---|---|---|
| SSLContextSpec | 26.312 | 30 | 62 | 125 |
| TrustManagerFactorySpec | 18.029 | 22 | 64 | 70 |
| MessageDigestSpec | 16.183 | 65 | 38 | 55 |
| SecureRandomSpec | 12.400 | 15 | 43 | 53 |
| CipherSpec | 10.923 | 32 | 21 | 72 |
| KeyStoreSpec | 10.660 | 35 | 22 | 52 |
| SignatureSpec | 990 | 11 | 4 | 9 |
| MacSpec | 837 | 6 | 7 | 8 |
| KeyPairSpec | 668 | 5 | 8 | 8 |
| KeyPairGeneratorSpec | 16 | 4 | 2 | 2 |

**13 specs com ZERO linhas** em toda a campanha: CipherInputStreamSpec, CipherOutputStreamSpec,
DHGenParameterSpecSpec, **GCMParameterSpecSpec**, HMACParameterSpecSpec, IvParameterSpecSpec,
KeyGeneratorSpec, KeyManagerFactorySpec, PBEKeySpecSpec, PBEParameterSpecSpec,
RandomStringPasswordSpec, SecretKeySpec, SecretKeySpecSpec.

Por categoria (linhas / unique_msg / APKs): InvalidSequenceOfMethodCalls 70.760 / 157 / 113;
UnsafeAlgorithm 15.444 / 47 / 80; UnsafeProtocol 8.802 / 14 / 62; InvalidKeyStoreType 2.005 / 5 / 11;
InvalidKeySize 7 / 2 / 2.

`message == "unknown"`: **70.760 linhas (72,9%)** — exatamente as InvalidSequenceOfMethodCalls
(coerente com o construtor de 3 args do `@fail`, ErrorDescription.java:34-36).

Foco do piloto:
- **CipherSpec**: 10.814/10.923 linhas (99,0%) são `unknown`/InvalidSeq; UnsafeAlgorithm tem
  **um único literal** (109 linhas): `…but found RSA/ECB/OAEPWithSHA1AndMGF1Padding.`
  Sítios Cipher dominados por classes GCM da Tink (AndroidKeystoreAesGcm 16 sítios,
  InsecureNonceAesGcmJce 10…).
- **GCMParameterSpecSpec**: 0 linhas, 0 sítios, 0 APKs — consistente com o `@fail` inalcançável
  provado no parecer diagnóstico (não é prova de que ninguém violou a regra; é prova de que a
  spec não tem canal para dizê-lo).

## 4. Hipóteses testáveis (sem atribuição causal)

- **H1 (zero-rows)**: para cada uma das 13 specs sem linhas, o zero decompõe-se em
  {handler morto (provado p/ GCM), supressão por condition, all-fail sem emissão (perda GH100),
  pointcut não casado, API não exercitada}. Teste: harness unitário por spec sobre o monitor
  pós-reparo + re-campanha; nunca inferir do zero.
- **H2 (pareamento espúrio)**: TrustManagerFactorySpec, nas células execução×sítio
  `(apk,rep,timeout,tool,classe,método)`: **4.599 com AMBOS** UnsafeAlgorithm e InvalidSeq,
  3 só-específico, **0 só-genérico**. Compatível com `@fail` espúrio acompanhando erro
  específico (família D-S9). Teste: no conjunto derivado o pareamento deve desacoplar.
- **H3 (Cipher sub-reporta específico)**: 99% unknown + um único literal UnsafeAlgorithm é
  compatível com o defeito documentado do `g3` de aridade 1 (getInstance com provider e
  transformação insegura não disparava nada → init seguinte vira InvalidSeq) e com a supressão
  do init por chave não validada. Teste: corpus discriminante com os 3 getInstance.
- **H4 (rótulo vazio)**: `but found .` = **8.843 linhas**, e **não** se confina a
  TMF/SSLContext: TrustManagerFactorySpec 8.371, **SignatureSpec 234, MessageDigestSpec 156**,
  SSLContextSpec 51, MacSpec 31. A atribuição do Grupo 8 (colisão de wrapper, GH100) cobre
  TMF/SSL; Signature/MD/Mac com rótulo vazio são **resíduo não explicado pela narrativa
  registrada** — hipótese nova a testar (mesma colisão? strings vazias reais?).
- **H5 (SecureRandom)**: 12.400 linhas, 100% unknown/InvalidSeq — compatível com os all-fail
  `c3/g4/setSeed3` do congelado (Grupo 3b).
- **H6 (MessageDigest)**: 10.135 unknown/InvalidSeq concentradas em wrappers de digest
  (okio.ByteString.digest$okio 2.695; CommonUtils.hash 1.610) — compatível com o all-fail
  `reset` e/ou reuso digest-após-digest; o evento `reset` foi removido no derivado (D-S9).
- **H7 (contagem dependente de processo)**: o dedupe in-JVM é por processo; tools que matam/
  reiniciam o app mais vezes gerariam mais linhas do mesmo sítio. Teste: modelar linhas ~ tool
  com sítio fixo antes de qualquer comparação entre tools.

## 5. Proveniência e ameaças à validade do protocolo-piloto

| # | Ameaça | Mitigação proposta |
|---|---|---|
| A1 | Pseudorreplicação (97.018 linhas ↛ independência; 454 sítios, 113 APKs, 8.147 execuções; 7 clones no subset40 conforme memória do projeto) | reportar por sítio/APK; clusterizar por APK; nunca IC sobre linhas |
| A2 | Dados pré-GH100/GH101: perdas de emissão confundem ausência com aceitação | tratar zero como terceiro estado; re-medição pós-reparo lida como forma-de-mensagem em sítio nomeado (método do Grupo 8) |
| A3 | Seleção não aleatória das 2 specs do piloto (1 portadora de D-S9/D-S11, 1 byte-idêntica) | restringir conclusões ao par; sem extrapolação às 23 |
| A4 | Unidade "sítio" sem linha de fonte (CSV não tem source): sítios multi-linha subcontados; dedupe in-JVM é por linha, dataset por método | declarar a agregação em todo número; usar unique_msg para granularidade de evento |
| A5 | jca × jca_android indistinguíveis em qualquer dataset futuro (nenhum campo de conjunto/versão na mensagem) | adicionar campo de conjunto ao ErrorDescription ou join por metadado de execução |
| A6 | Comparações com cov_mop para braços jca_android viciadas: a análise estática usa `jca` silenciosamente (ver gama_sinergia.md) | passar `mop_dir` explícito; gate de configuração |
| A7 | Contagens sensíveis ao ciclo de vida do processo (dedupe por processo, reset no restart) | dedupe por unique_msg×execução antes de comparar tools |
| A8 | Timestamps do logcat sem ano (parser infere; logcat_parser.py:437-466) e sem tz | só afeta análises temporais; registrar época da execução |

## 6. Comandos

```
sha256sum errors.csv                       # 78023def… (== manifesto)
uv run python <scratch>/gama/analyze_errors.py
uv run python <scratch>/gama/analyze_errors2.py
```
