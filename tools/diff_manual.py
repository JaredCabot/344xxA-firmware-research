#!/usr/bin/env python3
"""Diff the firmware command inventory against the commands the manual documents.
Manual syntax lines use SCPI optional-node brackets, e.g.
    [SENSe:]VOLTage[:DC]:NULL[:STATe] {ON|1|OFF|0}
Every combination of optional nodes is expanded and each node is reduced to its
short form, so the firmware's 'VOLT:NULL' matches that line.
usage: diff_manual.py manual.txt scpi_firmware.txt out_undoc.txt out_doc.txt"""
import sys, re, itertools
manual = open(sys.argv[1], encoding='latin1').read()
fw = [l.strip() for l in open(sys.argv[2]) if l.strip()]
def short(node):
    m = re.match(r'\*?[A-Z]+[0-9]?', node)
    return m.group() if m else node.upper()
def nodes(tok):
    """Split a manual token into (name, optional) nodes, tracking [ ] depth."""
    out, depth, cur, opt = [], 0, '', False
    for ch in tok:
        if ch == '[': depth += 1; continue
        if ch == ']': depth = max(0, depth - 1); continue
        if ch == ':':
            if cur: out.append((cur, opt)); cur = ''
            continue
        if not cur: opt = depth > 0
        cur += ch
    if cur: out.append((cur, opt))
    return out
def braces(tok):
    """Expand {A|B} alternation, innermost first. Unbalanced braces are dropped."""
    m = re.search(r'\{([^{}]*)\}', tok)
    if not m:
        return [tok.replace('{', '').replace('}', '')]
    out = []
    for alt in m.group(1).split('|'):
        out += braces(tok[:m.start()] + alt + tok[m.end():])
    return out
def expand(tok):
    res = set()
    for variant in braces(tok):
        res |= expand1(variant)
    return res
def expand1(tok):
    ns = [(n, o) for n, o in nodes(tok) if re.match(r'\*?[A-Z]', n)]
    opts = [i for i, (_, o) in enumerate(ns) if o]
    res = set()
    for r in range(len(opts) + 1):
        for drop in itertools.combinations(opts, r):
            seq = [short(n) for i, (n, _) in enumerate(ns) if i not in drop]
            if len(seq) >= 2: res.add(':'.join(seq))
    return res
doc = set()
for m in re.finditer(r'[\[\]{}|:*A-Za-z0-9]*[A-Z][a-z]*[\[\]{}|:*A-Za-z0-9]*', manual):
    t = m.group()
    if ':' in t:
        doc |= expand(t)
# The firmware also stores all-uppercase long forms (its FUNCtion name table,
# e.g. VOLTAGE:DC:RATIO). Map each upper-cased long keyword seen in the manual
# to its short form and normalize the firmware paths through it.
longmap = {}
for kw in re.findall(r'\b([A-Z]{2,}[a-z]+)\b', manual):
    longmap.setdefault(kw.upper(), short(kw))
fw = sorted(set(':'.join(longmap.get(n, n) for n in c.split(':')) for c in fw))
def dc_implied(c):
    """VOLT:NULL in the firmware's state dump is VOLT:DC:NULL with the default
    DC node omitted; the manual writes {AC|DC} explicitly."""
    p = c.split(':')
    if p[0] in ('VOLT', 'CURR') and len(p) > 1 and p[1] not in ('AC', 'DC'):
        return ':'.join([p[0], 'DC'] + p[1:])
    return c
undoc = sorted(c for c in fw if c not in doc and dc_implied(c) not in doc)
open(sys.argv[3], 'w').write('\n'.join(undoc) + '\n')
open(sys.argv[4], 'w').write('\n'.join(sorted(doc)) + '\n')
print('documented short-form paths (expanded):', len(doc),
      ' firmware paths:', len(fw), ' firmware paths not found in manual:', len(undoc))
