# Undocumented commands and internal features

Everything here was read out of firmware A.03.03 for documentation purposes.
None of it bypasses licensing, options, or instrument security, and the notes
stop short of anything that would (see NOTICE.md).

"Documented" means listed in the *Keysight Truevolt Series Operating and Service
Guide* (9018-03876), which covers all four models. It contains no `DIAGnostic`
and no `SYSTem:FPANel` commands at all.

Evidence levels used below:

- **Firmware command:** the command string is in the instrument's own firmware.
- **Sent by a Keysight tool:** a program shipped in the ROM sends this exact
  command to the instrument, which shows the syntax.
- **Inferred:** meaning worked out from surrounding names or messages. Not
  exercised on an instrument.

None of these commands has been sent to an instrument for this write-up.

## Measurement settings

### `[SENSe:]VOLTage:AC:MODE` and `[SENSe:]CURRent:AC:MODE`

Firmware command. Both appear in the instrument's own state-dump query list
(`:VOLT:AC:MODE?`, `:CURR:AC:MODE?`) next to the documented `:BAND`, `:NULL` and
`:RANG` settings. The front-panel strings have a "Meas Settings" menu with an
"AC Mode" entry offering **RMS** and **Avg**.

Inferred: this selects between the documented true-RMS AC measurement and an
average-responding mode, which the manual never mentions. The parameter
spellings accepted over SCPI are not confirmed.

## The DIAGnostic subsystem

### Commands in the measurement firmware (`Torreys.dll`)

The keyword table holds `DIAG` with `POKE`, `PEEK`, `OFINIT`, `OFCLR`, `FPGA`
and `FP`/`KEYPress`.

| Command | Evidence | What is known |
|---|---|---|
| `DIAG:POKE <op>[,<a1>[,<a2>[,<a3>]]]` | Sent by a Keysight tool: `WarmupRackTest.exe` sends `DIAG:POKE 123,1,0`, `DIAG:POKE 123,1,1`, `diag:poke 37` | A numbered internal-operation call: an operation code plus up to three arguments. One operation reports whether a primary or secondary AC flatness data record is present ("DIAG:POKE %d: Primary flatness data record", "...There is no flatness data record available"). What the other operation codes do is not known. |
| `DIAG:PEEK? <a>, <b>` | Sent by a Keysight tool: `DIAG:PEEK? 2, 4`, `DIAG:PEEK? %i, 5` | Read-side companion to POKE. Meaning of the arguments not known. |
| `DIAG:FPGA:SWITch:SET <n>` | Sent by a Keysight tool: `diag:fpga:switch:set %u` | Inferred: sets the measurement FPGA's switch configuration, used by the warm-up rack test. |
| `DIAG:FP:KEYPress "<key>"` | Firmware command; written into the firmware's own front-panel macro files | Simulates a front-panel key press. The firmware's "Front Panel Event Log" recorder writes `.demo` scripts made of `run_scpi`, `wait`, `simulate_key` and `DIAG:FP:KEYP "<key>"` lines. Key names include `Softkey0`-`5`, `Hardkey0`-`29`, `KnobLeft`/`KnobRight` and `EnterNumber`. `DIAG:FP:KEYP "QuickHelp <key>"` triggers the quick-help (press-and-hold) action for a key. |
| `DIAG:OFINIT`, `DIAG:OFCLR` | Firmware command | Factory identity initialisation. `DIAG:OFINIT` checks for a 10-character serial number starting with two letters and writes the instrument's identity records to its secure storage. Parameters and behaviour are deliberately not documented here: those records determine the model and its feature set, which is outside this project's scope. |

`DIAG:POKE`, `DIAG:OFINIT` and `DIAG:OFCLR` change internal state. Do not send
them to an instrument you are not prepared to have recalibrated or repaired.

### Commands used by the web interface

The browser applet `DM344XXA.jar` sends these to the instrument:

- `DIAG:MON:STATE ON`, `DIAG:MON:STATE OFF`, `DIAG:MON:STATE?`
- `DIAG:LOCAL`, `DIAG:REMOTE?`
- `DIAG:WEB:LOG`, `DIAG:WEB:TIME`
- `DIAGnostic:APPlication:MODel?`

The remote front panel's server side (`WebControlDll.dll`) sends
`SYST:FPAN:KEYP <id>` to press a front-panel key. This is a second, separate key
interface from `DIAG:FP:KEYPress`.

### Framework diagnostics

The .NET application framework (`Agilent.Cdf.Api.ApplicationFramework.dll`)
defines a `DIAGnostic:CDF` branch of 28 nodes (`CLISt`, `LIST`, `SCALar`,
`FORMat`), with leaves named after data types (`BOOLean`, `INT16`, `UINT64`,
`DOUBle`, ...). Inferred: these exercise the command framework's data-type
handling, for testing.

## Internal mechanisms (named, not detailed)

These exist in `Torreys.dll`. Documenting how to drive them would cross into
option and security territory, so this file only records that they are there:

- A feature manager with a developer mode and a production-test mode. Enabling
  developer mode is refused while the instrument is secured, and the
  production-test mode requires developer mode.
- A secure-code subsystem: secure code entry, a secure count, and the
  calibration-secured state.
- A boot-ROM operation reachable through the internal peek/poke layer.

If a future task needs any of these, confirm the scope first.

## Hardware and web facts the manual does not give

- **Front panel.** One front-panel microcontroller, in one of two hardware
  variants: an NXP P89LPC932A1 (8051), or a TI MSP430FR2033. The ROM carries
  firmware for both (`AgtFPNxp.2.40.hex`, `AgtFPMsp430.3.15.hex`) and a config
  file for each. `AgilentFrontPanelSerial.dll` detects the variant at boot from
  a measured voltage ("Platform identified as MSP430-type based on %d mV"). Both
  talk over a serial port and share one key map.
- **Key map.** `AgtFrontPanelKeyMap.34460-66502.xml` lists 28 keys on an 8x4
  matrix, each with its row, column, label and Windows virtual-key code
  (`scanCode` is 0 throughout).
- **Web interface.** 36 `.asp` files. `InstrumentIO.asp` is the browser SCPI
  console; it posts to `/InstrumentIO/Execute` and `/InstrumentIO/DeviceClear`,
  which `LxiInstrumentIO.dll` serves as an ISAPI extension.
  `WebControlMethod.asp` is the AJAX back end of the remote front panel
  (`SetKey`, `ScpiInAsciiOutAscii`). `DataGet.asp`, `DataSend.asp` and
  `DataTransfer.asp` are unused templates from an oscilloscope product
  ("EXAMPLE" watermark, reference waveforms, wave generator, serial bus) and do
  nothing on the DMM.

## Secondary measurements

The firmware's state-dump list has `:SEC` nodes for exactly nine function
paths: `CAP`, `CURR`, `CURR:AC`, `FREQ`, `FRES`, `TEMP`, `VOLT`, `VOLT:AC` and
`VOLT:RAT`. These are documented in the manual (it also documents `PERiod` and
`RESistance` secondaries, which are not in this list). They are listed here only
because they are easy to miss.

## Method and limits

The firmware command list comes from readable strings in `Torreys.dll`
(`analysis/scpi_firmware.txt`, 148 paths after folding long-form spellings),
diffed against the manual by `tools/diff_manual.py`. The diff leaves 5 paths
(`analysis/scpi_not_in_manual.txt`): the two AC Mode commands and three DIAG
commands. The other commands above were found in the tools, applets and
assemblies that send them.

This is not the complete command tree. The full parser tree, with every node's
parameters, is built in code and needs further analysis of `Torreys.dll` and the
.NET parser framework to recover.
