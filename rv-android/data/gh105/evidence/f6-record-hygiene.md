# Tarefas 9.5, 9.8 e 9.19 — as três de registro, e a que foi refutada

**Data**: 2026-08-25 · **Commit da árvore**: `70877f67`
Nenhuma das três toca `.mop`, então nenhuma leva par de arnês (é o que a 9.18 diz). A
evidência de cada uma é o artefato conferido contra a sua fonte.

## 9.5 — os quatro javadocs de `Property`

O ramo "apagar as constantes" não sobreviveu a duas verificações, e as duas foram refeitas aqui:

1. `PROPERTY_CONSTANTS_AT_FREEZE` (`tests/parity/test_gh101_specset_gates.py:71-97`) lista as
   quatro, e `test_property_append_only` (`:209`) falha em qualquer remoção — materialização
   da INV-INS-132. "Append-only was the rule for adding" está errado: a regra como escrita é
   *never removed, renamed or reordered*.
2. Leitores fora do conjunto vivo, conferidos por grep na árvore inteira:

| constante | quem lê |
|---|---|
| `GENERATED_CIPHER` | **só** o arquivado `jca_android_bug_predicate` (write em `CipherSpec` ×3, `validate` nas duas streams). O congelado `jca` **não a nomeia**. |
| `GENERATED_MAC` | `jca/MacSpec.mop:73,80,87`; o arquivado; e `rvsec-crysl-mop` (`PredicateSite`, `PredicateIdioms`, `PredicateSubstrateTest`) como fixture de substrato arity-1 |
| `GENERATED_TRUST_MANAGERS` | `jca/TrustManagerFactorySpec.mop:88` — **só um `remove`**, de uma marca que nada seta; o arquivado tem write e read; `PredicateStoreTest` a usa como chave neutra |
| `WRAPPED_KEY` | `jca/CipherSpec.mop:118` — write-only, sem leitor em nenhum dos cinco conjuntos |

Apagar quebraria a compilação do monitor do `jca`, que é **o lado A do arnês diferencial**
desta change. Restou o reparo dos javadocs (P4), que é o que foi feito: cada um diz agora qual
conjunto congelado ou arquivado o lê e que nenhum conjunto vivo o escreve.
`test_property_append_only` verde depois da edição.

## 9.8 — as seis linhas ausentes da `ConscryptAliasTable`

Fonte pinada `backup/gh104-analise/OpenSSLProvider.java` (607 linhas). Contagem por serviço,
extraída da fonte e comparada com a tabela:

```
Alg.Alias total na fonte: 175
por serviço: AlgorithmParameters 8, CertificateFactory 1, Cipher 34, KeyFactory 5,
             KeyGenerator 23, KeyPairGenerator 5, Mac 24, MessageDigest 12,
             SecretKeyFactory 1, Signature 61, TrustManagerFactory 1
```

A tabela tinha 169 e nenhuma linha de `KeyFactory` nem de `CertificateFactory`. As seis
ausentes, com a linha da fonte: `KeyFactory 1.2.840.113549.1.1.1→RSA` (:195),
`1.2.840.113549.1.1.7→RSA` (:196), `2.5.8.1.1→RSA` (:197), `1.2.840.10045.2.1→EC` (:200),
`1.3.133.16.840.63.0.2→EC` (:201); `CertificateFactory X.509→X509` (:500).

Entraram **nos dois registros** — a classe Java e `data/jca_android/alias_table.csv`, que
`ConscryptAliasTableTest` compara linha a linha — em ordem alfabética de serviço, como o resto
da tabela. Contagens atualizadas em quatro lugares: javadoc da classe, o teste (renomeado para
`tableHasTheOneHundredAndSeventyFiveExtractedRows`) e três menções no
`data/jca_android/README.md`, incluindo a tabela `yes`/`no` (67/108, era 67/102) e a linha
"149 rows are in services..." que estava obsoleta desde a task 11.6 (era o número da era de 158
linhas; hoje são 160 cobertas e 15 sem especificação).

**Nenhum veredito se move**: nenhum `.mop` chama `matches` com `KeyFactory` ou
`CertificateFactory`, e as seis linhas são `no` por construção. O que muda é que o número de
linhas da tabela passa a ser **o número de registrações `Alg.Alias` do arquivo pinado**, então
a alegação de completude da classe vira medição em vez de promessa.

## 9.19(b) — as 15 linhas `transcription` do `conformance_record.csv`

Todas apontavam `rule` para `generated/api30/` e descreviam listas pré-D-15. Re-ancoradas ao
expert com os literais de hoje, mantendo o texto histórico e acrescentando um parágrafo
`D-15 (2026-08-24):` — a mesma convenção que o `divergence_record.csv` já usa
("a deleted row would make the api30 era unreadable").

Três correções substantivas saíram da conferência linha a linha:

- **`SecretKeySpecSpec`**: a linha dizia que a regra não declara nada sobre o algoritmo e que
  a allow-list ficou **sem base** (`MOP-SEM-BASE`). Verdade da api30, **falso do expert**:
  `SecretKeySpec.crysl:18` declara `keyAlgorithm in {"AES", "HmacSHA256", "HmacSHA384",
  "HmacSHA512"}`. A lista está de volta e é byte-idêntica à do congelado.
- **`MessageDigestSpec` e `SignatureSpec`**: o **custo declarado está retirado**. A api30
  admitia MD5/SHA-1 (e MD5withRSA/SHA1withRSA/SHA1withDSA); o expert não admite nenhum, as
  listas voltaram às do congelado, e `evidence/d15_c5_replay.md` mede as 5.892 linhas
  acusadas outra vez.
- **`KeyManagerFactory`, `SecureRandom`, `TrustManagerFactory`, `KeyPairGenerator`,
  `Mac`, `KeyGenerator`**: os estreitamentos ("SunX509 não existe no Android", "3072 fora",
  "HmacPBESHA1 fora") foram **revertidos** pela regra do no-narrowing; `changed_from_jca`
  passa de `yes` para `no` em nove das quinze, porque as listas voltaram a ser as do
  congelado.

Restam mudadas em relação ao congelado apenas `KeyStoreSpec` (9 tipos contra os 5 do expert,
os quatro `platform-value` citados) e `SSLContextSpec` (3 protocolos contra 2, o `TLS`).

## 9.19(a) — **REFUTADA**, e a tarefa precisa de correção

A tarefa manda trocar `constraint_table.csv:51` (`KeyStoreSpec | KeyStore.crysl:52`) e `:72`
(`SSLContextSpec | SSLContext.crysl:29`) de `IGUAL` para `MOP-MAIS-PERMISSIVO`, porque o
`.mop` admite 9 tipos contra 5 e 3 protocolos contra 2.

**A premissa lê o conjunto errado.** A coluna `mop_line` dessas linhas nomeia o **semeador**,
não o sucessor. Três oráculos independentes:

1. `jca/KeyStoreSpec.mop:23` é literalmente
   `Arrays.asList("JCEKS", "JKS", "DKS", "PKCS11", "PKCS12")` — os cinco do expert.
   `jca/SSLContextSpec.mop:23` é `Arrays.asList("TLSV1.2", "TLSV1.3")` — os dois do expert.
   As linhas de 9 e de 3 estão em `jca_android`, nas linhas 41-42 e 43.
2. `scripts/gh104_gates.py:1798-1802`, comentário do próprio gate: *"`constraint_table.csv`
   records the clause-by-clause comparison of the api30 rules against the **seed**, so it is an
   oracle for `jca` and for nothing else. Reading it on the successor set would report every
   correct transcription as a disagreement with the set it replaced."* — e o código só carrega
   o oráculo quando `set_name == "jca"`.
3. **Medido.** G-CONF deriva os vereditos por conta própria do `jca` + regras expert e
   reproduz o registro: `{"agree": 66, "disagree": 0, "not-derived": 14, "unrecorded": 0}`.
   Com as duas linhas viradas para `MOP-MAIS-PERMISSIVO`: `{"agree": 64, "disagree": 2, ...}`.

Ou seja: aplicar a 9.19(a) **introduziria** a divergência que ela diz corrigir. As duas linhas
estão certas como estão, e a permissividade deliberada do sucessor já está registrada onde
pertence — nas linhas `platform-value` do `divergence_record.csv` e agora também nas duas
linhas `transcription` re-ancoradas acima.

A varredura que a tarefa pedia ("sweep the remaining `IGUAL` rows once while there") está
feita e é mais forte do que amostragem: o `agree 66 / disagree 0` é o gate recomputando **as
80 linhas** contra a fonte. Não há terceira linha errada porque não há nenhuma.

**Pendente**: corrigir o texto da 9.19(a) via `openspec-update-change` antes de fechar a
tarefa. A parte (b) está feita.
