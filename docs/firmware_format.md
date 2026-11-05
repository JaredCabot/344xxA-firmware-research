# The 3446xA firmware package format

This describes the `.upd` file layout from the outside in, so the image can be
rebuilt or re-derived. All multi-byte values are little-endian. Everything here
was checked against firmware A.03.03 only.

## Layer 1: the `.upd` wrapper

```
offset 0         u64   xmlLen
offset 8               XML description (xmlLen bytes, UTF-8)
offset 8+xmlLen        gzip stream (to EOF)
```

The XML names the models (34460A/34461A/34465A/34470A), the version
(`A.03.03`), the build date (`7/2/2021 5:45:07 PM`), and a base64 MD5. The MD5
covers the gzip's *inflated* contents, which is the XPRESS container in layer 2,
not the final `nk.bin`. `unpack_upd.py` checks it.

## Layer 2: the XPRESS container (`XPRS`)

```
'XPRS'  (4 bytes)
u32     total uncompressed size
then repeated blocks:
  u32   blockSize, flags in the top two bits
  ...   blockSize bytes
```

- Bit 31 set: the block is stored, copied verbatim (size in the low 31 bits).
- Bit 30 set: short final block. The next u32 is the uncompressed length, and an
  XPRESS-LZ77 stream follows. The encoder leaves the last 4 output bytes (the
  B000FF end record's zero checksum) implicit, so the decoder zero-fills to the
  stated length.
- Otherwise: a normal XPRESS-LZ77 block that expands to 65536 bytes.

The LZ77 is the plain Microsoft XPRESS variant: 32-bit flag words read
MSB-first, 1 = match; 2-byte match token with `length = token & 7` and
`offset = (token >> 3) + 1`, plus the nibble/byte/word length-extension ladder.
The output is `nk.bin`. The decode is confirmed by layer 3: all 168 record
checksums in `nk.bin` pass.

## Layer 3: the Windows CE ROM image (`B000FF`)

`nk.bin` is a standard Windows CE record image.

```
'B000FF\n'
u32  image start address   ($80361000 here)
u32  image length          ($0185E320)
then records:
  u32 address, u32 length, u32 checksum (byte sum), <length bytes>
  a record with address 0 ends the list; its length field is the entry point ($80362000)
```

Writing each record at `address - start` into a flat buffer gives the RAM image
(`nk_flat.bin`). The ROM table of contents is reached through the `ECEC`
signature at flat offset $40, whose following u32 points at the `ROMHDR`
($81BBBFE0). From there you get the module list (186 entries) and the file list
(253 entries).

The OS is Windows Embedded CE 6.0. 181 of the 186 modules carry subsystem
version 6.0, the kernel identifies itself as "Windows CE Kernel for ARM (Thumb
Enabled) Built on Mar 8 2013", and `Torreys.dll`'s PDB path names the
`STM320s_CE6.0_ACCL (ARMV4I)` SDK. The CPU type in the ROM header is $01C2
(`IMAGE_FILE_MACHINE_THUMB`), which CE uses for ARMV4I images. The code is
32-bit ARM with Thumb interworking, not Thumb-2.

## Layer 4: ROM file / section compression

Modules keep their executable sections uncompressed so they can run in place.
Their writable data sections, and most ROM files, may be compressed: the `$800`
file attribute marks a compressed file, `$2000` a compressed module section.

A compressed item is split into 4096-byte pages. It begins with a table:

```
u24              total uncompressed size
u24 * nPages     end offset of each page's block, from the start of the item
```

Page 0's block starts right after the table; page *k* starts where page *k-1*
ended. Each block is:

```
u32  $00000010          header length (16 bytes, including this word)
u32  uncompressed size  (4096, except the last page)
u32  compressed size    (bytes after the 16-byte header)
u32  uncompressed size  (repeated)
---- compressed data ----
u32  $8D80805B          constant on every page; not checked by the decoder
...  LZX bitstream
```

The bitstream is Microsoft LZX with a 64 KB window (`window_bits = 16`), one
independent stream per page. After decoding, **the Intel-E8 call translation
must be undone**, even though the stream's own E8 header bit is 0 on every page:
translation size 12,000,000, with positions measured from the start of each
4 KB page. Skipping this step leaves wrong bytes after many `$E8` bytes: 73 of
the 222 compressed files and 34 module images are affected, including
`Torreys.dll` and the .NET assemblies.

For a module data section, the decoded size can be smaller than the section's
virtual size; the remainder is zero-filled BSS.

### How the decode was verified

- All 222 compressed files and all 309 compressed module sections decode to
  exactly the size their own headers declare, with no LZX errors.
- Files with built-in integrity checks pass: all 15 PNGs have valid chunk CRCs,
  `DM344XXA.jar` passes a full zip CRC test, and every base relocation in
  `Torreys.dll` has a valid type (0 or 3).
- Text files with known contents (`jquery-1.12.3.min.js`, `bootstrap.min.css`,
  the C headers) decode to their expected contents. These contain no `$E8`
  bytes, so on their own they could not catch the E8 step; the CRC and
  relocation checks above are what confirm it.
