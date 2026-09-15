# Relatório executivo — o que as acusações da `estudo02` dizem, o que não dizem, e o que decidir

**Data:** 15/09/2026
**Para:** a equipe do RVSec / RV-Android
**Base:** a reanálise independente das acusações (`20260915_reanalise_acusacoes.md` e anexos em
`adjudicacao_nobs/reanalise_20260915/`), a comparação `jca` × `jca_android`
(`20260914_specs_jca_vs_android.md`) e verificações feitas em 15/09 nas specs `jca`, no arquivo
publicado do artigo, no código do CryptoAnalysis (CogniCrypt) e nos relatórios do CogniCrypt sobre o
corpus.

O artigo publicado não é alterado por nada deste relatório. Os números novos servem às próximas
campanhas e à tese.

---

## Para quem tem cinco minutos

A `estudo02` repetiu o experimento do artigo (11 ferramentas de teste × 163 apps × 3 repetições × 3
orçamentos de tempo) trocando o conjunto de specs antigo, `jca`, pelo novo, `jca_android`. A
campanha rodou inteira e bem. Ela contou **27 068 maus usos** no formato que o artigo usa.

Lendo esses maus usos um a um, a conclusão é que **a contagem mistura coisas muito diferentes**:

- **23,2 %** (6 278, em 50 dos 163 apps) são o que a regra CrySL de fato proíbe;
- **5,8 %** (1 572, em só 14 apps) são problemas de segurança de verdade: trust manager que aceita
  qualquer certificado, chave ou IV fixos, salt fixo;
- **64,3 %** (17 409) são **código correto que o monitor não consegue enxergar**. O monitor pergunta
  "de onde veio esta chave / este trust manager?" e, por um limite de como ele guarda essa
  informação, responde "não sei" (o código `NOBS`). A campanha contou esse "não sei" como mau uso;
- o resto é uma coleção de casos menores: decisões das próprias regras, reuso legal que a regra
  recusa, e defeitos do instrumentador.

Três coisas atenuam o susto:

1. **Nenhuma conclusão sobre ferramentas se inverte, mas as diferenças encolhem.** Refizemos o
   modelo estatístico do artigo contando só os maus usos sustentados (seção 10):
   - **se mantêm:** mais tempo dá mais maus usos (+14 % em 180 s, +21 % em 300 s), e o `ape` fica
     acima das demais ferramentas;
   - **ficam mais fracas:** as desvantagens dos dois `droidbot` "naive" e do `qtesting` em relação
     ao `monkey`, que continuam na mesma direção, mas não passam mais na correção para comparações
     múltiplas;
   - **desaparecem:** as desvantagens do `ares` e do `humanoid`, que vinham de acusações que não se
     sustentam.
2. **O problema não é novo nem exclusivo do `jca_android`.** O `jca`, usado no artigo, tinha
   totais parecidos (28 831 maus usos nos mesmos apps), mas uma composição ainda mais ruidosa:
   - cerca de 43 % eram listas das regras que recusam o jeito correto de fazer no Android;
   - cerca de 31 % eram defeitos das próprias specs;
   - o "não sei de onde veio" também estava lá, **disfarçado de erro de sequência**.

   O `jca_android` passou a dizer esse "não sei" às claras.
3. **O CogniCrypt, a ferramenta estática de referência, tem o mesmo limite, e sem distinguir.** No
   nosso corpus, 44 % dos achados dele são "origem não comprovada", 82 % desses caem no okhttp e o
   método mais acusado é o mesmo que concentra o nosso `NOBS`. A diferença é que ele não separa
   "violou" de "não consegui ver": relata tudo como erro.

**Sobre o instrumentador**, achamos quatro defeitos:

- um evento que dispara duas vezes num único `getInstance`;
- chamadas a `getEncoded()` que nunca recebem monitor;
- ganchos pulados quando a chamada é destino de um desvio;
- um tipo aninhado resolvido errado.

Eles respondem por **cerca de 3 % dos maus usos** (e um quarto das linhas brutas), e **tudo o que
eles acrescentam de falso pode ser retirado dos dados sem rodar nada de novo**.

**Recomendação:**

- não rodar a `estudo02` de novo;
- limpar a contagem na análise, como já foi feito para o modelo (seção 10);
- tratar o `NOBS` com um catálogo de vereditos por trecho de código;
- preparar os consertos do instrumentador e do gerador de relatórios, que estourou a memória, para
  valerem nas próximas campanhas.

O escopo desses consertos está no Apêndice A. As decisões pedidas à equipe estão na seção 13.

---

## 1. O que foi a `estudo02`

É a repetição local do Estudo 2 da tese, o experimento do artigo, com três diferenças de peso:

- **Specs:** o conjunto de specs é o `jca_android` (47 arquivos `.mop`) no lugar do `jca` (23). É
  o fator estudado.
- **Instrumentador:** os apps foram instrumentados pelo instrumentador que opera direto no DEX
  (dexlib2).
- **Monkey:** o `monkey` roda com a opção de seguir após crash e ANR. Isso o deixou mais forte, e
  ele é a referência do modelo.

**Números da campanha:**

- 16 137 execuções, todas concluídas; 15 650 admissíveis depois da validação;
- cerca de seis dias de máquina em 10 containers;
- veredito, modelo e tabelas comitados em 14/09.

Uma primeira leitura das acusações foi feita em 14/09. Ela exagerou alguns "defeitos" e não conferiu
as acusações que não eram `NOBS`. Em 15/09 foi refeita do zero, por censo e não por amostra, com
cada trecho de código relido na fonte: a spec, a regra CrySL, o código do app ou da biblioteca e o
bytecode do APK instrumentado. **É essa segunda leitura que vale.** A primeira fica como registro.

## 2. Como se conta um "mau uso"

É preciso separar três unidades, porque os números mudam muito conforme a unidade:

- **Linha.** Um relato do monitor gravado no `errors.csv`. O monitor não repete um relato idêntico
  dentro do mesmo processo, então uma linha é "este trecho de código recebeu esta acusação nesta
  execução", não uma chamada. A campanha tem **139 916 linhas**.
- **Mau uso por execução.** A combinação (app, ferramenta, repetição, orçamento, classe, método,
  spec). É a unidade do artigo ("maus usos únicos"). A campanha tem **27 068**, em 91 dos 163 apps.
- **Sítio.** O trecho de código acusado: (classe, método, spec, código de erro). Um mesmo sítio de
  uma biblioteca popular aparece em dezenas de apps e em centenas de execuções. É a unidade certa
  para **julgar**, porque o veredito sobre um trecho de código vale para todas as vezes em que ele
  roda.

## 3. O que os 27 068 maus usos realmente são

| grupo | maus usos | % |
|---|---:|---:|
| **Sustentado pelas regras** | **6 278** | **23,2** |
| … dos quais relevantes para segurança | 1 572 | 5,8 |
| Código correto que o monitor não consegue ver | 17 409 | 64,3 |
| Objeto criado sem que o monitor visse a criação | 956 | 3,5 |
| Só o efeito do disparo duplo do `getInstance` | 654 | 2,4 |
| Reuso legal que a regra recusa | 572 | 2,1 |
| Produtor que falta no conjunto de specs | 552 | 2,0 |
| Acusação que a regra faz de propósito | 537 | 2,0 |
| Outros efeitos do instrumentador | 110 | 0,4 |

Cada grupo, em palavras:

- **Sustentado pelas regras.** O programa faz o que a regra proíbe. A maior parte (4 706) é fiel à
  regra e **sem importância prática**:
  - MD5 ou SHA-1 para nomear arquivos de cache ou calcular impressões digitais;
  - AES/ECB usado como peça interna do CMAC;
  - HMAC-SHA1 em códigos de uso único (HOTP/TOTP), que as RFCs exigem;
  - RSA de 3 072 bits, que a lista da regra recusa.

  Os relevantes são poucos e concretos: um app que aceita qualquer certificado **por padrão**
  (`feeder`), chaves e IVs embutidos no código (`myexpenses`, `redreader`, `mtgfam`), senhas
  guardadas como SHA-1 sem salt (Fossify), e alguns casos discutíveis (poucas iterações de PBKDF2,
  por exemplo).
- **Código correto invisível.** Explicado na seção 4. É o grupo que domina.
- **Objeto sem evento de criação.** Explicado na seção 5.
- **Disparo duplo.** Um defeito do instrumentador, explicado na seção 6.
- **Reuso legal recusado.** Reinicializar um `Cipher` ou `Mac` depois de usá-lo é permitido pela API
  e é o que bibliotecas como tink e ktor fazem. A regra CrySL não prevê o ciclo, e a spec a
  transcreve fielmente.
- **Produtor ausente.** A regra exige uma origem que existe e é observável, mas nenhuma spec a
  registra. Caso único: a chave pública do TLS do ktor, construída por `ECPublicKeySpec`.
- **Decisão da regra.** A regra acusa de propósito, e a transcrição é fiel. Dois casos:
  - bytes aleatórios usados como chave, quando a regra exige material preparado;
  - chaves do AndroidKeyStore obtidas por `getEntry`, quando a regra só credita `getKey`.

### Em quantos apps

| recorte | apps | % dos 163 |
|---|---:|---:|
| Com alguma acusação do monitor (bruto) | 91 | 55,8 % |
| **Com algum mau uso sustentado (os 6 278)** | **50** | **30,7 %** |
| Com algum mau uso relevante para segurança (os 1 572) | 14 | 8,6 % |

Dos 50 apps com mau uso sustentado, **36 só têm casos sem relevância prática**, como MD5/SHA-1 para
nomear cache. Os outros 14 têm algo relevante.

A contagem é muito concentrada: 5 apps somam 45 % dos 6 278, e 10 apps somam 61 %.

| app | total | mau uso real (`NOBS`) | discutível | sem relevância |
|---|---:|---:|---:|---:|
| `passportreader` | 990 | 99 | 0 | 891 |
| `myexpenses` | 594 | 396 | 198 | 0 |
| `glpi` | 575 | 0 | 80 | 495 |
| `redreader` | 366 | 297 | 0 | 69 |
| `avare` | 297 | 0 | 0 | 297 |
| `dsub2000` | 198 | 99 | 99 | 0 |
| `feeder` | 194 | 98 | 0 | 96 |

Os números altos vêm de repetição, não de muitos problemas por app. Um trecho que roda na abertura
do app aparece em quase todas as 99 execuções (11 ferramentas × 3 orçamentos × 3 repetições), e por
isso muitos apps somam 99, 198 ou 297. Tabela completa em `docs/20260915_modelo_rq1_desfechos.md`.

## 4. O "não observado" (`NOBS`) explicado

### 4.1 A ideia

Várias regras CrySL não falam só de *valores* ("o algoritmo tem de ser AES") e de *ordem* ("chame
`init` antes de `doFinal`"). Elas falam de **origem**:

- "a chave passada ao `Cipher` tem de ter saído de um gerador de chaves";
- "o trust manager passado ao `SSLContext` tem de ter saído de um `TrustManagerFactory`";
- "o IV tem de ser aleatório".

O monitor verifica a origem com uma espécie de caderno de anotações:

1. Quando um **produtor** roda (por exemplo, `KeyGenerator.generateKey()`), o monitor anota: "este
   objeto é uma chave gerada".
2. Quando o **consumidor** roda (`Cipher.init(chave)`), ele procura aquele objeto no caderno.

A resposta tem três valores:

- **satisfeito**: a anotação existe e confere;
- **violado**: a anotação existe e contradiz a exigência;
- **não observado**: não há anotação nenhuma para aquele objeto. Sai o código `NOBS`.

O detalhe que decide tudo: o caderno identifica o objeto pelo **endereço na memória**, não pelo
conteúdo. Então, sempre que um programa correto troca o objeto por outro equivalente (copia um
array, embrulha o objeto num array novo, relê bytes do disco), o objeto novo chega ao consumidor sem
anotação. O monitor diz "não observei", e a campanha contou isso como mau uso.

**O programa não tem erro. O erro está em contar o "não sei" como "está errado".** As próprias specs
avisam: no Android, "não observado" é tão frequentemente um limite de alcance do instrumento quanto
um mau uso.

### 4.2 Os caminhos corretos que o monitor não vê

Estes cinco mecanismos explicam os 17 409. Todos foram conferidos no código.

**a) `null` significando "use o padrão do sistema".** O okhttp, a biblioteca HTTP mais usada no
Android, prepara a verificação de certificados assim:

```kotlin
val factory = TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm())
factory.init(null as KeyStore?)   // null = use os certificados do sistema
```

- **O que o programa faz:** passar `null` é a forma documentada, e correta, de pedir os certificados
  do sistema.
- **O que a regra pede:** um `KeyStore` que o monitor viu ser carregado. `null` não é um.
- **Por que isso acusa:** foi uma decisão consciente, registrada em agosto no próprio arquivo da
  spec, que reconhece o custo.

**b) Array novo em volta do mesmo objeto.** Logo depois, o okhttp faz:

```kotlin
sslContext.init(null, arrayOf(trustManager), null)
```

1. O monitor anotou a origem no array devolvido pela fábrica.
2. O okhttp tirou o trust manager de dentro desse array.
3. Depois o colocou num **array novo**.

O trust manager é o mesmo e é correto, mas o array é outro, e o caderno não o conhece. Nessa mesma
linha saem ainda dois "não observados" pelo motivo (a): o `null` do gerenciador de chaves (o app não
usa certificado de cliente) e o `null` do gerador aleatório (usar o do sistema).

Esses dois métodos do okhttp, sozinhos, respondem por **43,5 %** de todo o código correto
invisível. Oito métodos de biblioteca respondem por 73 %.

**c) Chave relida do armazenamento.** A biblioteca tink (Google):

1. gera uma chave aleatória numa execução;
2. guarda a chave cifrada nas preferências do app;
3. na execução seguinte, lê os bytes de volta e monta a chave.

A origem foi aleatória, mas aconteceu em outro processo. Os bytes chegam "sem história".

**d) IV lido da mensagem cifrada.** Ao decifrar, o IV correto é o que veio junto com a mensagem. A
regra pede um IV aleatório. Ele foi aleatório quando a mensagem foi cifrada, talvez em outro
aparelho, e o monitor não tem como saber.

**e) IV calculado por projeto.** No AES-SIV, o IV é derivado da própria mensagem. No TLS, o nonce de
cada registro vem de um contador. Nos dois casos, não ser aleatório é o correto.

### 4.3 Os `NOBS` que são mau uso de verdade

São **1 109 maus usos em 10 apps**, e todos têm a mesma cara: a origem não foi vista porque **não
existe origem boa**.

| app | o que faz | maus usos |
|---|---|---:|
| `myexpenses` (biblioteca de licenças do Google embarcada) | salt literal e IV estático | 396 |
| `redreader` | chave derivada do certificado de assinatura do app; IV zerado | 297 |
| `passportreader` (anúncios do Google) | chave = bytes fixos em Base64 | 99 |
| `dsub2000` | trust manager que aceita tudo (só usado se o usuário ligar "permitir inseguro") | 99 |
| `metadataremover` | `SecureRandom` com semente fixa (sem efeito prático no Android 7+) | 99 |
| `feeder` | trust manager que aceita tudo, **ligado por padrão** | 98 |
| `mtgfam` | texto de recurso usado como chave AES; IV = chave | 15 |
| outros três | derivação caseira de chave; trust-all atrás de opção | 6 |

### 4.4 O que tem conserto no monitor e o que não tem

| mecanismo | tem conserto? |
|---|---|
| (b) array novo | **Sim, em princípio.** Anotar a origem em cada trust manager, e não só no array, e conferir os elementos. |
| (a) `null` = padrão | **É uma decisão, não um defeito.** Pode ganhar um código próprio ("pediu o padrão do sistema"), mas isso muda o que é acusado. |
| (c), (d), (e) | **Não.** Nenhum monitor em tempo de execução sabe se bytes lidos do disco foram aleatórios um dia. Esses continuarão "não observados", e o certo é **não contá-los como mau uso**. |

## 5. Como um objeto é criado sem evento de criação

O monitor só enxerga chamadas que estão **no código do APK** e que a spec lista. O autômato de cada
spec começa esperando a criação do objeto (`getInstance` ou o construtor). Se o primeiro evento que
ele vê é um uso (`update`, `nextBytes`, `getPublic`), ele acusa "sequência inválida". Um objeto pode
nascer fora da vista do monitor de três jeitos:

1. **Dentro do sistema Android, que não está no APK.** O caso mais comum: um par de chaves obtido por
   `KeyPairGenerator.generateKeyPair()`. O `new KeyPair(...)` roda dentro do framework, e o monitor
   só vê o primeiro `getPublic()` (267 maus usos). A regra CrySL exige ver o construtor. Manter essa
   exigência foi decisão registrada em agosto, tomada sabendo do custo: a alternativa faria perder a
   cadeia de origem das chaves usadas depois por `Signature` e `Cipher`.
2. **Por um caminho que a regra não lista.**
   - A biblioteca criptográfica spongycastle cria o seu gerador aleatório por um construtor
     protegido de `SecureRandom` (495).
   - O Guava obtém um `MessageDigest` por `clone()` (28).
   - O `AlgorithmParameters` pode vir de `cipher.getParameters()` (17).
3. **Por uma subclasse própria.** A biblioteca kmp-tor usa uma classe de digest própria (149).

Em todos esses casos, o programa está certo, e a acusação de "sequência inválida" é um efeito de
alcance, não um mau uso.

## 6. Os defeitos do instrumentador

O instrumentador é a ferramenta que insere as chamadas ao monitor dentro do APK. Achamos quatro
defeitos com efeito medido, mais uma divergência já conhecida.

### 6.1 O disparo duplo do `getInstance`

A spec do `TrustManagerFactory` declara dois eventos, um para cada forma da API:

```
g1:  getInstance(String)          -- um argumento
g2:  getInstance(String, ...)     -- algoritmo mais provedor
```

**Por que dispara duas vezes.** O "`...`" de `g2` também aceita zero argumentos a mais, então o
padrão de `g2` casa com a chamada de um argumento. No AspectJ, a ferramenta de referência, uma
segunda cláusula (`args(alg, *)`, que exige dois argumentos) separa os dois eventos. O instrumentador
DEX aceita essa cláusula sem checar quantos argumentos a chamada tem, e dispara os dois eventos para
uma única chamada.

**O que isso faz.** Uma sequência correta do okhttp vira:

| no programa | o monitor vê | resultado |
|---|---|---|
| `getInstance("PKIX")` | `g1` | ok |
| (a mesma chamada) | `g2` | "sequência inválida" **falsa**; o autômato volta ao início |
| `init(null)` | `init` fora de hora | "sequência inválida" **falsa**, mais o "não observado" do `null` |
| `getTrustManagers()` | fora de hora | "sequência inválida" **falsa** |

Das quatro linhas, três são o artefato. O mesmo acontece com o `KeyManagerFactory` e o
`SecureRandom`. No `SecureRandom` há um efeito a mais: a falha descarta bytes aleatórios que
esperavam ser anotados, e isso gerou 3 "não observados" falsos adiante.

**Tamanho:** 35 694 linhas (25,5 % de todas) e 654 maus usos que não têm nada além disso.

**Situação:** o disparo em si está registrado na especificação do instrumentador, que decidiu
**contar** os casos antes de filtrar. A consequência no autômato não estava registrada.

### 6.2 `getEncoded()` chamado sobre um subtipo do sistema não recebe monitor

- **O que deveria acontecer:** quando o código faz `secretKey.getEncoded()`, o monitor deveria
  anotar os bytes devolvidos como "material de chave".
- **O que acontece:** o instrumentador procura o método entre os métodos **declarados** pelo tipo
  `SecretKey`. Esse tipo herda `getEncoded` de `Key` sem redeclará-lo, então nenhum monitor é
  inserido, e nada avisa.
- **Tamanho:** 1 559 chamadas sem monitor, em 117 apps.
- **Direção:** a anotação não é gravada, então o defeito só **cria** "não observados" falsos; nunca
  esconde uma violação.
- **Efeito nesta campanha:** de 47 a 94 maus usos (app `photok`).
- **Situação:** não documentado.

### 6.3 Gancho pulado quando a chamada é destino de um desvio

O instrumentador insere a chamada ao monitor imediatamente **antes** da chamada monitorada. Mas, se
algum `if` ou `goto` do método aponta para a chamada, o desvio continua apontando para a instrução
original e **passa por cima do monitor**. Conferido no app `aegis`:

```
if (nonce == null) goto L
...
    chamada ao monitor            <- inserida antes do init
L:  Cipher.init(modo, chave)       <- o desvio chega aqui direto
```

- **Efeito, nos dois sentidos:**
  - no caminho do desvio, o monitor não vê o `init`, e os relatos daquele ponto se perdem (falso
    negativo);
  - a chamada seguinte vira "sequência inválida" (falso positivo).
- **Tamanho:** 424 de 7 838 ganchos desse tipo (5,4 %), em 39 apps, quase todos dentro do
  BouncyCastle embarcado.
- **Efeito medido nesta campanha:** 13 maus usos falsos. Os falsos negativos dentro de bibliotecas
  não podem ser medidos, porque a cobertura só registra métodos do app.
- **Situação:** não documentado.

### 6.4 Tipo aninhado resolvido errado

`KeyStore.getEntry` e `setEntry` nunca recebem monitor: o nome `KeyStore.ProtectionParameter` é
lido como se fosse um pacote, e não uma classe interna. **Sem efeito nesta campanha**, mas uma
campanha com apps que usem `setEntry` seguido de `store` teria acusação falsa.

### 6.5 Divergência já conhecida: monitor "depois" não roda quando a chamada lança exceção

Documentada em 27/08 (`docs/20260827_divergencia_after_dexlib2_ajc.md`):

- **O que acontece:** no instrumentador DEX, o monitor que deveria rodar *depois* de uma chamada não
  roda se a chamada lança exceção. No AspectJ ele roda. O próprio comentário do código promete o
  comportamento do AspectJ.
- **Superfície:** 58 dos 202 eventos do `jca_android`.
- **Efeito nesta campanha:** não medido.

Não é um conserto trivial, porque muda o que é acusado. É uma decisão (seção 13).

### 6.6 Não é do monitor

Algumas linhas se perdem na gravação do logcat: diferenças de 1 a 2 relatos por sítio. É perda de
registro, não erro de monitoramento.

## 7. E o `jca` do artigo? As specs estavam erradas?

Os totais são parecidos por coincidência:

- nos 162 apps em comum, 28 831 maus usos no `jca` contra 27 068 no `jca_android`;
- no arquivo publicado, 28 930 maus usos em 113 apps.

Decompondo as acusações publicadas por mensagem, spec e mecanismo, conferidos nos arquivos `.mop`
do `jca` e nas regras CrySL:

| mecanismo no `jca` | maus usos | % |
|---|---:|---:|
| **A. A lista da regra recusa o jeito correto de fazer no Android** | **12 358** | **42,7** |
| • `SSLContext.getInstance("TLS")`: a regra lista só "TLSv1.2" e "TLSv1.3"; no Android, "TLS" já entrega essas duas versões | 8 352 | |
| • `KeyStore` do tipo `AndroidKeyStore` (ou `BKS`, o padrão do Android), fora da lista da regra | 3 698 | |
| • `TrustManagerFactory` "X509", que no Android é outro nome de "PKIX" | 308 | |
| **B. Defeito da própria spec `jca`** | **9 000** | **31,1** |
| • "esperava um de … mas encontrou ." (algoritmo vazio), cerca de 4 300 deles no `TrustManagerFactory` do okhttp e do ktor, que pedem o algoritmo padrão | 4 545 | |
| • `SecureRandom`: o autômato não aceita um segundo `nextBytes` no mesmo objeto, mas a regra aceita repetições | 4 455 | |
| **C. Origem da chave não vista, relatada como "sequência inválida"** | **4 145** | **14,3** |
| **D. MD5/SHA-1** (fiel à regra, raramente relevante) | 2 705 | 9,3 |
| Resto (criação não vista, reuso do `Mac`, OAEP-SHA1, "SSL", …) | 722 | 2,5 |

**Em quantos apps.** No `jca`, **113 dos 163 apps (69,3 %)** tinham alguma acusação. No bruto da
`estudo02`, são **91 dos 163 (55,8 %)**.
- **São comparáveis:** a unidade é a mesma, app com qualquer acusação do monitor, sem julgamento.
- **A ressalva:** mudaram as specs (é o fator estudado), a configuração do `monkey` e a imagem da
  campanha.

| nos 162 apps em comum | apps |
|---|---:|
| com acusação nos dois conjuntos | 90 |
| só no `jca` | 22 |
| só no `jca_android` | 1 |

O `jca` não tem equivalente dos 50 apps com mau uso sustentado, porque as suas acusações não foram
julgadas uma a uma. O que dá para dizer:
- **54 dos 113 apps** só tinham acusações dos grupos A e B (valor correto recusado pela lista, ou
  defeito da spec), que o `jca_android` já não faz;
- **os outros 59** têm algo nos grupos C, D ou no resto, e não se sabe quantos se sustentariam.

**O grupo C é o parentesco com o `NOBS`.** No `jca`, a pergunta de origem da chave estava escrita
como condição do evento `Cipher.init`. No monitor gerado, uma condição falsa faz o evento
**desaparecer** sem relato. O `Cipher` fica parado no estado anterior, e a chamada seguinte
(`doFinal`) é acusada de "sequência inválida". Ou seja:

- o `jca` também não via essas origens;
- mas, em vez de dizer "não observei", ele acusava o programa de chamar métodos na ordem errada;
- os métodos mais acusados assim são os mesmos que hoje aparecem como código correto invisível
  (tink `AesSiv`, `AndroidKeystoreAesGcm`, `PrfAesCmac`).

O `jca_android` mudou isso de propósito, e o comentário da spec explica o motivo.

**O grupo B também já está corrigido no `jca_android`.**
- **Algoritmo vazio.** O `jca` guardava o algoritmo numa variável preenchida pelo evento do
  `getInstance`. O `jca_android` pergunta ao próprio objeto no momento do uso (`mf.getAlgorithm()`,
  `jca_android/TrustManagerFactorySpec.mop:122-124`) e aceita os apelidos do Android ("X509" = PKIX).
  Na `estudo02`, das 19 448 linhas de acusação de valor (algoritmo, protocolo, tamanho de chave),
  **nenhuma tem valor vazio**, e o `TrustManagerFactory` não tem nenhuma acusação de algoritmo.
- **Grupo A.** As listas passaram a aceitar os valores corretos da plataforma, como "TLS",
  `AndroidKeyStore` e `BKS`.

O que ainda aparece nos mesmos métodos do okhttp e do ktor é outra coisa: o disparo duplo (seção 6.1)
e o `init(null)` lido como não observado (seção 4.2).

**Então as specs `jca` estavam erradas?** A resposta depende da pergunta:

- **Eram fiéis à regra?** Em boa parte, sim. O grupo A e o MD5/SHA-1 transcrevem listas que estão na
  regra CrySL. O problema foi aplicar ao Android listas escritas para Java de desktop.
- **Apontavam problema de segurança?** Quase nunca, nos grupos A, B e D. O que pode ser relevante
  está dentro dos 4 145 do grupo C e de parcelas pequenas. Não foi medido quanto.
- **Eram artefato da spec?** O grupo B inteiro, sim: 31 %.

Se "mau uso" for lido como "erro do programa", a maior parte do que o artigo contou não se sustenta.
Isso vale para os dois conjuntos, por mecanismos diferentes. **Não medimos se o ruído do `jca` se
distribui por igual entre as ferramentas**, que é o que importaria para o ranking publicado. O
artigo não será revisto. Isso fica como lição para as próximas campanhas.

## 8. E o CogniCrypt?

O CogniCrypt (CryptoAnalysis) verifica as mesmas regras CrySL, mas **sem executar o programa**:
segue os valores pelo código. Conferido no código-fonte:

- **Uma exigência de origem não comprovada vira sempre o mesmo erro, `RequiredPredicateError`.** Não
  existe um estado "não sei" (`PredicateHandler.java:236-237`).
- **Valores que vêm de onde a análise não entra** (métodos nativos, classes excluídas, chamadas sem
  destino conhecido) **são tratados como objetos novos, sem origem** (`CogniCryptIntAndStringBoomerangOptions.java:44-48`).
  O resultado é acusação, não silêncio: o mesmo limite de alcance do nosso `NOBS`, contado como erro.
- **A assimetria:** quando o CogniCrypt não consegue descobrir estaticamente um valor (um nome de
  algoritmo que vem de uma variável, por exemplo), ele **não acusa nada**
  (`ConstraintSolver.java:549-551`). O monitor, ao contrário, vê o valor real em execução.

Há relatórios do CogniCrypt 5.0.1 para o nosso corpus (`rvsec-dataset/cognicrypt/`, 144 dos 163
apps da campanha):

- 1 708 achados, dos quais **758 (44 %) são "origem não comprovada"**;
- **86 %** desses 758 são de `SSLContext` e `TrustManagerFactory`, e **82 %** caem no okhttp;
- o método mais acusado é `Platform.newSslSocketFactory` (360), o mesmo que concentra o nosso
  `NOBS`;
- as mensagens contam a mesma história: gerenciador de chaves nulo, trust managers não comprovados,
  gerador aleatório nulo, `KeyStore` nulo.

**O limite é compartilhado.** A regra pede uma origem que o programa correto não precisa produzir de
forma visível, e nenhuma das duas técnicas enxerga através de cópias, `null`s com sentido de padrão
ou código fora do seu alcance. **O que é específico de cada uma:** o monitor perde a origem por
guardar objetos por endereço; a análise estática, por não seguir o valor através de código que ela
não analisa. **A diferença de tratamento:** o `jca_android` separa "violou" de "não observei"; o
CogniCrypt entrega as duas coisas sob um mesmo nome.

Uma nota de contexto. O pacote de replicação do RVSec compara monitoramento, CogniCrypt e
CryptoGuard e reporta F1 médio de 95 %, 83 % e 78 %. Essa comparação usou benchmarks Java pequenos,
onde o produtor costuma estar visível, e esse limite quase não aparece. **Uma ressalva:** o código
que lemos é de um checkout do CryptoAnalysis, e os relatórios do corpus vieram da versão 5.0.1. Não
conferimos se os trechos citados são idênticos nas duas.

## 9. Dá para aproveitar a campanha?

**Sim.** Todo o ruído medido *para mais* (acusação que não devia existir) sai só com análise. O
`errors.csv` guarda o código e o evento de cada relato, e isso basta:

| o que atrapalha | como sai sem rodar de novo | tamanho |
|---|---|---|
| "não observado" | pelo código (`-NOBS-`) | 44,7 % das linhas |
| Disparo duplo | regra já escrita: "sequência inválida" de `TrustManagerFactory`, `KeyManagerFactory` ou `SecureRandom` cujo gatilho é o `g2` | 25,5 % das linhas; 654 maus usos |
| "Sequência inválida" em cascata de uma falha de valor | mesmo trecho, mesmo mau uso | 11,7 % das linhas |
| `getEncoded` sem monitor e gancho pulado | identificados um a um | 47–94 e 13 maus usos |

O que **não** se recupera sem rodar é o que deixou de ser relatado:

- **ganchos pulados em bibliotecas** (417 pontos): a cobertura não registra código de biblioteca;
- **monitor "depois" com exceção**: não medido;
- **violações de ordem reais escondidas pelo disparo duplo**: só nas três specs afetadas. Os valores
  continuam checados, porque o monitor confere o valor antes de decidir a transição.

O `getEncoded` não entra aqui: ele só cria acusação falsa, nunca esconde uma verdadeira.

Onde deu para medir, esse lado ausente foi pequeno. No código de app, o único ponto afetado que
executou foi o do `aegis`, e em 4 de 6 execuções um mau uso sumiu.

## 10. O modelo refeito com a contagem limpa

### O que foi feito

O artigo compara as ferramentas com um modelo estatístico:
- **O que se conta:** uma linha por execução, com o número de maus usos distintos que ela achou.
- **O que explica a contagem:** a ferramenta (referência: `monkey`), o orçamento (referência: 60 s)
  e o tamanho do app em código que alcança APIs monitoradas.
- **Tipo de modelo:** binomial negativo, com erros-padrão agrupados por app e correção de Holm sobre
  as 10 comparações com o `monkey`.
- **Leitura:** cada ferramenta ganha uma razão de taxas (IRR). 0,85 quer dizer "acha 15 % menos que o
  `monkey`, com o resto igual".

Refizemos o **mesmo** modelo trocando só o que se conta:

| desfecho | maus usos | execuções com zero | apps com algum |
|---|---:|---:|---:|
| bruto (o do veredito de 14/09) | 27 068 | 61,1 % | 91 |
| sustentado pelas regras | 6 278 | 82,0 % | 50 |
| sustentado sem os 379 discutíveis | 5 899 | 82,0 % | 50 |
| relevante para segurança | 1 572 | 95,3 % | 14 |

Como foi feito:
1. **Arquivos limpos.** `experimento-estudo02/scripts/desfechos_sustentados.py` gera
   `errors_sustentado.csv` e `errors_relevante.csv` a partir do `errors.csv`, que não muda.
2. **Contagem por execução.** O script conta os maus usos de cada arquivo. Antes de seguir, ele
   confere que a mesma contagem feita no `errors.csv` original reproduz a do modelo original. Bateu
   nas 16 137 execuções.
3. **Modelo.** `rq1_estudo02.py` ganhou a opção `--outcome`. Sem ela, a saída continua idêntica, byte
   a byte, à do veredito.
4. **Resultados:** `docs/20260915_modelo_rq1_desfechos.md` (lado a lado) e
   `docs/20260915_modelo_rq1_sustentado.txt` (completo, com as sensibilidades).

**A regra de leitura foi fixada antes de rodar.** Uma conclusão se mantém quando a razão fica do
mesmo lado de 1 **e** cada estimativa cai dentro do intervalo de 95 % da outra. O desfecho sustentado
tem um quarto dos casos, então os intervalos alargam: perder significância com intervalos que se
sobrepõem é menos dado, não efeito diferente.

### O que mudou e o que não mudou

**Orçamento: se mantém.** Mais tempo dá mais maus usos sustentados: +14 % em 180 s e +21 % em 300 s,
com significância. No bruto, +17 % e +25 %.

**Ferramentas contra o `monkey`: nenhuma troca de lado, e nenhuma passa mais em Holm.** No bruto,
quatro passavam.

| ferramenta | IRR bruto | IRR sustentado | leitura |
|---|---:|---:|---|
| `droidbot` bfs naive | 0,808 | 0,883 | continua abaixo (intervalo sem o 1, sem correção); não passa em Holm |
| `droidbot` dfs naive | 0,808 | 0,874 | idem |
| `qtesting` | 0,764 | 0,855 | idem; e some quando se tiram as execuções que a própria ferramenta interrompeu, como já acontecia no bruto |
| `ares` | 0,912 | 0,973 | **a desvantagem desaparece**: a estimativa bruta cai fora do intervalo do sustentado |
| `humanoid` | 0,885 | 0,969 | **idem** |

**`ape` acima das outras ferramentas: a direção se mantém contra as nove.** Continua significativo,
sem correção, contra sete delas. Contra `ares` (p 0,055) e `droidmate` (p 0,13) já não é. Os
tamanhos diminuem: contra o `qtesting`, a razão cai de 1,34 para 1,22.

**Os discutíveis não pesam.** Tirar os 379 dá praticamente o mesmo resultado, então a classificação
deles não decide nada.

**O tamanho do app perde o efeito.** A razão da covariável vai de 1,135 para 1,010. A associação "app
maior, mais maus usos" vinha das acusações que não se sustentam.

**O desfecho "relevante" não compara ferramentas.**
- Em 6 dos 14 apps, o mau uso relevante aparece em 99 a 100 % das execuções, sempre com a mesma
  contagem: `myexpenses`, `redreader`, `dsub2000`, `feeder`, `passportreader`, `metadataremover`.
- Em outros 2, aparece em 76 a 81 % das execuções: `nextcloudcookbook` e `glpi`.

É código que roda na abertura do app, e qualquer ferramenta o alcança: cada ferramenta acha entre 139
e 159. Esse desfecho mede o app, não a ferramenta, e fica só descritivo.

**Em uma frase:** o ruído não inverte nenhuma ferramenta, mas **infla as diferenças**. Com a contagem
limpa, as ferramentas ficam mais parecidas entre si, duas desvantagens desaparecem, e continuam de pé
o efeito do orçamento e a posição do `ape`.

**Ressalva:** o desfecho sustentado herda a classificação da reanálise, inclusive os pontos da seção
14 que não foram conferidos um a um.

## 11. Como tratar o `NOBS`

A proposta é tratar na **análise**, não no monitor. O `NOBS` é honesto: diz exatamente o que o
monitor sabe. O erro foi somá-lo em "mau uso". Três camadas:

**Camada 1 — três desfechos em vez de um.**
- **Bruto:** como hoje. Serve para comparar com o artigo.
- **Sustentado pelas regras:** violações sem artefatos e sem cascata, mais os `NOBS` julgados mau
  uso real.
- **Relevante para segurança:** 1 572 maus usos em só 14 apps. Não separa ferramentas (seção 10);
  usar de forma descritiva.

A camada 1 já está implementada para esta campanha (seção 10).

**Camada 2 — um catálogo de vereditos por trecho de código, versionado como dado.**
- A chave é (classe, método, spec, código), com a versão da biblioteca quando for o caso.
- O script de consolidação aplica o catálogo.
- Um trecho fora do catálogo aparece como **não julgado**, com a sua contagem. Nunca é somado em
  silêncio.
- É barato: 181 trechos nesta campanha, e 73 % da massa invisível está em 8 métodos de bibliotecas
  que se repetem entre apps (okhttp, tink, ktor). Numa campanha nova, só se leem os trechos novos.
- **Cuidado:** o comportamento de uma biblioteca pode mudar entre versões.

**Camada 3 — reduzir o invisível na fonte, onde há conserto.**
- Array novo: anotar a origem por elemento.
- Cópias feitas em código instrumentado: propagar a anotação na cópia.
- Relidos do disco, IV da mensagem, IV derivado: continuam `NOBS` e caem na camada 2.

**Uma ideia, ainda não testada, para achar mau uso entre os `NOBS` automaticamente:** registrar uma
impressão (hash) do valor quando sai `NOBS`.
- Uma chave ou IV **idêntico em instalações e execuções independentes** é candidato forte a valor
  embutido no código. Um valor aleatório muda a cada instalação.
- Para trust managers, o equivalente seria registrar a classe: uma classe do próprio app no lugar da
  do sistema merece leitura.
- **Limite:** não decide tudo. A chave do `redreader`, derivada do certificado do app, também é
  estável, e é mau uso. Serve para priorizar a leitura, não para dar o veredito.

As camadas 1 e 2 mudam só a análise. A camada 3 e a ideia **mudam o que o monitor acusa**. Por isso
deveriam ser medidas numa rodada à parte, sem misturar com os consertos do instrumentador. Misturar
impede saber quanto cada mudança contribuiu.

## 12. Rodar a `estudo02` de novo, ou consertar para as próximas?

**Proporção antes de tudo:** os defeitos do instrumentador respondem por cerca de 3 % dos maus usos.
A massa grande, os 64 % de código correto invisível, **não é defeito do instrumentador**, e rodar de
novo com ele consertado não a reduz.

### Opção 1 — consertar e rodar de novo

**Ganhos:**
- recupera os relatos que hoje se perdem (ganchos em bibliotecas, monitor "depois" com exceção);
- dados brutos limpos, sem depender de filtro posterior;
- valida os consertos em execução real.

**Riscos e custos:**
- **Custo:** cerca de seis dias de máquina, mais reinstrumentar os 163 apps, smoke e pós-processamento.
  Na última vez, o pós-processamento morreu por falta de memória (Apêndice A, item A6) e houve
  reinícios.
- **Causas misturadas:** as ferramentas não exploram os apps de forma determinística. Com 3
  repetições, a diferença entre as duas campanhas mistura o efeito do conserto com variação
  aleatória, e não há como separar.
- **Regressão:** checar a aridade no casamento de eventos remove eventos, e um erro ali silencia
  eventos legítimos. Mexer no destino dos desvios toca o mesmo mecanismo de que outras guardas
  dependem.
- **Retrabalho:** o veredito, o modelo e as tabelas comitados teriam de ser refeitos.

### Opção 2 — limpar na análise agora, consertar para as próximas campanhas

- A `estudo02` fica como está e é lida com os três desfechos (seções 10 e 11).
- Os consertos se validam **sem campanha**, porque os quatro defeitos são visíveis no APK
  instrumentado. A verificação é estática e determinística e roda em horas. Dá para contar antes e
  depois (Apêndice A).
- O efeito no monitor se confere com o harness de traços e com um smoke dirigido em poucos apps
  (`aegis`, um app com BouncyCastle, um com okhttp).

### Recomendação: opção 2

1. Tudo o que medimos para mais sai pela análise.
2. O que só uma nova campanha traria é pequeno onde deu para medir, e viria misturado com variação
   aleatória.
3. A próxima campanha vale a pena quando houver outro motivo para rodar: o próximo estudo, ou as
   mudanças de spec do `NOBS`, medidas à parte.

## 13. Decisões pedidas à equipe

1. **Desfecho da `estudo02`.** Adotar o "sustentado pelas regras" (6 278) como leitura principal,
   com o bruto ao lado e a partição da seção 3 explícita? Se o texto disser "problema de segurança",
   o número é o relevante (1 572), que é só descritivo.
2. **Conclusões sobre ferramentas.** Aceitar a leitura da seção 10?
   - nenhuma comparação com o `monkey` passa em Holm no desfecho sustentado;
   - as desvantagens do `ares` e do `humanoid` desaparecem;
   - orçamento e `ape` se mantêm.

   Isso muda o que o veredito de 14/09 diz sobre `ares` e `qtesting`; o veredito comitado não foi
   alterado.
3. **Catálogo de vereditos.** Transformar os vereditos por trecho de código num artefato versionado,
   aplicado pela consolidação das próximas campanhas?
4. **Rodar de novo ou não.** Confirmar a opção 2 (não rodar a `estudo02` de novo)?
5. **Consertos do instrumentador.** Aprovar o escopo do Apêndice A (itens A1 a A4) para uma change,
   e decidir quando.
6. **Monitor "depois" com exceção** (item A5). Implementar o comportamento do AspectJ, que muda
   acusações e pede medição diferencial, ou manter e corrigir a documentação?
7. **Gerador de relatórios** (item A6). Aprovar o conserto, de preferência numa change própria do
   `rv-platform`, separada do instrumentador.
8. **Mudanças de spec para o `NOBS`** (anotação por elemento, código próprio para `null`). Levar para
   uma rodada de medição separada?

## 14. O que não está verificado

- **Os 956 e os 572.** A classificação de "objeto sem evento de criação" e de "reuso legal" foi feita
  por spec e classe. Os trechos foram lidos, mas os 6 710 maus usos do lado não-`NOBS` não foram
  reconferidos um a um.
- **O `photok`.** A divisão entre os dois métodos (47 certos, até 94) não está fechada.
- **Relatos perdidos em bibliotecas.** Os falsos negativos do gancho pulado não são mensuráveis com a
  cobertura atual.
- **App × biblioteca.** A separação usa o prefixo do pacote do app, e bibliotecas do mesmo autor com
  outro prefixo caem como biblioteca.
- **O `jca`.**
  - O motivo exato de o algoritmo ficar vazio (grupo B, 4 545) não foi reconstituído.
  - Os grupos C e `SecureRandom` foram lidos na spec e nos trechos principais, não um a um.
  - Não foi medido como o ruído do `jca` se distribui entre as ferramentas.
- **O CogniCrypt.** Não conferimos se o código lido e a versão 5.0.1 são idênticos nos trechos
  citados.
- **O `jca` no modelo.** O modelo com a contagem limpa foi refeito só para a `estudo02`. Como o `jca`
  está fora de uso, não foi feito para o artigo.

O veredito de 14/09 precisa de leitura com ressalva em dois pontos. O veredito comitado não foi
alterado.
- **Seção 4:** atribui o salto de linhas de `TrustManagerFactory`, `KeyManagerFactory` e
  `SecureRandom` à verbosidade do conjunto de specs. Para essas três specs, três em cada quatro linhas
  são o disparo duplo.
- **Conclusão sobre `ares` e `qtesting` abaixo do `monkey`:** vale para a contagem bruta. Na contagem
  sustentada, a do `ares` desaparece e a do `qtesting` não passa em Holm (seção 10).

---

## Apêndice A — Escopo proposto para as changes (não criadas)

Este apêndice descreve o que uma change OpenSpec conteria. Nenhuma change foi aberta. Quando for
aprovada, ela segue o fluxo OpenSpec do projeto. Os itens A1 a A5 são do instrumentador DEX
(`rvsec/rvsec-android/rvsec-instrumentation-dexlib2/`). O A6 é do `rv-platform` e, por ser de outro
módulo e não mudar nenhuma acusação, deveria ser uma change separada.

Princípio comum a todos: **cada conserto vem com uma contagem antes e depois**, feita sobre os 163
APKs instrumentados. Assim, o efeito de cada um é conhecido antes de qualquer campanha.

### A1. Checar a aridade de `args(...)` no casamento de eventos (disparo duplo)

- **Problema.** Um `args(...)` sem tipo casa com qualquer chamada, qualquer que seja o número de
  argumentos. O wrapper agrupa por chamada e dispara todos os eventos que casaram. Resultado:
  `getInstance(String)` dispara também o evento de dois argumentos.
- **Onde.** `pointcut-engine/.../PointcutMatcher.java:268-271` (aceita sem checar);
  `WrapperEmitter.java:301-313` (hoje só conta, em `advicesExcludedByArity`).
- **Evidência.** Confirmado no bytecode de dois apps da campanha. 35 694 linhas e 654 maus usos só
  disso. O contador aponta 10 pares incompatíveis em 164 das 170 linhas por APK.
- **Conserto.** Quando a cláusula `args` tem posições fixas, exigir que o número de argumentos da
  chamada seja igual. Com `..` no fim, exigir que seja pelo menos igual. A especificação do
  instrumentador já registra esse conserto como trabalho futuro.
- **Cuidado.** Os 25 eventos "depois" que declaram parâmetros **sem** cláusula `args` não podem ser
  afetados; a especificação os lista um a um.
- **Verificação.**
  - O contador de incompatíveis vai a 0.
  - Os wrappers de `getInstance(String)` deixam de chamar `g2`.
  - A contagem de eventos por wrapper muda **só** nesses pares.
  - O harness de traços mostra "sequência inválida" sumindo em `TrustManagerFactory`,
    `KeyManagerFactory` e `SecureRandom`, e nada mais mudando.
- **Muda acusações?** Sim: remove artefatos. Nas próximas campanhas, a comparação com a `estudo02`
  precisa descontar isso.

### A2. Métodos herdados em subtipos do sistema (`getEncoded`) e contador de descarte

- **Problema.** Quando a chamada é feita sobre um tipo do sistema que herda o método sem redeclará-lo
  (`SecretKey.getEncoded()`), a busca por métodos declarados volta vazia, e o wrapper é descartado
  sem aviso.
- **Onde.** `WrapperEmitter.expandCallTarget` (`:437-445`) consulta `AndroidClassIndex.methods`
  (`:115-126`), que só devolve métodos declarados. O descarte silencioso está em
  `WrapperEmitter.java:291`. Os apelidos para subtipos só existem para classes do próprio APK
  (`InheritanceResolver.java:79-96`).
- **Evidência.** Varredura dos 163 APKs: com dono `Key`, 2 847 chamadas, todas tecidas; com dono
  subtipo do sistema, 1 559 chamadas e nenhuma tecida, em 117 apps.
- **Conserto.**
  1. Resolver o método subindo a hierarquia de tipos do sistema.
  2. Transformar o descarte silencioso num contador publicado junto dos outros, para que qualquer
     descarte futuro apareça.
- **Verificação.**
  - As chamadas sobre subtipos sem monitor vão de 1 559 a 0.
  - O novo contador de descarte é 0 no corpus, ou lista o que resta.
- **Muda acusações?** Sim, só para menos: remove "não observados" falsos. Efeito esperado pequeno (47
  a 94 maus usos na `estudo02`).

### A3. Gancho inserido antes de uma chamada que é destino de desvio

- **Problema.** O código do monitor é inserido antes da chamada, mas o rótulo de destino dos desvios
  continua na instrução original. Quem chega pelo desvio pula o monitor.
- **Onde.** `dex-mutator/.../InstructionInjector.java:80-87` (`insertBefore`) e `:457-463`
  (`insertAll`). O mesmo comportamento é usado **de propósito** pela guarda `if(...)`
  (`InstructionInjector.java:167-180`).
- **Evidência.** Bytecode do `aegis` (`CryptoUtils.createCipher`). No corpus: 424 de 7 838 ganchos,
  em 39 apps e 94 trechos. Na campanha: 13 maus usos falsos e relatos perdidos no `aegis`.
- **Conserto.** Na inserção "antes", mover os rótulos que apontam para a chamada, e as entradas de
  tratamento de exceção que começam nela, para a primeira instrução inserida.
- **Cuidado.** A guarda `if(...)` depende do comportamento atual e precisa continuar funcionando;
  hoje não há caso de teste com desvio.
- **Verificação.**
  - A varredura `experimento-estudo02/scripts/branch_target_hooks.py` vai de 424 a 0.
  - Os testes do injetor ganham casos com `if`, `goto` e `switch` apontando para a chamada, e com
    guarda `if(...)`.
  - A tabela de linhas deixa de atribuir o evento à linha anterior.
- **Muda acusações?** Sim, nos dois sentidos: devolve relatos que se perdiam e remove sequências
  falsas.

### A4. Tipo aninhado no resolvedor de nomes

- **Problema.** `KeyStore.ProtectionParameter`, importado pelo nome curto, é resolvido como pacote
  (`java/security/KeyStore/ProtectionParameter`) e não como classe interna
  (`KeyStore$ProtectionParameter`). Os eventos `getEntry`/`setEntry` nunca casam.
- **Onde.** `TypeResolver.java:87-103` e `resolveFqn` (`:110-117`).
- **Conserto.** Tentar a forma de classe interna quando o prefixo resolve para uma classe conhecida.
- **Verificação.** Os eventos `getEntry`/`setEntry` passam a ser tecidos no `networksurvey` e nos
  outros apps que usam essas chamadas; a contagem vai de 0 a n.
- **Muda acusações?** Na `estudo02`, não, porque não houve acusação de `KeyStore`. Em campanhas
  futuras, pode passar a registrar sequências com `setEntry`.

### A5. Monitor "depois" quando a chamada lança exceção (decisão, não conserto automático)

- **Problema.** No instrumentador DEX, o monitor "depois" não roda se a chamada lança exceção; no
  AspectJ roda. O comentário de `AfterEmitter.java` promete o comportamento do AspectJ.
- **Evidência.** `docs/20260827_divergencia_after_dexlib2_ajc.md`: 58 dos 202 eventos do
  `jca_android`.
- **Opções.**
  - **(a) Implementar o comportamento do AspectJ.** O mecanismo de `try/catch` já existe e é usado em
    outro tipo de evento.
  - **(b) Manter e corrigir a documentação.**
- **Por que é decisão.** A opção (a) muda o que é acusado, justamente nas chamadas que a API rejeita
  com exceção. Exigiria uma medição diferencial própria antes de qualquer campanha.

### A6. Gerador de relatórios que estoura a memória (`rv-platform`)

- **Problema.** No fim da `estudo02`, **os dez containers morreram na exportação final por falta de
  memória** (`exit=137`, OOMKilled), dentro do primeiro arquivo, `coverage.csv`. O `coverage.csv`
  ficou truncado. `errors.csv`, `summary.csv`, `app_events.csv`, `results.json` e `performance.csv`
  não foram escritos. As tabelas só existem porque foram regeneradas offline.
- **Onde e por quê.** `modules/rv-platform/src/rv_platform/components/result_processor.py`.
  - `execute()` (`:239-244`) faz **seis passadas sobre a campanha inteira**, uma por arquivo.
  - Na primeira, `_write_task_coverage_data` reconstrói o repositório de cada tarefa a partir do
    logcat e o **guarda na própria tarefa** (`task.repository = reconstructed`, `:525`).
  - `_resolve_static_data` guarda o modelo de análise estática **por tarefa**
    (`task.static_data = static_data`, `:361`), e não por app. O mesmo modelo é reinterpretado para
    cada uma das dezenas de execuções do mesmo app, e nada é liberado.
  - Com cerca de 1 600 execuções por container, a memória cresce até o limite: o kill veio entre 179
    e 726 tarefas, com 2,8 a 4,7 milhões de métodos carregados.
  - Liberar tudo só no fim não resolve, porque a morte acontece na primeira passada.
- **O que já está provado.** `experimento-estudo02/scripts/regenerate_tables.py` resolve o problema
  **sem mudar nenhuma coluna**:
  - usa os próprios métodos de escrita do `result_processor`;
  - inverte o laço: para cada tarefa, roda todos os escritores e então solta repositório e modelo;
  - lê o modelo estático uma vez por app;
  - rodou em 5 a 11 minutos por container, com no máximo 365 MB de memória residente;
  - a equivalência foi conferida contra o índice e contra o `coverage.csv` parcial da corrida ao vivo.
- **Conserto proposto.** Levar essa forma de laço para o `ResultProcessorComponent`:
  1. abrir os seis arquivos no início e escrever os cabeçalhos;
  2. para cada tarefa (ordenadas por app), obter o repositório e rodar todos os escritores;
  3. descartar `task.repository` e `task.static_data` depois de cada tarefa;
  4. manter um cache de **um** modelo estático, trocado quando muda o app.

  Cabeçalhos e formato ficam idênticos.
- **O mesmo acúmulo acontece durante a corrida, não só na exportação** (conferido no código em
  15/09):
  - `StaticAnalysisComponent` grava o modelo estático na tarefa (`static_analysis.py:137`).
  - `CoverageComponent` grava o repositório na tarefa (`coverage.py:61,149,307`).
  - Ao terminar, a tarefa, com os dois, é guardada viva no dicionário do `TaskStorage`
    (`platform.py:430` → `task_storage.py:457`).
  - Nenhum ponto do `rv-platform` solta esses campos. Então, numa sessão longa, a memória cresce a
    cada execução concluída, antes mesmo da exportação.
  - O conserto precisa soltar `repository` e `static_data` **quando a tarefa termina**, e não só no
    gerador. O gerador, por sua vez, reconstrói a partir do logcat.
  - **Não verificado:** se as quedas de container durante a corrida da `estudo02` foram causadas por
    isso. Os registros da campanha anotam o estouro de memória na exportação, mas não a causa das
    quedas durante a corrida.
- **A conferir no conserto.** Se algum escritor depende de ter visto todas as tarefas antes de
  escrever. O `results.json` é hierárquico e pode precisar ser escrito em fluxo.
- **Verificação.**
  1. Regenerar um container da `estudo02` com o componente consertado e comparar byte a byte com
     `data/results/estudo02_regen/estudo02_NN/`, com `PYTHONHASHSEED=0`. A ordem das linhas de
     `coverage.csv` dentro do mesmo segundo depende da semente de hash.
  2. Um teste de teto de memória com centenas de tarefas sintéticas do mesmo app.
- **Muda acusações?** Não. Muda só a memória e a ordem de trabalho. É um reparo puro e pode seguir
  independente de todos os outros itens.

## Apêndice B — Onde está cada número

| assunto | arquivo |
|---|---|
| Reanálise completa, com `arquivo:linha` de cada achado | `experimento-estudo02/docs/20260915_reanalise_acusacoes.md` |
| Partição dos 27 068 maus usos | `adjudicacao_nobs/reanalise_20260915/full_partition_keys.csv` (coluna `status`) |
| Vereditos por trecho `NOBS` | `adjudicacao_nobs/reanalise_20260915/my_verdicts_all.csv` |
| Vereditos não-`NOBS` | `adjudicacao_nobs/reanalise_20260915/readers/r7_table.md` |
| O que cada código `NOBS` lê e quem o produz | `adjudicacao_nobs/reanalise_20260915/readers/specsheet.md` |
| Gancho pulado por desvio | `adjudicacao_nobs/reanalise_20260915/branch_target_hooks*.csv`, script em `experimento-estudo02/scripts/branch_target_hooks.py` |
| `jca` × `jca_android` por spec | `experimento-estudo02/docs/20260914_specs_jca_vs_android.md` |
| Acusações publicadas do artigo | `ase-journal/dataset/results/errors.csv` (somente leitura) |
| Specs | `rvsec/rvsec/rvsec-mop/src/main/resources/{jca,jca_android}/` |
| Regras CrySL fixadas | `rvsec-cognicrypt/CrySL-Rules/` |
| Relatórios do CogniCrypt sobre o corpus | `rvsec-dataset/cognicrypt/*_CryptoAnalysis-Report.csv` (os dois `cognicrypt_{summary,metrics}.csv` da mesma pasta são resumo da execução, não achados) |
| Números das seções 7 e 8 (`jca` por mecanismo, valores do `jca_android`, CogniCrypt) | `experimento-estudo02/docs/20260915_jca_e_cognicrypt.md`, gerado por `scripts/jca_e_cognicrypt.py` |
| Divergência do monitor "depois" | `docs/20260827_divergencia_after_dexlib2_ajc.md` |
| Regenerador de tabelas | `experimento-estudo02/scripts/regenerate_tables.py` |
| Modelo com a contagem limpa | `experimento-estudo02/docs/20260915_modelo_rq1_desfechos.md`, `20260915_modelo_rq1_sustentado.txt`; scripts `desfechos_sustentados.py` e `rq1_estudo02.py --outcome` |
| Arquivos de acusação limpos e contagens por execução | `experimento-estudo02/docs/desfechos_sustentados.zip` (contém `errors_sustentado.csv`, `errors_relevante.csv` e `per_task_desfechos.csv`; o script os regenera em `data/results/estudo02_consolidado/`) |
| Dados da campanha | `data/results/estudo02_consolidado/` |
