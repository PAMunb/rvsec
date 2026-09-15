import glob, collections, re, sys
S = '/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/0ee8ae87-067b-4f9c-8243-e059d2f22e23/scratchpad/ge/out2'
FRAMEWORK_KEY = re.compile(r'^(Ljava/security/Key;|Ljavax/crypto/SecretKey;|Ljavax/crypto/spec/SecretKeySpec;|Ljava/security/PublicKey;|Ljava/security/PrivateKey;|Ljava/security/interfaces/[A-Za-z]*Key;|Ljavax/crypto/interfaces/[A-Za-z]*Key;)$')
GETENC_EVENTS = {'KeySpec_ge1Event', 'SecretKeySpec_e1Event'}
rows = []
for f in sorted(glob.glob(S + '/*.txt')):
    for line in open(f):
        p = line.split()
        if len(p) != 5: continue
        rows.append(p)
print('files', len(glob.glob(S + '/*.txt')), 'rows', len(rows))
# classification
by_owner = collections.defaultdict(collections.Counter)
inline_events = collections.Counter()
wrappers = collections.Counter()
for apk, cls, meth, owner, kind in rows:
    if kind.startswith('WRAPPER:'):
        wrappers[kind[8:]] += 1
        continue
    if kind.startswith('INLINE:'):
        ev = kind[7:].lstrip(';.')
        inline_events[(owner, ev)] += 1
        k = 'woven inline' if ev in GETENC_EVENTS else 'not woven (other Event nearby: %s)' % ev
    else:
        k = 'not woven'
    by_owner[owner][k] += 1
print('\n== wrapper redirections (original owner not recoverable from the wrapper call) ==')
for w, n in wrappers.most_common(): print(f'{n:6d}  {w}')
print('\n== framework Key-family owners (declared owner of the surviving invoke) ==')
tot_fw = collections.Counter()
for owner in sorted(by_owner, key=lambda o: -sum(by_owner[o].values())):
    if not FRAMEWORK_KEY.match(owner): continue
    c = by_owner[owner]; total = sum(c.values())
    inl = c.get('woven inline', 0); nw = total - inl
    tot_fw['total'] += total; tot_fw['inline'] += inl; tot_fw['none'] += nw
    print(f'{total:6d} total | inline {inl:4d} | not woven {nw:6d}  {owner}   {dict(c)}')
print('framework Key-family totals:', dict(tot_fw))
print('\n== INLINE events actually seen within 3 instrs (owner, event) ==')
for (o, e), n in inline_events.most_common(20): print(f'{n:5d} {o} {e}')
print('\n== non-framework owners with surviving getEncoded()[B invokes (top 25) ==')
for owner in sorted(by_owner, key=lambda o: -sum(by_owner[o].values()))[:60]:
    if FRAMEWORK_KEY.match(owner): continue
    print(f'{sum(by_owner[owner].values()):6d} {owner}')
print('\n== top 10 APKs by not-woven framework Key-family calls ==')
per_apk = collections.Counter(); per_apk_sites = collections.defaultdict(collections.Counter)
for apk, cls, meth, owner, kind in rows:
    if kind.startswith('WRAPPER:') or not FRAMEWORK_KEY.match(owner): continue
    if kind.startswith('INLINE:') and kind[7:].lstrip(';.') in GETENC_EVENTS: continue
    per_apk[apk] += 1; per_apk_sites[apk][(cls, meth, owner)] += 1
print('APKs with >=1 not-woven framework Key-family call:', len(per_apk), 'of', len(glob.glob(S + '/*.txt')))
for apk, n in per_apk.most_common(10):
    print(f'\n{n:5d}  {apk}')
    for (cls, meth, owner), m in per_apk_sites[apk].most_common(4):
        print(f'         {m:3d}x {cls}->{meth}  [{owner}]')
print('\n== not-woven framework Key-family calls in classes OUTSIDE bouncycastle/tink/conscrypt/google ==')
app = collections.Counter()
for apk, cls, meth, owner, kind in rows:
    if kind.startswith('WRAPPER:') or not FRAMEWORK_KEY.match(owner): continue
    if kind.startswith('INLINE:') and kind[7:].lstrip(';.') in GETENC_EVENTS: continue
    if re.match(r'^L(org/bouncycastle|org/spongycastle|com/google|org/conscrypt|okhttp3|kotlin|androidx|android|java|javax|io/netty|org/apache|net/i2p|org/eclipse)/', cls): continue
    app[(apk, cls, meth, owner)] += 1
print('sites', sum(app.values()), 'distinct (apk,class,method,owner)', len(app), 'apks', len({k[0] for k in app}))
for (apk, cls, meth, owner), n in app.most_common(25): print(f'{n:3d} {apk} {cls}->{meth} [{owner}]')
