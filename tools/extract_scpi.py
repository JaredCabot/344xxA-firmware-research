#!/usr/bin/env python3
"""Extract the SCPI command inventory from the decompressed firmware.
Source: readable ASCII strings in Torreys.dll (native measurement engine),
including the instrument's semicolon-separated query-dump template.
Keywords keep their original case; each node is reduced to the SCPI short form
(its leading upper-case run) so that 'SYSTem:LOCK' and 'SYST:LOCK' agree.
Writes one canonical short-form path per line.
usage: extract_scpi.py <extract_dir> <out.txt>"""
import sys, re, os
ext, out = sys.argv[1], sys.argv[2]
# strings that look like colon paths but are not commands
JUNK = {'HH:MM:SS', 'USB0'}
def short(node):
    m = re.match(r'\*?[A-Z]+[0-9]?', node)
    return m.group() if m else node.upper()
paths = set()
data = open(os.path.join(ext, 'files', 'Torreys.dll'), 'rb').read()
for b in re.findall(rb'[\x20-\x7e]{3,}', data):
    for tok in re.split(r'[;\s,"\'()]+', b.decode()):
        t = tok.strip().rstrip('?').lstrip(':')
        if not re.fullmatch(r'\*?[A-Za-z]{2,14}(:[A-Za-z]{2,14}){1,6}', t):
            continue
        nodes = t.split(':')
        if not all(re.match(r'[A-Z]', n) for n in nodes):
            continue
        p = ':'.join(short(n) for n in nodes)
        if p not in JUNK and not p.startswith('USB'):
            paths.add(p)
open(out, 'w').write('\n'.join(sorted(paths)) + '\n')
print('firmware SCPI paths:', len(paths))
