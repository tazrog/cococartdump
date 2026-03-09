# TRS-80 Color Computer Cartridge Dumper

This project is now a standalone CoCo cartridge dumper for an Arduino Mega 2560.

- The firmware only reads cartridge ROM data.
- Joystick support, quit/reset buttons, and XRoar bridge functions have been removed.
- The cartridge pin layout in the dumper firmware is unchanged.

## Files

- [`coco_cart_dumper.ino`](/home/tazrog/coco_cart_dumper/coco_cart_dumper.ino): Arduino Mega dumper firmware
- [`tools/capture_coco_dump.py`](/home/tazrog/coco_cart_dumper/tools/capture_coco_dump.py): Tkinter desktop dumper app

## Supported Cartridges

- Simple 8 KiB and 16 KiB ROM cartridges
- Read window starting at `0xC000`
- `/CTS` asserted on all reads
- `/SCS` asserted for the upper 8 KiB window

Bank-switched cartridges are not supported.

## Mega Pin Map

### Cartridge bus

- Mega `D22..D37` -> cartridge `A0..A15`
- Mega `D38..D45` <- cartridge `D0..D7`
- Mega `D46` -> cartridge `R/W`
- Mega `D47` -> cartridge `/CTS`
- Mega `D48` -> cartridge `/SCS`

Pins `D49`, `D50`, `D51`, `D52`, and `D53` are not used by the current dumper firmware.

## CoCo Cartridge Pin Layout

Connector numbering below follows the CoCo cartridge port numbering used in the technical reference. Confirm connector orientation before applying power.

### Power and ground

- CoCo pin `9` (`+5V`) -> Mega `5V`
- CoCo pin `34` (`GND`) -> Mega `GND`
- CoCo pin `35` (`GND`) -> Mega `GND`

### Data bus

- CoCo pin `10` (`D0`) -> Mega `D38`
- CoCo pin `11` (`D1`) -> Mega `D39`
- CoCo pin `12` (`D2`) -> Mega `D40`
- CoCo pin `13` (`D3`) -> Mega `D41`
- CoCo pin `14` (`D4`) -> Mega `D42`
- CoCo pin `15` (`D5`) -> Mega `D43`
- CoCo pin `16` (`D6`) -> Mega `D44`
- CoCo pin `17` (`D7`) -> Mega `D45`

### Address bus

- CoCo pin `19` (`A0`) -> Mega `D22`
- CoCo pin `20` (`A1`) -> Mega `D23`
- CoCo pin `21` (`A2`) -> Mega `D24`
- CoCo pin `22` (`A3`) -> Mega `D25`
- CoCo pin `23` (`A4`) -> Mega `D26`
- CoCo pin `24` (`A5`) -> Mega `D27`
- CoCo pin `25` (`A6`) -> Mega `D28`
- CoCo pin `26` (`A7`) -> Mega `D29`
- CoCo pin `27` (`A8`) -> Mega `D30`
- CoCo pin `28` (`A9`) -> Mega `D31`
- CoCo pin `29` (`A10`) -> Mega `D32`
- CoCo pin `30` (`A11`) -> Mega `D33`
- CoCo pin `31` (`A12`) -> Mega `D34`
- CoCo pin `37` (`A13`) -> Mega `D35`
- CoCo pin `38` (`A14`) -> Mega `D36`
- CoCo pin `39` (`A15`) -> Mega `D37`

### Control signals

- CoCo pin `18` (`R/W`) -> Mega `D46`
- CoCo pin `32` (`/CTS`) -> Mega `D47`
- CoCo pin `36` (`/SCS`) -> Mega `D48`

Other cartridge pins are not used by this dumper.

## Serial Protocol

Host to Mega:

- `D <start_hex> <size_hex>`: dump bytes from the cartridge window

Mega to host:

- `BEGIN <size_decimal>`
- raw payload bytes
- `END`

## Desktop Dumper App

The Tkinter dumper app is intended to run on either Windows or Linux.

- Windows: select the Mega as a `COM` port such as `COM3`
- Linux: select the Mega as a device such as `/dev/ttyACM0`

Install `pyserial` if it is not already available:

```bash
python3 -m pip install pyserial
```

On Windows, if `python3` is not available in `PATH`, use:

```bash
py -m pip install pyserial
```

Start the dumper window:

```bash
python3 tools/capture_coco_dump.py
```

On Windows, you can also start it with:

```bash
py tools\capture_coco_dump.py
```

In the window:

1. Select the Arduino Mega serial port.
2. Choose the folder to save the dump into.
3. Enter the cartridge name.
4. Leave size on `auto`, or select `2000` for 8 KiB or `4000` for 16 KiB.
5. Click `Dump Cartridge`.

The app saves the ROM as `<cart name>.ccc` in the selected folder.

## Notes

- Default baud rate is `115200`.
- Default start address is `C000`.
- `auto` captures 16 KiB first, then trims to 8 KiB if the upper half is mirrored or unconnected.
- The app refuses to save dumps that look electrically unconnected.
- The app uses standard Tkinter, so a normal Python install on Windows or Linux is usually enough.

## Standalone Executable Build

The desktop app can be packaged as a standalone executable with PyInstaller.

- Linux builds must be created on Linux.
- Windows builds must be created on Windows.
- Do not expect one OS to produce a runnable executable for the other.
- `scripts/coco.png` is the source application icon for both platforms.

Install build dependencies:

```bash
python3 -m pip install -r requirements-build.txt
```

If that still leaves `PyInstaller` unavailable, install into a virtual environment and build from there:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements-build.txt
./scripts/build_linux.sh
```

On Windows:

```bash
py -m pip install -r requirements-build.txt
```

### Build On Linux

```bash
./scripts/build_linux.sh
```

This creates:

- `dist/ccd`

### Install On Linux

```bash
./scripts/install_linux.sh
```

This installs:

- executable to `~/.local/bin/ccd`
- icon to `~/.local/share/icons/hicolor/256x256/apps/cococartdump.png`
- desktop launcher to `~/.local/share/applications/cococartdump.desktop`

### Build On Windows

```bat
scripts\build_windows.bat
```

This creates:

- `dist\ccd.exe`
- `scripts\coco.ico` generated from `scripts\coco.png`

### Install On Windows

```bat
scripts\install_windows.bat
```

This installs:

- executable to `%LocalAppData%\Programs\cococartdump\ccd.exe`
- icon to `%LocalAppData%\Programs\cococartdump\coco.ico`
- Start Menu shortcut named `cococartdump`

## Distribution Notes

- The generated executable already bundles Python and the app code.
- End users do not need to install Python to run the packaged executable.
- End users still need USB serial access permissions on Linux.
- On Linux, if the Arduino device is inaccessible, add the user to the appropriate serial-access group such as `dialout`.

## Troubleshooting

- If no cartridge is detected, verify connector orientation, ground, and `+5V`.
- If only the lower 8 KiB reads correctly, verify the `/SCS` path on Mega `D48`.
- If the dump is mostly `FF` or `00`, verify `/CTS`, data lines, and address wiring.
- If reads are unstable, increase `ADDRESS_SETUP_US` or `STROBE_SETTLE_US` in [`coco_cart_dumper.ino`](/home/tazrog/coco_cart_dumper/coco_cart_dumper.ino).
- If the app does not start on Linux, install your distro's `python3-tk` package.
