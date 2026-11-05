# 3446xA firmware research

Reverse-engineering notes and tools for the Keysight Truevolt DMM family
(**34460A, 34461A, 34465A, 34470A**), firmware **A.03.03**.

The goal is documentation: understand how the firmware is packaged and how it
works, and write up undocumented SCPI commands and features as a supplement to
the factory manual. This repository does not break licensing, options, or
instrument security; see [NOTICE.md](NOTICE.md).

## Layout

| Path | What |
|------|------|
| `tools/` | The unpack/extract pipeline (Python, plus one C decompressor) |
| `docs/` | Format spec, findings, and the handoff in `STATUS.md` |
| `analysis/` | Firmware command inventory, ROM inventory, manual diff |
| `manual_supplement/` | The supplementary manual (rendered PDF) |
| `LICENSE` | MIT, except the vendored libmspack files (LGPL 2.1) |

Start with **`docs/STATUS.md`**: it says what is done and what to do next.

## Rebuilding

Put the original `Agt3446XA_rev_A_03_03.upd` in `Firmware/`, then from the
repository root:

```sh
cd tools && sh build.sh
mkdir -p ../work
python3 unpack_upd.py  ../Firmware/Agt3446XA_rev_A_03_03.upd  ../work/nk.bin
python3 b000ff.py      ../work/nk.bin  ../work/nk_flat.bin
python3 extract_all.py ../work/nk_flat.bin  ../work/extract
```

The firmware, everything extracted from it, and the PDF manual are git-ignored.
The tools regenerate the extraction from the `.upd` in about ten seconds.

## What's inside, briefly

The `.upd` is a gzip wrapping a Microsoft XPRESS container, which wraps a
Windows Embedded CE 6.0 ROM image for ARM (ARMV4I). Inside are 186
execute-in-place modules and 253 files. The measurement application and SCPI
engine is the 8.6 MB native `Torreys.dll`, with a .NET Compact Framework 3.5
layer on top for the parser framework, LXI and GUI. ROM files are compressed
with Microsoft LZX (64 KB window, one stream per 4 KB page) and need an
Intel-E8 un-translation pass after decoding; see
[`docs/firmware_format.md`](docs/firmware_format.md).
