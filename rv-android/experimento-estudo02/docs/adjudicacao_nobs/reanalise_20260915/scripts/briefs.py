import pandas as pd, re, sys
SP=sys.argv[1]
b=pd.read_csv('data/results/estudo02_consolidado/errors.csv')
n=b[b.code.str.contains('-NOBS-',na=False)].copy()
batches={
 'L1_okhttp_conscrypt': [('okhttp3.',None),('org.conscrypt.',None)],
 'L2_tink': [('com.google.crypto.tink.',None)],
 'L3_ktor': [('io.ktor.',None)],
 'L4_apps_tls': [('org.openhab.',None),('de.duenndns.',None),('de.luhmer.',None),('github.paroj.dsub2000.service',None),('com.nononsenseapps.jsonfeed',None),('de.lukasneugebauer',None),('eu.opencloud',None),('com.owncloud',None),('ch.rmy.',None),('com.etesync',None),('net.osmtracker',None),('at.bitfire',None),('com.matedroid',None),('com.ivanovsky',None)],
 'L5_apps_crypto_a': [('com.google.android.vending',None),('me.diamondforge',None),('com.leekleak',None),('com.afkanerd',None),('org.quantumbadger',None),('github.paroj.dsub2000.util',None),('rocks.poopjournal',None),('dev.leonlatsch',None),('com.google.android.gms',None)],
 'L6_apps_crypto_b': [('org.fedorahosted',None),('se.arctosoft',None),('org.flyve',None),('com.nononsenseapps.feeder',None),('com.gelakinetic',None),('org.cry.otp',None),('com.beemdevelopment',None),('com.craxiom',None),('app.michaelwuensch',None),('ua.com.radiokot',None),('dev.whyoleg',None),('io.treehouses',None),('org.spongycastle',None),('org.bouncycastle',None)],
}
def batch_of(cls):
    for k,pre in batches.items():
        for p,_ in pre:
            if cls.startswith(p): return k
    return 'UNASSIGNED'
n['batch']=n['class'].map(batch_of)
print(n.groupby('batch').size())
print(n[n.batch=='UNASSIGNED'][['class','method']].drop_duplicates())
def parse(msg):
    m=re.search(r"val='(.*?)' exp='(.*?)' msg='(.*?)'$", str(msg))
    return m.groups() if m else ('','',str(msg))
for k in batches:
    d=n[n.batch==k]
    out=[f"# Batch {k}: NOBS sites to read\n"]
    for (cls,meth),g in d.groupby(['class','method'], sort=False):
        out.append(f"\n## {cls}.{meth}\n")
        out.append(f"- NOBS lines: {len(g)}; APKs ({g.apk.nunique()}): {', '.join(sorted(g.apk.unique()))}\n")
        for (spec,code,ev),h in g.groupby(['spec','code','event']):
            srcs=h.source.value_counts()
            val,exp,msg=parse(h.message.iloc[0])
            vals=sorted(set(parse(x)[0] for x in h.message.unique()))[:6]
            out.append(f"- **{code}** (spec `{spec}`, event `{ev}`), lines {len(h)}, source lines {dict(srcs.head(4))}\n")
            out.append(f"  - expects: {exp}\n  - msg: {msg}\n  - observed val(s): {vals}\n")
    open(f'{SP}/briefs/{k}.md','w').write(''.join(out))
    print(k, d.drop_duplicates(['class','method']).shape[0], 'methods', d.drop_duplicates(['class','method','spec','code']).shape[0], 'sites', len(d), 'lines')
