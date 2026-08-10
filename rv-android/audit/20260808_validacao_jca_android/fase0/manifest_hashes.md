# Fase 0 — Manifesto de Proveniência (hashes, estado git, ambiente)

**Data da coleta:** 2026-08-08
**Auditoria:** validação formal das 23 especificações JavaMOP `jca_android`

## HEADs de referência

| Repositório | Caminho | Branch | HEAD | `git status --porcelain \| wc -l` |
|---|---|---|---|---|
| rvsec (monorepo) | `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec` | `modules` | `1dd1f4c5cbdcafcf1869244a9731be806102c63d` | 549 (working tree sujo) |
| MetaCrySL | `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/MetaCrySL` | `master` | `fb1ecabaf1193dd54f98e7f03e19e2203e6641dd` | 0 (limpo) |
| ase-journal | `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal` | `jss-jca` | `f693a378771ef99668c1af1340791764636a644f` | 31 |

**Regra de validade da auditoria:** todos os hashes abaixo foram calculados sobre os **bytes do working tree** na data da coleta. Como o working tree do monorepo rvsec está sujo (549 entradas no porcelain), o estado git de cada arquivo hasheado em relação ao HEAD está registrado explicitamente na coluna "Git vs HEAD". Resultado central: **os 23 `.mop` de `jca_android`, os 23 `.mop` de `jca`, as 33 `.cryptsl` de `api30` e o `errors.csv` estão todos LIMPOS em relação aos respectivos HEADs** (`git status --porcelain -- <path>` vazio para todos). A sujeira do working tree do rvsec está em outros caminhos (docs, módulos Python etc.) e não toca os artefatos auditados. Portanto, bytes do working tree = bytes do HEAD para todos os arquivos deste manifesto.

---

## 1. Specs `jca_android` (23 arquivos — objeto da auditoria)

Diretório: `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android/`
Git vs HEAD: **limpo** (porcelain vazio para o diretório inteiro). Encoding: todos os 23 são ASCII puro (`file`).

| Arquivo | SHA-256 | Tamanho (bytes) | mtime (-0300) |
|---|---|---|---|
| CipherInputStreamSpec.mop | `d71a86d8b396633bd3609fac1746b6e346e354d4760ab7d14444ecca87f84bb0` | 1769 | 2026-08-07 21:38:10 |
| CipherOutputStreamSpec.mop | `c105492951623e0b795f7a31341d340109583253f8820f14f290e66d981d9a70` | 1853 | 2026-08-07 21:38:14 |
| CipherSpec.mop | `c9deafb2acb2b2d75e55fe1c62b4f948685aa7e23142a71c5d883c8bb74d2de5` | 16836 | 2026-08-07 21:37:47 |
| DHGenParameterSpecSpec.mop | `f2f6aed6d049adc24b0a8be5c7901c5d2c163360866ae4e06c3425508f1072eb` | 1086 | 2026-08-06 18:25:51 |
| GCMParameterSpecSpec.mop | `18c84f8f64f3b5dde60ee06aee1e2cfd86e5468c32b005567f5e79f1e4355fe5` | 1676 | 2026-08-06 18:25:51 |
| HMACParameterSpecSpec.mop | `254040e78e3215708ab3855e08661413f20a34fe27b953d03121b300f608f282` | 997 | 2026-08-06 18:25:51 |
| IvParameterSpec.mop | `633237ac49e0bcc9b6bfd83284a4d4821130a204178839a08a8b538d8704fede` | 2889 | 2026-08-07 14:59:38 |
| KeyGeneratorSpec.mop | `3788c3d8d0993b838d3469dd703b8df735cb16a1f98b7531e7e14a071cb77877` | 5677 | 2026-08-07 17:03:01 |
| KeyManagerFactorySpec.mop | `a7fb68fb7bd119133b416b4e61a9d3898cfe5a03fca9a3bc7eecabff97eece8a` | 5925 | 2026-08-07 17:11:06 |
| KeyPairGeneratorSpec.mop | `9a2628406a78dd7f3983c5ed352379eb0b9ac0dc6c7379adc05c53000f5ac994` | 6414 | 2026-08-07 16:37:50 |
| KeyPairSpec.mop | `8bc496323dde905cd4dc0df0d543f2c77eb98b41951118a6379b9a575b6ffdf9` | 3214 | 2026-08-07 15:27:46 |
| KeyStoreSpec.mop | `3392a11d77305997a7e4f20559e24468386c9592355a5a0de198c85b825f8b00` | 3697 | 2026-08-07 15:28:12 |
| MacSpec.mop | `db8b0d12be1f3b0a3ea40531d9b3a358a29105d4cfed6444f2bb70c61651c922` | 11025 | 2026-08-07 19:43:38 |
| MessageDigestSpec.mop | `03ff03db45f0cfe56041c628c0ad771c1e7e134eb9a812769a178bce7bb7187c` | 4760 | 2026-08-07 15:00:12 |
| PBEKeySpecSpec.mop | `8fdcabe6300321aa1d35214c72107a5bc32be4d95995f65d9e4469d86df578c7` | 4947 | 2026-08-07 15:00:36 |
| PBEParameterSpecSpec.mop | `f088e3b7cd4fa111c0f7da4286bd4c216f1a76672a43e7c18a7b0465df7635fd` | 2742 | 2026-08-07 14:59:48 |
| RandomStringPassword.mop | `1d3cf93b98d47f0aca70801adde1b8df4ac65d86a1215b9d8e4d9be56b3e517b` | 814 | 2026-08-06 18:25:51 |
| SSLContextSpec.mop | `42760be50837ab884a8bcf57b0a5253cbe63de1545c3e5f0d62e8aaaf63a15ce` | 5620 | 2026-08-07 14:05:17 |
| SecretKeySpec.mop | `03768f3bb39fc5f2e1a230c30d6c9659d727ee72d633eb37f735d66c067b494b` | 2038 | 2026-08-07 16:38:31 |
| SecretKeySpecSpec.mop | `d1cc088aee24205bffd3cb241427469f03d388e7aacdeed753399a088eacb8ef` | 4035 | 2026-08-07 16:39:07 |
| SecureRandomSpec.mop | `9e58c92c395bdb2f3c4da88925076112cbf1aa3c5519d37e27ed79737479b7d3` | 6857 | 2026-08-07 15:00:51 |
| SignatureSpec.mop | `68dd32a67ecae1c4ed23391021acd398a2fe167bc7018dbf63907cdf58272637` | 7725 | 2026-08-07 15:28:57 |
| TrustManagerFactorySpec.mop | `a4691fd43de403e5788e05a4ce8c3060cc4158072a282dccddab27a71a337a70` | 7158 | 2026-08-07 17:11:31 |

---

## 2. Specs `jca` — conjunto CONGELADO (23 `.mop`, hasheados apenas para referência; NÃO auditados)

Diretório: `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca/`
Git vs HEAD: os 23 `.mop` estão **limpos**. Quatro arquivos são byte-idênticos aos homônimos de `jca_android`: DHGenParameterSpecSpec.mop, GCMParameterSpecSpec.mop, HMACParameterSpecSpec.mop, RandomStringPassword.mop.

| Arquivo | SHA-256 | Tamanho (bytes) | mtime (-0300) |
|---|---|---|---|
| CipherInputStreamSpec.mop | `0bfa254dd2cc3611e959a03785942c2e4b7e309c2438547a3f88414e7a2e849a` | 874 | 2026-02-24 08:51:16 |
| CipherOutputStreamSpec.mop | `f61bf1beb626d041531f85a39be79aa4cb6c61c119c2b257fa0ba70a69167eb2` | 954 | 2026-02-24 08:51:16 |
| CipherSpec.mop | `819ed113762c6c8f5cfdb8bda34233161f3f432ea200c9ea6427c095b8dda341` | 7268 | 2026-02-24 08:51:16 |
| DHGenParameterSpecSpec.mop | `f2f6aed6d049adc24b0a8be5c7901c5d2c163360866ae4e06c3425508f1072eb` | 1086 | 2026-02-24 08:51:16 |
| GCMParameterSpecSpec.mop | `18c84f8f64f3b5dde60ee06aee1e2cfd86e5468c32b005567f5e79f1e4355fe5` | 1676 | 2026-02-24 08:51:16 |
| HMACParameterSpecSpec.mop | `254040e78e3215708ab3855e08661413f20a34fe27b953d03121b300f608f282` | 997 | 2026-02-24 08:51:16 |
| IvParameterSpec.mop | `96c4a418f08793d4b8397fda3db14d2287e58446fc089c8ad507ca4435796e2e` | 2232 | 2026-02-24 08:51:16 |
| KeyGeneratorSpec.mop | `69529737fd463c67545817fcad3c3d5fa8ec164647cb427210fe07813e5552bf` | 3155 | 2026-02-24 08:51:16 |
| KeyManagerFactorySpec.mop | `28d8e7780814fdbf5ee7707bf4abb3467fdf1bd3429c81364187c1df1ff20086` | 3329 | 2026-06-02 11:02:44 |
| KeyPairGeneratorSpec.mop | `452a8ee39b685ade8499aa84bac6cd16e9144404b82aa84f01af80789c1c2177` | 4304 | 2026-02-24 08:51:16 |
| KeyPairSpec.mop | `a4cafbf2d7114c378b0ac0762a44d1514c765f4967703c47b2f4e843cebd332a` | 1492 | 2026-02-24 08:51:16 |
| KeyStoreSpec.mop | `aae11de78dbf57bc39399e816955b36425b9ea2cab09783e2bdb5f3683ebca6b` | 2867 | 2026-02-24 08:51:16 |
| MacSpec.mop | `a8c3ff8e0c1853457c587e597148adb5e5ee88156f3fe46d014a7a5abaadc79c` | 3772 | 2026-02-24 08:51:16 |
| MessageDigestSpec.mop | `5d08e921845ae1fe151d73d54de61027978b07fcecb66930f2c952542972b67e` | 4826 | 2026-02-24 08:51:16 |
| PBEKeySpecSpec.mop | `986b135c49e58b5192d489202131bc0a38e7d6dc8caa61a53bef27fd2a70cf7a` | 3738 | 2026-06-12 12:48:42 |
| PBEParameterSpecSpec.mop | `abc9a5178764b5131de19321f070d5f238b84337a974535a6f0a303fe704d309` | 2306 | 2026-06-12 12:48:45 |
| RandomStringPassword.mop | `1d3cf93b98d47f0aca70801adde1b8df4ac65d86a1215b9d8e4d9be56b3e517b` | 814 | 2026-02-24 08:51:16 |
| SSLContextSpec.mop | `c2e9b0a9f29ec5f6ad7ea52195d61bbdf514e109658d6a7949040be013df595b` | 2768 | 2026-02-24 08:51:16 |
| SecretKeySpec.mop | `c99c7fa00331cab755d55d5fe6e6a20da06889767aa0ccfca57af9bb1e0b8ba0` | 859 | 2026-02-24 08:51:16 |
| SecretKeySpecSpec.mop | `869c220e37919be50e4a11725fe56b03c573fe49f316038bda497caf3f9ec81e` | 2993 | 2026-02-24 08:51:16 |
| SecureRandomSpec.mop | `a04220da642f820c1180f1865665421b673f21e320007796efbd71adf5ac7131` | 5758 | 2026-02-24 08:51:16 |
| SignatureSpec.mop | `0b3fbe5169b9a68c7439718fc3c2a30b778da619786bb8d5d9dd4318796eb238` | 5296 | 2026-02-24 08:51:16 |
| TrustManagerFactorySpec.mop | `32aa69c1d3943d7c57f9f282d5f8504682e209efd77f50443839c6d9a24b599d` | 3372 | 2026-02-24 08:51:16 |

**Anomalia registrada (não é `.mop`):** o diretório `jca/` contém `MultiSpec_1MonitorAspect.aj` (SHA-256 `7a5a0e813a60069872cb8d6d6c0e27a421b44d936d0d2adb32a7b0a62f0bf3af`, 71578 bytes, mtime **2026-08-08 10:39:47** — hoje). É artefato **gerado** pelo pipeline JavaMOP/rv-monitor, **não rastreado e ignorado pelo git** (`!!` em `git status --ignored`). Sua presença com mtime de hoje indica que uma geração de monitores rodou sobre `jca/` na manhã da coleta. Ele não altera nenhum `.mop`, mas é exatamente o tipo de resíduo que a proibição "nunca executar JavaMOP sobre a árvore de specs" desta auditoria visa evitar.

---

## 3. Regras CrySL `api30` (33 arquivos)

Diretório: `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/MetaCrySL/generated/api30/`
Git vs HEAD (`fb1ecaba`): **limpos** (repositório inteiro limpo, porcelain = 0).

| Arquivo | SHA-256 | Tamanho (bytes) | mtime (-0300) |
|---|---|---|---|
| AlgorithmParameters.cryptsl | `af87bd95b577a7f717e0f927801f680362f00289c62e6700253e77b34bb25dec` | 1422 | 2026-08-06 18:15:20 |
| CertPathTrustManagerParameters.cryptsl | `4ac896c2cb01c8ecba03c69fd0f5fe5e9c740da99db44c46dd233250a71319a8` | 365 | 2026-08-06 18:15:20 |
| Cipher.cryptsl | `a8e7e2d2e33946c5fffddbba00235ae09bd3a5daa51627c594d09eb989f82da4` | 5969 | 2026-08-06 18:15:20 |
| CipherInputStream.cryptsl | `f291a28979d71b012b1c550f4af0c90bd2282ef4f49b7d574e37319bc6d52122` | 597 | 2026-08-06 18:15:20 |
| CipherOutputStream.cryptsl | `9a57e52bf6bb870a1812ffd0ca04c7696212813e1d85a481fcc985f1fddb45b2` | 632 | 2026-08-06 18:15:20 |
| DHGenParameterSpec.cryptsl | `b5177f436864a60288a57fcab92baa58fe56544fcf1933c18ee0f32cc7335e98` | 254 | 2026-08-06 18:15:20 |
| DSAGenParameterSpec.cryptsl | `c10ae99c5537e5118acb54b4e20500b218e100a85e1d7787461857fc7b5e5b31` | 375 | 2026-08-06 18:15:20 |
| DigestInputStream.cryptsl | `4e1b326d180cbee4b9bb2ac72188c1c08ee6212caba1c6e53d94d7014575ddae` | 532 | 2026-08-06 18:15:20 |
| DigestOutputStream.cryptsl | `e47724bf7d32d17089c283f3b38e1930de655cd2f625c2bad62d5c451e11003c` | 571 | 2026-08-06 18:15:20 |
| GCMParameterSpec.cryptsl | `26474144cee2ab7f7a71946dbb7330960c11cb8edf0ff446536a672a59534dd8` | 499 | 2026-08-06 18:15:20 |
| HMACParameterSpec.cryptsl | `61d064317962f3a5fd801b989f311e4b550366518777534da21d8e05b714f14e` | 229 | 2026-08-06 18:15:20 |
| IvParameterSpec.cryptsl | `833c3e231f334396789727c41c43e81a593df81b2fa51fba760e7031ee81a1b6` | 382 | 2026-08-06 18:15:20 |
| Key.cryptsl | `15fc65627db853dcbb30cf84981864d52c5879d711d940184db47c7741b11ab3` | 254 | 2026-08-06 18:15:20 |
| KeyGenerator.cryptsl | `30779a3a516e6d0dd6b269a5528ef90ccf06564a5e08d3222f7edd6126de9ed3` | 978 | 2026-08-06 18:15:20 |
| KeyManagerFactory.cryptsl | `ebd1639ecc20d65934057e82e5dcdb8e256b206da00b123c86a4978f8f0afb4a` | 824 | 2026-08-06 18:15:20 |
| KeyPair.cryptsl | `e204371fd1f4ed8f2036c87730b74f83e5f872bd7ea65982e82caeb0e29b70dd` | 659 | 2026-08-06 18:15:20 |
| KeyPairGenerator.cryptsl | `c820d2d0394bedc7265436edeec0be7612b784baab30dc53836510978f5e66d0` | 1174 | 2026-08-06 18:15:20 |
| KeyStore.cryptsl | `083b171f5aea1e203d8136091ebf2a01172f9dca06d8ecd9e6bd39cbf432cd69` | 1998 | 2026-08-06 18:15:20 |
| KeyStoreBuilderParameters.cryptsl | `308db6ecd20adc06233a6b8a31df4aaf49deccf475116cb29140843533e9297d` | 268 | 2026-08-06 18:15:20 |
| Mac.cryptsl | `17245e0c95a67ab3ceb475a22cc7ecd64040969e6384520e4b487813cb3c03a1` | 1552 | 2026-08-06 18:15:20 |
| MessageDigest.cryptsl | `6bc3d2be90a449cb7ace2559bdbea38d6911638d2ffcace7c01d2537ee98d587` | 1116 | 2026-08-06 18:15:20 |
| PBEKeySpec.cryptsl | `05f05202b9c5c198c2144a9bdadeafa3e3b66878a8b21ed959b975fbc2735da1` | 747 | 2026-08-06 18:15:20 |
| PBEParameterSpec.cryptsl | `a6b7d2b18804502d9f70f54693ba6d6a245549457c1c0404726f38db48c8c827` | 546 | 2026-08-06 18:15:20 |
| PKIXBuilderParameters.cryptsl | `0d97a2ea9a9c401ea7e93d2108d6a8cb600f2b08757750739a64fe89b1a6640c` | 534 | 2026-08-06 18:15:20 |
| PKIXParameters.cryptsl | `a473727541355042b29483784f24ce6234ba20f055c04297a8d21159a64c692e` | 426 | 2026-08-06 18:15:20 |
| RSAKeyGenParameterSpec.cryptsl | `ba93ab02de6002a1b272ae5ef76e8513d306ff170bc392787b748729de53a020` | 411 | 2026-08-06 18:15:20 |
| SSLContext.cryptsl | `610bbcdb4a71ffcac8a41a9ca0ff44ac4385f8b3cf63c56a5affdca9521df940` | 980 | 2026-08-06 18:15:20 |
| SecretKey.cryptsl | `ed4677b1e365920b0a1ec5fc03b03fbc4f208321b5904e95f8cad4d3fcee6b88` | 366 | 2026-08-06 18:15:20 |
| SecretKeyFactory.cryptsl | `5a7e98ce55abd9f5740419b5f84101526c1f69447683bf58af30d073a4ab04e5` | 1866 | 2026-08-06 18:15:20 |
| SecretKeySpec.cryptsl | `ee7edaf9024c280ee1d6a037a8453540db8ab185630a956b830bfc4c8ead2538` | 569 | 2026-08-06 18:15:20 |
| SecureRandom.cryptsl | `69c55557c0a430dc37d35c64c7bacfd68a383dba4d3c1fc00033fe60c6886c02` | 1033 | 2026-08-06 18:15:20 |
| Signature.cryptsl | `ce3b0317f52a657b5c90c304112da75edf1eaf1276017758c56c0ae2fc814230` | 1780 | 2026-08-06 18:15:20 |
| TrustManagerFactory.cryptsl | `ae2a9d8f3fae3b782e81124846fc8b7943f9aa561764f9f366a685addbf160e6` | 748 | 2026-08-06 18:15:20 |

---

## 4. errors.csv (oráculo do dataset)

| Arquivo | SHA-256 | Tamanho (bytes) | mtime (-0300) | Git vs HEAD |
|---|---|---|---|---|
| `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal/dataset/results/errors.csv` | `78023defec078353bbd1f64331edb7992a2c34e29570e6ceb064fb57f37dea69` | 26323122 | 2026-07-31 14:11:06 | **limpo** (repo ase-journal, HEAD `f693a378`, branch `jss-jca`) |

---

## 5. Ambiente

| Item | Valor |
|---|---|
| SO | Linux canario 7.0.0-28-generic #28-Ubuntu SMP PREEMPT_DYNAMIC x86_64 |
| Java | OpenJDK 25.0.3 (Temurin-25.0.3+9, LTS) |
| Maven | Apache Maven 3.9.9 (via sdkman; roda sobre o Java 25.0.3) |
| Memória total | 123 GiB |
| CPUs (nproc) | 64 |

Nota: o `pom.xml` raiz do reactor rvsec fixa `java.version=21` para compilação; o JDK default da máquina é 25.0.3. Registrado por transparência — nenhuma compilação foi executada nesta fase.
