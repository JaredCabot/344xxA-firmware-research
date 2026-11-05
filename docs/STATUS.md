# Project status and handoff

**Instrument:** Keysight Truevolt DMM family: 34460A, 34461A, 34465A (6½ digit), 34470A (7½ digit)
**Firmware analysed:** `Agt3446XA_rev_A_03_03.upd`, version **A.03.03**, built 2021-07-02
**Scope:** understand how the firmware is built and packed, extract its contents, and document undocumented SCPI commands and features. License, option and security bypass is out of scope; see NOTICE.md.

## What is done

1. **The package is unpacked and every layer checked.** The header MD5 matches the XPRESS container, all 168 B000FF record checksums pass, and the ROM table of contents reads cleanly (186 modules, 253 files). See `docs/firmware_format.md`.
2. **The ROM compression is solved.** It is Microsoft LZX, 64 KB window, one stream per 4 KB page, *followed by an Intel-E8 un-translation step* (size 12,000,000, per page) that the stream header does not flag. `tools/romfile.c` does both.
3. **Everything is extracted and integrity-checked.** All compressed items decode to their declared sizes; every PNG CRC, the JAR's zip CRCs and `Torreys.dll`'s relocation table check out.
4. **The SCPI command set is inventoried and diffed against the manual.** See `docs/findings_undocumented.md` for the confirmed undocumented commands and their evidence.
5. **A supplementary manual** in the HP house style is in `manual_supplement/`.

## Correction history

The first pass (commit `fbb5083`) shipped an extractor without the E8 step. Its output was wrong in 73 of the 222 compressed files and 34 module images, `Torreys.dll` and the .NET assemblies included; the files it was checked against happen to contain no `$E8` bytes. An independent review found it, along with several factual errors in the docs (OS version, CPU, model digit counts, what the header MD5 covers, front-panel hardware, DIAG command semantics). All are fixed in the following commit. If you have output from the first pass, regenerate it.

## Where things are

After running the pipeline, the extracted firmware is in `work/extract/` (git-ignored):

- `work/extract/files/Torreys.dll`: 8.6 MB (8,576,000 bytes) native ARM PE, ARMV4I (32-bit ARM with Thumb interworking), PE machine $01C2, image base $10000000. The measurement application and SCPI engine. It is a compressed ROM file, not one of the XIP modules.
- `work/extract/files/Torreys.exe`: a small .NET host that calls into `Torreys.dll`.
- `work/extract/files/Agilent.Cdf.*.dll`: the .NET Compact Framework 3.5 layer (SCPI parser framework, LXI, licensing, secure storage, GUI).
- `work/extract/files/*.asp`, `*.htm`, `*.js`, `DM344XXA.jar`: the LXI web interface and remote front panel.
- `work/extract/files/WarmupRackTest.exe`: a Keysight test tool whose command strings show DIAG syntax.
- `work/extract/files/FrontPanel.Config.xml`, `Msp430FrontPanel.Config.xml`, `AgtFrontPanelKeyMap.34460-66502.xml`, `AgtFP*.hex`: front-panel microcontroller configs, key map and firmware.
- `work/extract/rom_toc.json`: the full ROM table of contents.

## What to do next

The command inventory comes from readable strings. The full SCPI parser tree (every node, its parameters, any hidden flag) is built in code. Recovering it means:

1. Loading `Torreys.dll` in Ghidra as **ARM:LE:32:v5t** (not Thumb-2), image base $10000000. It is a normal PE with a valid relocation table, so auto-analysis works.
2. Decompiling the .NET assemblies (`Agilent.Cdf.Api.UI.Scpi.dll` and friends) with ILSpy or `ilspycmd`. No .NET decompiler was available in the environment used so far.
3. Exercising the AC Mode and DIAG commands on a spare instrument to confirm parameters and responses; nothing has been tested on hardware yet.

Then extend `docs/findings_undocumented.md` and update the supplement PDF in `manual_supplement/`.

## How to reproduce from scratch

From the repository root, with the original `.upd` in `Firmware/`:

```sh
cd tools && sh build.sh
mkdir -p ../work
python3 unpack_upd.py  ../Firmware/Agt3446XA_rev_A_03_03.upd  ../work/nk.bin
python3 b000ff.py      ../work/nk.bin  ../work/nk_flat.bin
python3 extract_all.py ../work/nk_flat.bin  ../work/extract
python3 extract_scpi.py ../work/extract ../analysis/scpi_firmware.txt
pdftotext -layout "../Manuals/34465A Manual 9018-03876.pdf" ../work/manual.txt
python3 diff_manual.py ../work/manual.txt ../analysis/scpi_firmware.txt \
        ../analysis/scpi_not_in_manual.txt ../analysis/scpi_manual_normalized.txt
```

Extraction takes about ten seconds. `work/`, `Firmware/` and `Manuals/` are git-ignored: they hold Keysight and Microsoft material that must not be redistributed.
