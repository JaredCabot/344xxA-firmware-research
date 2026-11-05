# Tools

Pipeline, in order:

1. `unpack_upd.py in.upd out.nk.bin`: strip the gzip + XPRESS container, verify
   the header MD5, emit the Windows CE `nk.bin`.
2. `b000ff.py nk.bin nk_flat.bin`: flatten the B000FF record image to a RAM image.
3. `extract_all.py nk_flat.bin outdir/`: dump 186 modules and 253 files, decompressing
   LZX-compressed ones. Writes `rom_toc.json`. Needs `./romfile` (run `build.sh`).
4. `extract_scpi.py extractdir/ out.txt`: SCPI command inventory from `Torreys.dll`.
5. `diff_manual.py manual.txt firmware.txt undoc.txt doc.txt`: diff against the manual.

`romfile.c` is the Windows CE ROM LZX decompressor. It links libmspack's
`lzxd.c`, vendored here unmodified with its headers; those files are under the
GNU LGPL 2.1 (see `COPYING.LIB`), not the repository's MIT license. Build with
`sh build.sh`. `romfile` exits non-zero if any page fails to decode, and
`extract_all.py` reports it.
