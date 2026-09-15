import pandas as pd, sys
SP=sys.argv[1]
b=pd.read_csv('data/results/estudo02_consolidado/errors.csv')
b['nobs']=b.code.str.contains('-NOBS-',na=False)
b['fam']=b.code.str.extract(r'-([A-Z]+)-\d+$')[0]
K=['apk','tool','rep','timeout','class','method','spec']
b['kid']=b.groupby(K).ngroup()
ord3=b.spec.isin(['TrustManagerFactorySpec','KeyManagerFactorySpec','SecureRandomSpec'])&(b.fam=='ORDER')
# double-fire artifact: g2 trigger in the same key, in another method of the same run+spec, or at the same site in other runs
g2=ord3&(b.event=='g2'); b['rid']=b.groupby(['apk','tool','rep','timeout','spec']).ngroup()
site=b[['class','method','spec']].apply(tuple,axis=1)
b['art']=ord3&(b.kid.isin(set(b[g2].kid))|b.rid.isin(set(b[g2].rid))|site.isin(set(site[g2])))
val=b.fam.isin(['ALG','KEYSIZE','CONSTR','PROTO','FORB'])
# security relevance of value codes (r7)
sec_yes={('com.andrognito.patternlockview.utils.PatternLockUtils','patternToSha1'),('org.fossify.commons.views.PinTab','getHashedPin'),('de.lukasneugebauer.nextcloudcookbook.core.util.OkHttpClientProvider','configureTrustAllCertificates')}
sec_deb={('org.flyve.inventory.CryptoUtil','encrypt'),('github.paroj.dsub2000.util.Util','md5Hex'),('com.google.android.vending.licensing.AESObfuscator','<init>'),('app.michaelwuensch.bitbanana.util.UtilFunctions','encodePbkdf2')}
def cat(r):
    if r.nobs or r.art: return None
    if val[r.name]: 
        k=(r['class'],r['method']); return 'GENUINE_yes' if k in sec_yes else ('GENUINE_debatable' if k in sec_deb else 'GENUINE_no')
    # ORDER-00 non-artifact
    if r.spec in ('KeyPairSpec','AlgorithmParametersSpec'): return 'UNOBSERVED_CREATION'
    if r.spec=='SecureRandomSpec': return 'UNOBSERVED_CREATION' if 'spongycastle' in r['class'] else 'WEAVER_ARTIFACT_doublefire'
    if r.spec=='SignatureSpec': return 'WEAVER_ARTIFACT_branch'
    if r.spec=='CipherSpec' and 'aegis' in r['class']: return 'WEAVER_ARTIFACT_branch'
    if r.spec=='MessageDigestSpec' and ('FileID' in r['class'] or 'MessageDigestHashFunction' in r['class']): return 'UNOBSERVED_CREATION'
    if r.spec in ('CipherSpec','MacSpec','MessageDigestSpec','SSLContextSpec'): return 'ORDER_CASCADE_OR_REUSE'
    return 'OTHER'
nn=b[~b.nobs&~b.art].copy()
nn['cat']=nn.apply(cat,axis=1)
# per key: GENUINE if any value code; else ORDER-only classification: cascade needs value in same key (already excluded), so reuse/unobserved/artifact
rank={'GENUINE_yes':6,'GENUINE_debatable':5,'GENUINE_no':4,'ORDER_CASCADE_OR_REUSE':3,'UNOBSERVED_CREATION':2,'WEAVER_ARTIFACT_doublefire':1,'WEAVER_ARTIFACT_branch':1,'OTHER':0}
inv={v:k for k,v in rank.items()}
g=nn.groupby('kid').agg(r=('cat',lambda s: max(rank[x] for x in s)),spec=('spec','first'),cls=('class','first'),m=('method','first'),apk=('apk','first'))
g['status']=g.r.map(inv)
# ORDER-only keys that are 'ORDER_CASCADE_OR_REUSE' have no value code in the key (else GENUINE) -> LEGAL_REUSE (Cipher/Mac) 
g.loc[(g.status=='ORDER_CASCADE_OR_REUSE'),'status']='LEGAL_REUSE_REJECTED'
print('keys sustained by non-NOBS code (first pass 6 765):',len(g)); print(g.status.value_counts().to_string())
print(g[g.status=='LEGAL_REUSE_REJECTED'].groupby(['spec','cls','m']).size().to_string())
print(g[g.status.str.startswith('WEAVER')].groupby(['spec','cls','m']).size().to_string())
print(g[g.status=='UNOBSERVED_CREATION'].groupby(['spec','cls']).size().to_string())
g.to_csv(f'{SP}/nonnobs_keys.csv')
# combine with NOBS projection
nk=pd.read_csv(f'{SP}/my_verdicts_all_keys.csv').set_index('kid')
nk.loc[g.index,'status']='OTHER:'+g.status
print('\nFULL PARTITION (27 068):'); print(nk.status.value_counts().to_string())
strict=nk.status.isin(['NOBS:MISUSE'])|nk.status.str.startswith('OTHER:GENUINE')
print('sustained (rule-genuine or NOBS misuse):',int(strict.sum()),round(strict.mean(),3))
sec=nk.status.isin(['NOBS:MISUSE','OTHER:GENUINE_yes','OTHER:GENUINE_debatable'])
print('security-relevant sustained (misuse + genuine yes/debatable):',int(sec.sum()),round(sec.mean(),3))
nk['strict']=strict; nk['sec']=sec
print(nk.groupby('tool').strict.mean().round(3).to_string()); print(nk.groupby('timeout').strict.mean().round(3).to_string())
print('apks 91; with strict-sustained',nk[nk.strict].apk.nunique(),'; with security-relevant',nk[nk.sec].apk.nunique())
nk.to_csv(f'{SP}/full_partition_keys.csv')
