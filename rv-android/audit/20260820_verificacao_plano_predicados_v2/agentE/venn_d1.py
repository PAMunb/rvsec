#!/usr/bin/env python3
"""Agente E — auditoria 2a passada da alegacao D1 (venn RV x CC).

TAREFA 1: linha-base do venn publicado (rq1_rv_cc.py:45-143, pandas puro).
TAREFA 2/3: efeito das allow-lists api30 sob varias leituras.

Traducoes fieis das classes Java (fontes citados):
- CipherTransformationUtil.{alg,mode,pad,isValid}
  rvsec/rvsec-core/src/main/java/br/unb/cic/mop/jca/util/CipherTransformationUtil.java
- Api30CipherTransformationUtil.isValid
  .../Api30CipherTransformationUtil.java
- ConscryptAliasTable.{canonical,matches}
  .../ConscryptAliasTable.java  (linhas carregadas de data/jca_android/alias_table.csv,
  que ConscryptAliasTableTest afirma igual linha a linha a ROWS)
Allow-lists api30 lidas dos .mop de rvsec/rvsec-mop/src/main/resources/jca_android/.
"""
import re
import pandas as pd

DATASET = '/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal/dataset'
ALIAS_CSV = '/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/data/jca_android/alias_table.csv'

# ---------------------------------------------------------------- Java ports
def alg(t):   # CipherTransformationUtil.alg
    return t.split('/')[0] if '/' in t else t

def mode(t):  # CipherTransformationUtil.mode
    return t.split('/')[1] if '/' in t else ''

def pad(t):   # CipherTransformationUtil.pad
    arr = t.split('/')
    return arr[2] if len(arr) == 3 else ''

def jca_isvalid(t):
    """CipherTransformationUtil.isValid (jca congelado) — fiel, inclusive case."""
    modes = ["CBC", "CCM", "GCM", "PCBC", "CTR", "CTS", "CFB", "OFB"]
    padding = {
        "CBC": ["PKCS5PADDING", "ISO10126PADDING", "PKCS5PADDING"],
        "PCBC": ["PKCS5PADDING", "ISO10126PADDING", "PKCS5PADDING"],
        "GCM": ["", "NOPADDING"], "CTR": ["", "NOPADDING"], "CTS": ["", "NOPADDING"],
        "CFB": ["", "NOPADDING"], "OFB": ["", "NOPADDING"], "CCM": ["", "NOPADDING"],
    }
    if alg(t) == "AES":
        if mode(t) in modes:
            return pad(t).upper() in padding[mode(t)]
        return False   # Java: cai para o return false final
    elif alg(t) == "RSA":
        paddings = ["NoPadding", "PKCS1Padding", "OAEPWithMD5AndMGF1Padding",
                    "OAEPWithSHA-224AndMGF1Padding", "OAEPWithSHA-256AndMGF1Padding",
                    "OAEPWithSHA-384AndMGF1Padding", "OAEPWithSHA-512AndMGF1Padding"]
        rsa_ecb = [p.upper() for p in paddings]
        return (mode(t) == "" and pad(t).upper() == "") or \
               (mode(t) == "ECB" and pad(t).upper() in rsa_ecb)
    return False

def fold(s):
    return '' if s is None else s.strip().upper()

# Api30CipherTransformationUtil — listas transcritas do Java
A30_ALGORITHMS = ["ChaCha20", "AES_128", "ARC4", "RSA", "DESede", "AES", "BLOWFISH", "AES_256"]
A30_AES_MODES = ["CFB", "GCM", "OFB", "CTS", "CTR", "ECB", "CBC"]
A30_RSA_MODES = ["", "ECB"]
A30_CBC_PADDINGS = ["PKCS5Padding", "PKCS7Padding", "ISO10126Padding"]
A30_NO_PADDING = ["NoPadding"]
A30_RSA_PADDINGS = ["OAEPwithSHA-512andMGF1Padding", "OAEPwithSHA-224andMGF1Padding",
                    "PKCS1Padding", "OAEPwithSHA-256andMGF1Padding",
                    "OAEPwithSHA-1andMGF1Padding", "OAEPPadding",
                    "OAEPwithSHA-384andMGF1Padding", "NoPadding"]
A30_STREAM_MODES = ["OFB", "CTR", "CFB"]

def _contains(entries, value):
    return any(fold(e) == fold(value) for e in entries)

def api30_isvalid(t):
    """Api30CipherTransformationUtil.isValid — fiel (fold de case, nada mais)."""
    if t is None:
        return False
    a, m, p = alg(t), mode(t), pad(t)
    if not _contains(A30_ALGORITHMS, a):
        return False
    if fold(a) == "RSA":
        return _contains(A30_RSA_MODES, m) and _contains(A30_RSA_PADDINGS, p)
    if fold(a) == "AES" and not _contains(A30_AES_MODES, m):
        return False
    aes_family = fold(a) in ("AES", "DESEDE")
    if aes_family and fold(m) == "CBC":
        return _contains(A30_CBC_PADDINGS, p)
    if aes_family and _contains(A30_STREAM_MODES, m):
        return _contains(A30_NO_PADDING, p)
    if fold(a) == "AES" and fold(m) == "GCM":
        return _contains(A30_NO_PADDING, p)
    return True

# ConscryptAliasTable a partir do CSV auditavel
_alias = pd.read_csv(ALIAS_CSV, keep_default_na=False)
BY_SERVICE = {}
for _, r in _alias.iterrows():
    BY_SERVICE.setdefault(fold(r['service']), {})[fold(r['alias'])] = r['canonical']

def canonical(service, observed):
    if observed is None:
        return None
    aliases = BY_SERVICE.get(fold(service))
    if aliases is None:
        return observed
    return aliases.get(fold(observed), observed)

def matches(service, observed, allow_list, use_alias=True):
    """ConscryptAliasTable.matches; use_alias=False = so o fold direto (allow-list 'literal')."""
    if observed is None or allow_list is None:
        return False
    direct = fold(observed)
    resolved = fold(canonical(service, observed)) if use_alias else direct
    return any(fold(e) in (direct, resolved) for e in allow_list)

# Allow-lists api30, transcritas dos .mop de jca_android (fonte de cada uma citada)
MD_LIST = ["MD5", "SHA-224", "SHA-256", "SHA-1", "SHA-512", "SHA-384"]        # MessageDigestSpec.mop:28
SIG_LIST = ["NONEwithRSA", "SHA1withDSA", "SHA224withECDSA", "MD5withRSA",    # SignatureSpec.mop:35-39
            "SHA256withDSA", "SHA384withRSA/PSS", "DSAwithSHA1", "SHA384withRSA",
            "SHA512withRSA/PSS", "SHA1withRSA/PSS", "SHA512withRSA", "SHA1withRSA",
            "NONEwithDSA", "SHA256withRSA/PSS", "SHA224withRSA/PSS", "SHA256withRSA",
            "DSA", "SHA224withRSA", "SHA224withDSA", "DSS",
            "SHA1withECDSA", "SHA256withECDSA", "SHA384withECDSA", "SHA512withECDSA"]
MAC_LIST = ["PBEwithHmacSHA256", "PBEwithHmacSHA1", "HmacSHA224", "HmacSHA256",  # MacSpec.mop:24-26
            "HmacMD5", "HmacSHA512", "PBEwithHmacSHA512", "HmacSHA384",
            "PBEwithHmacSHA384", "PBEwithHmacSHA224", "PBEwithHmacSHA", "HmacSHA1"]
TMF_LIST = ["PKIX"]                                                            # TrustManagerFactorySpec.mop:35
SSL_LIST = ["Default", "TLSv1.2", "TLSv1.1", "SSL", "TLSv1", "TLS", "TLSv1.3"] # SSLContextSpec.mop:35-36
KS_LIST = ["AndroidKeyStore", "PKCS12", "BKS", "BouncyCastle", "AndroidCAStore"]  # KeyStoreSpec.mop:35

SPEC_SERVICE = {  # spec -> (service p/ ConscryptAliasTable, allow-list api30)
    'MessageDigestSpec': ('MessageDigest', MD_LIST),
    'SignatureSpec': ('Signature', SIG_LIST),
    'MacSpec': ('Mac', MAC_LIST),
    'TrustManagerFactorySpec': ('TrustManagerFactory', TMF_LIST),
    'SSLContextSpec': ('SSLContext', SSL_LIST),
    'KeyStoreSpec': ('KeyStore', KS_LIST),
}

# ------------------------------------------------------- TAREFA 1: linha-base
cc = pd.read_csv(f'{DATASET}/cc.csv', sep=';', keep_default_na=False)
mapping = pd.read_csv(f'{DATASET}/cc_rv_mapping.csv', keep_default_na=False)
rv_raw = pd.read_csv(f'{DATASET}/results/errors.csv', keep_default_na=False)

cc['method_name'] = cc['Method'].str.extract(r'(<init>|<clinit>|[A-Za-z_$][\w$]*)(?=\()')
mapping['RVSecRule'] = mapping['RVSecRule'].replace(
    {'None': pd.NA, 'none': pd.NA, 'nan': pd.NA, 'NaN': pd.NA, '': pd.NA})
cc['apk_clean'] = cc['apk'].str.replace(r'_CryptoAnalysis-Report$', '', regex=True) + '.apk'
cc = cc.merge(mapping, left_on='ViolatedRule', right_on='CogniCryptRule')
cc['RVSecRule'] = cc['RVSecRule'].replace(
    {'None': pd.NA, 'none': pd.NA, 'nan': pd.NA, 'NaN': pd.NA, '': pd.NA})
cc = cc[cc['RVSecRule'].notna()]
cc = (cc[['apk_clean', 'Class', 'method_name', 'RVSecRule']]
      .rename(columns={'apk_clean': 'apk', 'Class': 'class',
                       'method_name': 'method', 'RVSecRule': 'spec'})
      .drop_duplicates(subset=['apk', 'class', 'method', 'spec'])
      .reset_index(drop=True))

KEY = ['apk', 'class', 'method', 'spec']
cc_keys = set(map(tuple, cc[KEY].values))

def venn(rv_events):
    """rv_events: DataFrame com colunas KEY (eventos); deduplica e cruza com cc."""
    rv_keys = set(map(tuple, rv_events[KEY].drop_duplicates().values))
    both = len(rv_keys & cc_keys)
    return dict(RV=len(rv_keys), CC=len(cc_keys), both=both,
                only_RV=len(rv_keys) - both, only_CC=len(cc_keys) - both)

base = venn(rv_raw)
print('TAREFA 1 — linha-base :', base)
assert base == dict(RV=454, CC=423, both=112, only_RV=342, only_CC=311), base

# ------------------------------------------- classificacao evento a evento
ev = rv_raw.copy()
um = ev['unique_msg'].str.split(':::', expand=True)
ev['etype'] = um[3]
ev['found'] = ev['message'].str.extract(r'but found (.*)\.$')[0].fillna('')

def silenced(row, use_alias, cats):
    """O evento seria silenciado pela allow-list api30 correspondente?"""
    if row.etype not in cats:
        return False
    spec, val = row.spec, row.found
    if val == '':               # valor observado vazio: nao ha o que admitir
        return False
    if spec == 'CipherSpec':
        return api30_isvalid(val)
    if spec in SPEC_SERVICE:
        service, lst = SPEC_SERVICE[spec]
        return matches(service, val, lst, use_alias=use_alias)
    return False

UA = ('UnsafeAlgorithm',)
ALLCAT = ('UnsafeAlgorithm', 'UnsafeProtocol', 'InvalidKeyStoreType')

for name, use_alias, cats in [('literal(fold), so UnsafeAlgorithm', False, UA),
                              ('alias, so UnsafeAlgorithm', True, UA),
                              ('alias, UA+UP+IKST', True, ALLCAT)]:
    col = f's_{name}'
    ev[col] = ev.apply(lambda r: silenced(r, use_alias, cats), axis=1)
    n = int(ev[col].sum())
    tot = int(ev['etype'].isin(cats).sum())
    print(f'  silenciados [{name}]: {n} de {tot} eventos')

# sanity: caso-sensivel exato (modelagem da auditoria, "literal") p/ conferir 5.467
lit_cs = ev[(ev['etype'] == 'UnsafeAlgorithm') &
            (ev.apply(lambda r: (r.spec in SPEC_SERVICE and r.found != '' and
                                 r.found in SPEC_SERVICE[r.spec][1]) or
                                (r.spec == 'CipherSpec' and api30_isvalid(r.found) and False),
                      axis=1))]
print(f'  silenciados [literal case-sensitive, so UA]: {len(lit_cs)} (auditoria: 5.467)')

# ------------------------------------------------------- TAREFA 2: so eventos
s_lit = ev[~ev['s_literal(fold), so UnsafeAlgorithm']]
s_ali = ev[~ev['s_alias, so UnsafeAlgorithm']]
print('\nTAREFA 2 — remove so os eventos silenciados (chave sobrevive se restar 1 evento):')
print('  literal(fold):', venn(s_lit))
print('  alias        :', venn(s_ali))

# --------------------------------------- TAREFA 3a: descarte da chave inteira
def venn_dropkeys(silcol, group_cols):
    bad = set(map(tuple, ev.loc[ev[silcol], group_cols].drop_duplicates().values))
    keep = ev[~ev[group_cols].apply(tuple, axis=1).isin(bad)]
    return venn(keep), len(bad)

v3a, nk = venn_dropkeys('s_alias, so UnsafeAlgorithm', KEY)
print(f'\nTAREFA 3a — alias + descarte da chave inteira ({nk} chaves tocadas):', v3a)

# --------------------------------------- TAREFA 3c: leituras mais agressivas
v3c1, nk1 = venn_dropkeys('s_alias, so UnsafeAlgorithm', ['apk', 'spec'])
print(f'TAREFA 3c-1 — descarte por (apk,spec) [{nk1} grupos]:', v3c1)

v3c2, nk2 = venn_dropkeys('s_alias, UA+UP+IKST', KEY)
print(f'TAREFA 3c-2 — alias + UA+UnsafeProtocol+InvalidKeyStoreType, chave inteira [{nk2} chaves]:', v3c2)

v3c3, nk3 = venn_dropkeys('s_alias, UA+UP+IKST', ['apk', 'spec'])
print(f'TAREFA 3c-3 — UA+UP+IKST por (apk,spec) [{nk3} grupos]:', v3c3)

# variante: valor vazio tambem silencia (leitura "default e admitido")
ev['s_empty'] = ev.apply(lambda r: (r.etype in ALLCAT and
    (r.found == '' and (r.spec in SPEC_SERVICE or r.spec == 'CipherSpec'))) or
    silenced(r, True, ALLCAT), axis=1)
v3c4, nk4 = venn_dropkeys('s_empty', KEY)
print(f'TAREFA 3c-4 — + valor vazio silencia, chave inteira [{nk4} chaves]:', v3c4)

# ------------------------------ detalhe p/ relatorio: pares (spec,valor) e contagens
print('\nInventario UnsafeAlgorithm (spec, valor, n, literal-fold, alias):')
inv = (ev[ev.etype == 'UnsafeAlgorithm']
       .groupby(['spec', 'found']).size().reset_index(name='n'))
for _, r in inv.iterrows():
    lit = silenced(pd.Series({'etype': 'UnsafeAlgorithm', 'spec': r['spec'], 'found': r['found']}), False, UA)
    ali = silenced(pd.Series({'etype': 'UnsafeAlgorithm', 'spec': r['spec'], 'found': r['found']}), True, UA)
    print(f"  {r['spec']:24s} {r['found'][:45]:45s} {r['n']:6d}  lit={lit}  alias={ali}")
