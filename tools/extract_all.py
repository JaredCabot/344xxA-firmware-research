#!/usr/bin/env python3
"""Full WinCE ROM extractor for the 3446xA firmware.
Dumps every ROM FILE (decompressing LZX-compressed ones) and every MODULE's
sections (code is XIP/uncompressed; compressed data sections are LZX-expanded),
plus rom_toc.json. Requires ./romfile (libmspack LZX)."""
import struct, os, json, subprocess, sys, tempfile
HERE=os.path.dirname(os.path.abspath(__file__)); ROMFILE=os.path.join(HERE,'romfile')
IMG=sys.argv[1]; OUT=sys.argv[2]; BASE=int(sys.argv[3],0) if len(sys.argv)>3 else 0x80361000
img=open(IMG,'rb').read()
def cstr(a):
    o=a-BASE; return img[o:img.find(b'\x00',o)].decode('latin1','replace')
def rd(a,n): return img[a-BASE:a-BASE+n]
assert img[0x40:0x44]==b'ECEC'
toc=struct.unpack_from('<I',img,0x44)[0]
hdr=struct.unpack_from('<17I',img,toc-BASE); nummods,numfiles=hdr[4],hdr[12]
cpu,=struct.unpack_from('<H',img,toc-BASE+68)
os.makedirs(OUT+'/files',exist_ok=True); os.makedirs(OUT+'/modules',exist_ok=True)
FA_COMPRESSED=0x800; SCN_COMPRESSED=0x2000
def lzx_file(blob, real, dst):
    with tempfile.NamedTemporaryFile(delete=False) as t: t.write(blob); tn=t.name
    try:
        r=subprocess.run([ROMFILE,tn,str(real),dst],capture_output=True,text=True)
        if r.returncode: raise RuntimeError(r.stderr.strip())
    finally: os.unlink(tn)
p=toc+84
mods=[]
for i in range(nummods):
    attr,ftl,fth,size,name,e32,o32,load=struct.unpack_from('<8I',img,p-BASE);p+=32
    mods.append((cstr(name),size,attr,e32,o32,load))
files=[]
for i in range(numfiles):
    attr,ftl,fth,real,comp,name,load=struct.unpack_from('<7I',img,p-BASE);p+=28
    files.append((cstr(name),real,comp,attr,load))
toc_json={'base':hex(BASE),'cpu':hex(cpu),'nummods':nummods,'numfiles':numfiles,'files':[],'modules':[]}
# FILES
for nm,real,comp,attr,load in files:
    blob=rd(load,comp); dst=OUT+'/files/'+nm
    if (attr & FA_COMPRESSED) and comp!=real:
        try: lzx_file(blob,real,dst)
        except Exception as e:
            open(dst,'wb').write(blob); print('FILE decomp FAIL',nm,e)
    else:
        open(dst,'wb').write(blob[:real])
    toc_json['files'].append({'name':nm,'real':real,'comp':comp,'attr':hex(attr),'compressed':bool(attr&FA_COMPRESSED and comp!=real)})
# MODULES: rebuild flat image per module at vbase; decompress compressed data sections
for nm,size,attr,e32,o32,load in mods:
    e=struct.unpack_from('<HHIIHHIIIII',img,e32-BASE); objcnt=e[0]; vbase=e[3]; entry=e[2]
    secs=[]; blob=None
    hi=0
    for j in range(objcnt):
        vs,rva,ps,dp,ra,fl=struct.unpack_from('<6I',img,o32-BASE+24*j)
        hi=max(hi,rva+vs)
        secs.append([vs,rva,ps,dp,ra,fl])
    buf=bytearray(hi)
    for vs,rva,ps,dp,ra,fl in secs:
        raw=rd(dp,ps) if ps else b''
        if (fl & SCN_COMPRESSED) and ps and ps<vs:
            with tempfile.NamedTemporaryFile(delete=False) as t: t.write(raw); tn=t.name
            od=tn+'.o'
            try:
                r=subprocess.run([ROMFILE,tn,str(vs),od],capture_output=True,text=True)
                if r.returncode: raise RuntimeError(r.stderr.strip())
                raw=open(od,'rb').read()
            except Exception as ex: print('SECT decomp fail',nm,ex)
            finally:
                os.unlink(tn)
                if os.path.exists(od): os.unlink(od)
        buf[rva:rva+len(raw)]=raw[:vs]
    open(OUT+'/modules/'+nm+'.bin','wb').write(buf)
    toc_json['modules'].append({'name':nm,'size':size,'attr':hex(attr),'vbase':hex(vbase),'entry':hex(entry),'objcnt':objcnt,
        'sections':[{'vsize':s[0],'rva':hex(s[1]),'psize':s[2],'flags':hex(s[5]),'compressed':bool(s[5]&SCN_COMPRESSED and s[2]<s[0])} for s in secs]})
json.dump(toc_json,open(OUT+'/rom_toc.json','w'),indent=1)
print('done: %d files, %d modules (any decompression failure is printed above)'%(numfiles,nummods))
