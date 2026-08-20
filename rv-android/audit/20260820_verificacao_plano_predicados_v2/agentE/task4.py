#!/usr/bin/env python3
"""Tarefa 4 + diagnostico do off-by-one (299 vs 300)."""
import sys
sys.path.insert(0, '/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/2bc22646-6f82-4e15-ab12-8258ae5e3a7d/scratchpad/agentE')
import pandas as pd
from venn_d1 import ev, venn, cc_keys, KEY, venn_dropkeys, SPEC_SERVICE

# ---- diagnostico off-by-one: chaves por (spec, found) silenciado
sil = ev[ev['s_alias, so UnsafeAlgorithm']]
print('chaves distintas tocadas por (spec, found) silenciado:')
print(sil.groupby(['spec','found'])[KEY].apply(lambda d: d.drop_duplicates().shape[0]))
keys_sil = sil[KEY].drop_duplicates()
print('total chaves tocadas:', len(keys_sil))
kb = set(map(tuple, keys_sil.values))
print('  das quais em both:', len(kb & cc_keys))

# MacSpec: quantas chaves os 31 UA vazios ocupam? e sao only-RV?
mac = ev[(ev.spec=='MacSpec') & (ev.etype=='UnsafeAlgorithm')]
mk = mac[KEY].drop_duplicates()
print('\nMacSpec UA vazios: eventos', len(mac), 'chaves', len(mk),
      'em cc?', [tuple(r) in cc_keys for r in mk.values])
# hipotese: se essas chaves cairem tambem, o venn vira...
extra = set(map(tuple, mk.values))
bad = kb | extra
keep = ev[~ev[KEY].apply(tuple, axis=1).isin(bad)]
print('venn com MacSpec-vazio tambem descartado:', venn(keep))

# ---- TAREFA 4: atribuicao aos orfaos ------------------------------------
# Orfaos do jca congelado (recomputados dos .mop, 18 em 10 specs):
# IvParameterSpec{c3,c4} KeyPairGeneratorSpec{initError} MessageDigestSpec{reset}
# PBEKeySpecSpec{err1,err2,err3,f1,f2} PBEParameterSpecSpec{c3}
# SSLContextSpec{unsafe_protocol} SecretKeySpecSpec{c3,c4}
# SecureRandomSpec{c3,g4,setSeed3} SignatureSpec{g3} TrustManagerFactorySpec{g3}
ORPHAN_SPECS = ['IvParameterSpec','KeyPairGeneratorSpec','MessageDigestSpec',
                'PBEKeySpecSpec','PBEParameterSpecSpec','SSLContextSpec',
                'SecretKeySpecSpec','SecureRandomSpec','SignatureSpec',
                'TrustManagerFactorySpec']
in_orph = ev[ev.spec.isin(ORPHAN_SPECS)]
print('\n[T4] linhas de errors.csv em specs portadoras de orfaos:', len(in_orph),
      f'({len(in_orph)/len(ev)*100:.1f}% de {len(ev)})')
isomc = ev[ev.etype=='InvalidSequenceOfMethodCalls']
iso_orph = in_orph[in_orph.etype=='InvalidSequenceOfMethodCalls']
print('[T4] ISoMC nessas specs:', len(iso_orph), f'({len(iso_orph)/len(isomc)*100:.1f}% da categoria; gh101: 49.817/70,4%)')

# chaves do venn sustentadas por essas specs
rv_keys = set(map(tuple, ev[KEY].drop_duplicates().values))
orph_keys = set(map(tuple, in_orph[KEY].drop_duplicates().values))
print('[T4] chaves RV em specs portadoras de orfaos:', len(orph_keys), 'de', len(rv_keys),
      '| both:', len(orph_keys & cc_keys), '| only-RV:', len(orph_keys - cc_keys))

# modelo "reparo E5 sozinho": remove SO o ISoMC induzido pelo orfao, mantendo reports.
# Aproximacao superior: remove TODO ISoMC das specs portadoras (exagera o E5).
e5_keep = ev[~((ev.spec.isin(ORPHAN_SPECS)) & (ev.etype=='InvalidSequenceOfMethodCalls'))]
print('[T4] venn sob "E5 maximo" (todo ISoMC das 10 specs removido):', venn(e5_keep))

# co-emissao nas 53 chaves descartadas do cenario 3a: quantos ISoMC vs UA silenciado
d = ev[ev[KEY].apply(tuple, axis=1).isin(kb)]
tab = d.groupby('spec')['etype'].value_counts().unstack(fill_value=0)
print('\n[T4] eventos dentro das 53 chaves descartadas (cenario 3a):')
print(tab)

# combinado: allow-list comportamental (UA+UP+IKST, chave inteira) + E5-max
bad_all = set(map(tuple, ev.loc[ev['s_alias, UA+UP+IKST'], KEY].drop_duplicates().values))
keep2 = ev[~ev[KEY].apply(tuple, axis=1).isin(bad_all)]
keep2 = keep2[~((keep2.spec.isin(ORPHAN_SPECS)) & (keep2.etype=='InvalidSequenceOfMethodCalls'))]
print('[T4] venn combinado (allow-list UA+UP+IKST chave-inteira + E5-max):', venn(keep2))
