#!/usr/bin/env python3
"""Stage 1: Keysight 3446xA .upd firmware package -> nk.bin (WinCE B000FF image).
The .upd = [u64 xmlLen][XML][gzip stream]. The gzip inflates to an "XPRS"
container: 'XPRS'[u32 totalUncomp] then blocks {[u32 size]data}. Block size bit31
=stored, bit30=short-final(next u32=uncompressed len). Inner codec = MS-XPRESS LZ77.
Verifies the MD5 in the XML header. usage: unpack_upd.py in.upd out.nk.bin"""
import sys,struct,gzip,hashlib,base64
def xpress(ib,outmax=1<<30):
    out=bytearray();ip=0;flags=0;fc=0;nib=-1
    while len(out)<outmax:
        if fc==0:
            if ip+4>len(ib):break
            flags=struct.unpack_from('<I',ib,ip)[0];ip+=4;fc=32
        fc-=1
        if not (flags>>fc)&1:
            if ip>=len(ib):break
            out.append(ib[ip]);ip+=1;continue
        if ip+2>len(ib):break
        mb=ib[ip]|ib[ip+1]<<8;ip+=2;length=mb&7;off=(mb>>3)+1
        if length==7:
            if nib==-1:nib=ip;length=ib[ip]&15;ip+=1
            else:length=ib[nib]>>4;nib=-1
            if length==15:
                length=ib[ip];ip+=1
                if length==255:length=ib[ip]|ib[ip+1]<<8;ip+=2;length-=22
                length+=15
            length+=7
        length+=3
        for _ in range(length):out.append(out[-off])
    return bytes(out)
def main():
    d=open(sys.argv[1],'rb').read()
    n=struct.unpack_from('<Q',d,0)[0]; xml=d[8:8+n].decode()
    md5=base64.b64decode([l.split('>')[1].split('<')[0] for l in xml.splitlines() if 'md5hash' in l][0])
    payload=gzip.decompress(d[8+n:])
    assert hashlib.md5(payload).digest()==md5,'md5 mismatch'
    assert payload[:4]==b'XPRS'
    total=struct.unpack_from('<I',payload,4)[0]; ip=8; out=bytearray()
    while ip+4<=len(payload) and len(out)<total:
        cs=struct.unpack_from('<I',payload,ip)[0];ip+=4
        if cs&0x80000000: cs&=0x7fffffff; out+=payload[ip:ip+cs]; ip+=cs
        elif cs&0x40000000:
            cs&=0x3fffffff; ul=struct.unpack_from('<I',payload,ip)[0]
            r=xpress(payload[ip+4:ip+cs],ul); r+=b'\x00'*(ul-len(r)); out+=r[:ul]; ip+=cs
        else:
            out+=xpress(payload[ip:ip+cs],65536); ip+=cs
    open(sys.argv[2],'wb').write(out[:total])
    print("nk.bin %d bytes (container MD5 OK)"%len(out))
main()
