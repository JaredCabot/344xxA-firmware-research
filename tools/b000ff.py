#!/usr/bin/env python3
"""Stage 2: WinCE B000FF record image -> flat RAM image.
Verifies every record's checksum (byte sum), which also confirms the XPRESS
decode of stage 1. usage: b000ff.py nk.bin nk_flat.bin"""
import sys,struct
d=open(sys.argv[1],'rb').read(); assert d[:7]==b'B000FF\n','not a B000FF image'
start,length=struct.unpack_from('<II',d,7); off=15; img=bytearray(length); n=bad=0
while off<len(d):
    a,l,c=struct.unpack_from('<III',d,off);off+=12
    if a==0: break
    rec=d[off:off+l]; n+=1
    if sum(rec)&0xffffffff!=c: bad+=1; print('checksum mismatch at 0x%08x'%a)
    img[a-start:a-start+l]=rec; off+=l
open(sys.argv[2],'wb').write(img)
print('flat image: start 0x%08x len 0x%x, %d records, %d checksum errors'%(start,length,n,bad))
sys.exit(1 if bad else 0)
