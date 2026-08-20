#!/usr/bin/env python3
"""Structural analyzer for JavaMOP .mop specs (audit second pass, agent B).

For each .mop file:
  - neutralizes comments (// and /* */) and string/char literals (offset-preserving);
  - brace-matches event bodies (`event <name> ... { ... }`) and handler blocks
    (`@match`/`@fail`/`@<alias>` { ... });
  - paren-matches `condition(...)` regions;
  - locates the logic block (`fsm:`/`ere:`/`ltl:`/`cfg:`/`ptltl:`/`srs:`) and
    collects the event identifiers it uses;
  - classifies each `validate(` / `setProperty(` / `remove(Property` site as
    condition / body / @match / @fail / other;
  - flags orphan events (declared but absent from the logic block).
Specs without any logic block are legitimate event-only form: reported apart,
never counted as "100% orphan".
"""

import re
import sys
import json
from pathlib import Path
from collections import defaultdict

LOGIC_KINDS = ("fsm", "ere", "ltl", "cfg", "ptltl", "ptcaret", "srs", "fsm4j")


def neutralize(text):
    """Blank out comments and string/char literals, preserving offsets/newlines."""
    out = list(text)
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == '/' and i + 1 < n and text[i + 1] == '/':
            j = i
            while j < n and text[j] != '\n':
                out[j] = ' '
                j += 1
            i = j
        elif c == '/' and i + 1 < n and text[i + 1] == '*':
            j = text.find('*/', i + 2)
            j = n if j == -1 else j + 2
            for k in range(i, j):
                if out[k] != '\n':
                    out[k] = ' '
            i = j
        elif c in ('"', "'"):
            q = c
            j = i + 1
            while j < n:
                if text[j] == '\\':
                    j += 2
                    continue
                if text[j] == q or text[j] == '\n':
                    break
                j += 1
            j = min(j + 1, n)
            # keep the quotes, blank the inside
            for k in range(i + 1, j - 1):
                if out[k] != '\n':
                    out[k] = ' '
            i = j
        else:
            i += 1
    return ''.join(out)


def match_brace(text, open_idx):
    """Return index just past the brace matching text[open_idx] == '{'."""
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return i + 1
    return len(text)


def match_paren(text, open_idx):
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] == '(':
            depth += 1
        elif text[i] == ')':
            depth -= 1
            if depth == 0:
                return i + 1
    return len(text)


def line_of(text, idx):
    return text.count('\n', 0, idx) + 1


EVENT_RE = re.compile(r'\b(creation\s+)?event\s+(\w+)\b')
SPEC_HDR_RE = re.compile(
    r'^[ \t]*((?:(?:unsynchronized|decentralized|perthread|suffix|full-?binding|avoid|enforce|connected)\s+)*)'
    r'([A-Za-z_]\w*)\s*\(([^)]*)\)\s*\{', re.M)
LOGIC_RE = re.compile(r'\b(%s)\s*:' % '|'.join(LOGIC_KINDS))
HANDLER_RE = re.compile(r'@(\w+)\s*\{')
COND_RE = re.compile(r'\bcondition\s*\(')
SITE_RE = re.compile(r'\b(validate|setProperty|remove)\s*\(')


def analyze_file(path):
    raw = path.read_text(errors='replace')
    text = neutralize(raw)
    res = {
        'file': str(path), 'specs': [], 'sites': [],
        'notes': [],
    }

    # ---- spec headers (a file may hold >1 spec: flag it) ----
    headers = []
    for m in SPEC_HDR_RE.finditer(text):
        name = m.group(2)
        if name in ('if', 'for', 'while', 'switch', 'catch', 'new'):
            continue
        # must be at top level (outside every previously found spec body)
        if any(s <= m.start() < e for _, s, e in headers):
            continue
        end = match_brace(text, m.end() - 1)
        headers.append((m, m.start(), end))
    if not headers:
        res['notes'].append('NO_SPEC_HEADER_FOUND')
        return res

    for m, hstart, hend in headers:
        modifiers = m.group(1).split()
        name, params_txt = m.group(2), m.group(3)
        body = text[m.end():hend - 1]
        boff = m.end()  # offset of spec body in `text`
        spec = {
            'name': name, 'modifiers': modifiers, 'line': line_of(text, hstart),
            'params': [], 'dup_params': [], 'events': [], 'creation_events': [],
            'logic': None, 'logic_events_used': [], 'orphans': [],
            'handlers': [], 'aliases': [], 'event_only': False,
        }
        # parameters + duplicate names
        pnames = []
        for p in params_txt.split(','):
            p = p.strip()
            if not p:
                continue
            toks = p.replace('[]', ' ').split()
            if toks:
                pnames.append(toks[-1])
        spec['params'] = pnames
        spec['dup_params'] = sorted({x for x in pnames if pnames.count(x) > 1})
        spec['primitive_or_array_params'] = [
            p.strip() for p in params_txt.split(',')
            if p.strip() and (('[]' in p) or p.split()[0] in
                              ('int', 'long', 'boolean', 'byte', 'char',
                               'short', 'float', 'double'))]

        # regions inside this spec body
        regions = []  # (start, end, kind, label) offsets in `text`

        # events
        events = []
        for em in EVENT_RE.finditer(body):
            estart = boff + em.start()
            ename = em.group(2)
            creation = bool(em.group(1))
            # find event body: first '{' after the declaration, unless another
            # event/logic/handler keyword comes first (bodiless events).
            nxt = EVENT_RE.search(body, em.end())
            lim = boff + (nxt.start() if nxt else len(body))
            lm = LOGIC_RE.search(text, estart, lim)
            if lm:
                lim = lm.start()
            brace = text.find('{', boff + em.end(), lim)
            bodyspan = None
            if brace != -1:
                bend = match_brace(text, brace)
                bodyspan = (brace, bend)
                regions.append((brace, bend, 'body', ename))
            # condition(...) regions between decl and body/limit
            czone_end = brace if brace != -1 else lim
            for cm in COND_RE.finditer(text, estart, czone_end):
                cend = match_paren(text, cm.end() - 1)
                regions.append((cm.end() - 1, cend, 'condition', ename))
            events.append({'name': ename, 'creation': creation,
                           'line': line_of(text, estart),
                           'has_body': bodyspan is not None})
        spec['events'] = [e['name'] for e in events]
        spec['creation_events'] = [e['name'] for e in events if e['creation']]
        spec['events_detail'] = events

        # logic block
        lm = LOGIC_RE.search(text, boff, hend)
        logic_events = set()
        if lm:
            kind = lm.group(1)
            spec['logic'] = kind
            # logic text: from ':' to first handler '@' or spec end
            hm = HANDLER_RE.search(text, lm.end(), hend)
            # alias lines belong to logic tail; stop at first '@handler'
            lend = hm.start() if hm else hend - 1
            ltxt = text[lm.end():lend]
            if kind == 'fsm':
                logic_events = set(re.findall(r'(\w+)\s*->', ltxt))
                # 'default X' clauses name states, not events; '->' already
                # excludes them.
            else:
                toks = set(re.findall(r'[A-Za-z_]\w*', ltxt))
                logic_events = toks & set(spec['events'])
            # aliases (state aliases in fsm; ere aliases rare)
            spec['aliases'] = re.findall(r'\balias\s+(\w+)\s*=', ltxt)
            spec['logic_events_used'] = sorted(logic_events & set(spec['events']))
            spec['orphans'] = sorted(set(spec['events']) - logic_events)
            # reverse orphans: symbols the logic uses that no event declares
            if kind == 'fsm':
                raw_used = set(re.findall(r'(\w+)\s*->', ltxt))
            else:
                raw_used = set(re.findall(r'[A-Za-z_]\w*', ltxt)) - {
                    'epsilon', 'empty', 'alias'}
                raw_used -= set(spec['aliases'])
                # states named on alias right-hand sides are not events either
                raw_used -= set(re.findall(r'\balias\s+\w+\s*=\s*(\w+)', ltxt))
            spec['undeclared_logic_symbols'] = sorted(
                raw_used - set(spec['events']))
        else:
            spec['event_only'] = True

        # handlers
        for hm2 in HANDLER_RE.finditer(text, boff, hend - 1):
            hname = hm2.group(1)
            hend2 = match_brace(text, hm2.end() - 1)
            regions.append((hm2.end() - 1, hend2, 'handler', hname))
            spec['handlers'].append(hname)

        # predicate sites within this spec
        for sm in SITE_RE.finditer(text, boff, hend - 1):
            fn = sm.group(1)
            # Predicate API takes Property.<X> as first argument. Anything else
            # (private helper `validate(int)`, Iterator.remove(), a helper that
            # shadows the name) is NOT a predicate site: count it apart, since
            # a naive name-based gate would miscount exactly here.
            after = text[sm.end():sm.end() + 40]
            if not after.lstrip().startswith('Property'):
                res.setdefault('shadowed_sites', []).append(
                    {'spec': name, 'fn': fn, 'line': line_of(text, sm.start())})
                continue
            pos = sm.start()
            klass, label = 'other', ''
            # innermost region wins: condition < body/handler nesting
            best = None
            for (s0, e0, kind, lab) in regions:
                if s0 <= pos < e0:
                    if best is None or (e0 - s0) < (best[1] - best[0]):
                        best = (s0, e0, kind, lab)
            if best:
                kind, lab = best[2], best[3]
                if kind == 'condition':
                    klass = 'condition'
                elif kind == 'body':
                    klass, label = 'body', lab
                elif kind == 'handler':
                    klass = '@' + lab
            res['sites'].append({'spec': name, 'fn': fn, 'class': klass,
                                 'label': label, 'line': line_of(text, pos)})
        res['specs'].append(spec)
    return res


def main(root):
    root = Path(root)
    sets = ['jca', 'jca_android', 'jca_android_bug_predicate',
            'generic', 'generic_new']
    summary = {}
    details = {}
    for s in sets:
        files = sorted((root / s).glob('*.mop'))
        agg = {
            'n_files': len(files), 'orphans': [], 'event_only': [],
            'validate': defaultdict(int), 'setProperty': defaultdict(int),
            'remove': defaultdict(int), 'dup_params': [], 'multi_spec': [],
            'no_header': [], 'notes': [], 'shadowed': [], 'reverse_orphans': [],
            'dup_events': [],
        }
        for f in files:
            r = analyze_file(f)
            details[str(f)] = r
            if len(r['specs']) > 1:
                agg['multi_spec'].append(f.name)
            if not r['specs']:
                agg['no_header'].append(f.name)
            for sp in r['specs']:
                if sp['event_only']:
                    agg['event_only'].append(f.name)
                else:
                    for o in sp['orphans']:
                        agg['orphans'].append((f.name, sp['name'], o))
                if sp['dup_params']:
                    agg['dup_params'].append((f.name, sp['dup_params']))
                for u in sp.get('undeclared_logic_symbols', []):
                    agg['reverse_orphans'].append((f.name, sp['name'], u))
                cnt = {}
                for e in sp['events']:
                    cnt[e] = cnt.get(e, 0) + 1
                for e, k in cnt.items():
                    if k > 1:
                        agg['dup_events'].append((f.name, sp['name'], e, k))
            for sh in r.get('shadowed_sites', []):
                agg['shadowed'].append((f.name, sh['fn'], sh['line']))
            for site in r['sites']:
                key = site['class']
                if key.startswith('@'):
                    key = '@fail' if key == '@fail' else '@match-like:' + key
                agg[site['fn']][key] += 1
        summary[s] = agg

    for s, a in summary.items():
        print(f"\n=== {s}  ({a['n_files']} .mop) ===")
        orf_specs = sorted({(f, sp) for f, sp, _ in a['orphans']})
        print(f"orphan events: {len(a['orphans'])} in {len(orf_specs)} specs")
        for f, sp, o in a['orphans']:
            print(f"  ORPHAN {f} :: {sp} :: {o}")
        if a['event_only']:
            print(f"event-only specs (no fsm/ere): {len(a['event_only'])}")
            for f in a['event_only']:
                print(f"  EVENT-ONLY {f}")
        for fn in ('validate', 'setProperty', 'remove'):
            if a[fn]:
                tot = sum(a[fn].values())
                print(f"{fn}: {tot}  {dict(a[fn])}")
        if a['dup_params']:
            print(f"dup-param specs: {len(a['dup_params'])}")
            for f, d in a['dup_params']:
                print(f"  DUP {f} {d}")
        if a['multi_spec']:
            print(f"multi-spec files: {a['multi_spec']}")
        if a['no_header']:
            print(f"NO HEADER PARSED: {a['no_header']}")
        for f, sp, u in a['reverse_orphans']:
            print(f"  REVERSE-ORPHAN {f} :: {sp} :: logic uses undeclared '{u}'")
        for f, sp, e, k in a['dup_events']:
            print(f"  DUP-EVENT {f} :: {sp} :: '{e}' declared {k}x")
        if a['shadowed']:
            print(f"name-shadowed non-predicate sites: {len(a['shadowed'])}")
            for f, fn, ln in a['shadowed']:
                print(f"  SHADOWED {f}:{ln} {fn}(...) without Property arg")

    out = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    if out:
        def _default(o):
            if isinstance(o, tuple):
                return list(o)
            raise TypeError
        out.write_text(json.dumps(
            {'summary': {k: {kk: (dict(vv) if isinstance(vv, defaultdict) else vv)
                             for kk, vv in v.items()} for k, v in summary.items()},
             'details': details}, indent=1, default=_default))
        print(f"\n[json] {out}")


if __name__ == '__main__':
    main(sys.argv[1])
