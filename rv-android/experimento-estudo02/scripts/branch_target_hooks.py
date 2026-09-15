"""Census of inline `before` monitor hooks that a branch jumps over.

The dexlib2 weaver inserts a `before` hook as instructions placed ahead of the matched invoke.
A branch whose target is the matched invoke keeps pointing at the invoke, so on that path the
hook never runs. This script finds every such site in one instrumented APK.

A site is a run of consecutive `MultiSpec_1RuntimeMonitor.<before event>` invokes immediately
followed by a non-monitor invoke whose offset is the target of an `if-*`, `goto*` or switch in the
same method. The `if-nez` guard that `IfGuardEmitter` places in front of a guarded hook targets the
same invoke on purpose and is not counted.

usage: uv run python branch_target_hooks.py <instrumented.apk> <out.csv> <descriptor.json>
Output columns: apk,cls,method,sig,event,target_invoke,invoke_off,branch_srcs,direction,app_code
(direction: layout of the branch relative to the invoke, `forward` when at least one source precedes
it; on every branch path the hook does not run, whatever the direction; a loop back-edge runs it on
the first iteration only)
plus one `#total_before_hooks=<n>` trailer line (denominator: inline before-hook runs seen).
"""
import csv, json, re, struct, subprocess, sys, tempfile, zipfile, os

DEXDUMP = os.path.join(os.environ['ANDROID_HOME'], 'build-tools/37.0.0/dexdump')
MON = 'Lmop/MultiSpec_1RuntimeMonitor;.'
METHOD = re.compile(r'\|\[[0-9a-f]+\] ([^\s:]+):(\S+)')
INSN = re.compile(r'^([0-9a-f]{6}): [0-9a-f ]+\|([0-9a-f]{4}): (\S+)(.*)$')
BRANCH = re.compile(r'^(if-\w+|goto(?:/16|/32)?)$')
SWITCH = re.compile(r'^(packed-switch|sparse-switch)$')


def before_events(descriptor):
    d = json.load(open(descriptor))
    return {c['method'].split('.', 1)[1] for a in d['advices'] if a['position'] == 'before'
            for c in a['monitorCalls']}


def switch_targets(dex, file_off, switch_addr, payload_addr):
    # payload file offset = switch instruction file offset + 2 * (payload_addr - switch_addr)
    off = file_off + 2 * (payload_addr - switch_addr)
    ident, size = struct.unpack_from('<HH', dex, off)
    if ident == 0x0100:
        rel = struct.unpack_from(f'<{size}i', dex, off + 8)
    elif ident == 0x0200:
        rel = struct.unpack_from(f'<{size}i', dex, off + 4 + 4 * size)
    else:
        raise ValueError(f'bad switch payload ident {ident:#x} at {off:#x}')
    return [switch_addr + r for r in rel]


def scan_method(name, sig, insns, dex, events, pkg, apk, out):
    targets = {}  # addr -> list of source addrs
    for i, (foff, addr, op, rest) in enumerate(insns):
        if BRANCH.match(op):
            arg = rest.split(',')[-1].split('//')[0].strip()
            if arg.startswith('#'):  # dexdump prints goto/32 as a signed relative offset
                rel = int(arg[1:], 16)
                t = addr + (rel - (1 << 32) if rel >= 1 << 31 else rel)
            else:
                t = int(arg, 16)
            targets.setdefault(t, []).append((i, addr))
        elif SWITCH.match(op):
            p = int(rest.split(',')[-1].split('//')[0].strip(), 16)
            for t in switch_targets(dex, foff, addr, p):
                targets.setdefault(t, []).append((i, addr))
    total = 0
    for i, (foff, addr, op, rest) in enumerate(insns):
        if not op.startswith('invoke') or MON in rest:
            continue
        j = i - 1
        run = []
        while j >= 0 and insns[j][2].startswith('invoke-static') and MON in insns[j][3]:
            ev = insns[j][3].split(MON, 1)[1].split(':', 1)[0]
            if ev not in events:
                break
            run.append(ev)
            j -= 1
        if not run:
            continue
        total += 1
        # the guard prefix of a guarded hook (if-nez right before the run) targets this invoke by design
        srcs = [a for (k, a) in targets.get(addr, []) if not (k == j and insns[k][2] == 'if-nez')]
        if srcs:
            cls, meth = name.rsplit('.', 1)
            tgt = rest.split('}, ', 1)[1].split(' //')[0] if '}, ' in rest else rest
            direction = 'forward' if any(s < addr for s in srcs) else 'backward'
            out.writerow([apk, cls, meth, sig, '|'.join(reversed(run)), tgt, f'{addr:04x}',
                          '|'.join(f'{s:04x}' for s in srcs), direction, int(cls.startswith(pkg))])
    return total


def main(apk_path, out_path, descriptor):
    events = before_events(descriptor)
    apk = os.path.basename(apk_path)
    pkg = apk.rsplit('_', 1)[0]
    total = 0
    with tempfile.TemporaryDirectory() as td, open(out_path, 'w', newline='') as fh:
        out = csv.writer(fh)
        out.writerow(['apk', 'cls', 'method', 'sig', 'event', 'target_invoke', 'invoke_off', 'branch_srcs',
                      'direction', 'app_code'])
        with zipfile.ZipFile(apk_path) as z:
            dexes = [n for n in z.namelist() if re.fullmatch(r'classes\d*\.dex', n)]
            for n in dexes:
                p = z.extract(n, td)
                dex = open(p, 'rb').read()
                proc = subprocess.Popen([DEXDUMP, '-d', p], stdout=subprocess.PIPE, text=True,
                                        errors='replace', bufsize=1 << 20)
                name, sig, insns = None, None, []
                for line in proc.stdout:
                    m = METHOD.search(line)
                    if m:
                        if name and not name.startswith('mop.'):
                            total += scan_method(name, sig, insns, dex, events, pkg, apk, out)
                        name, sig, insns = m.group(1), m.group(2), []
                        continue
                    m = INSN.match(line)
                    if m and name:
                        insns.append((int(m.group(1), 16), int(m.group(2), 16), m.group(3), m.group(4)))
                if name and not name.startswith('mop.'):
                    total += scan_method(name, sig, insns, dex, events, pkg, apk, out)
                proc.wait()
                os.remove(p)
        fh.write(f'#total_before_hooks={total}\n')


if __name__ == '__main__':
    main(*sys.argv[1:4])
