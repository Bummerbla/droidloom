# DroidLoom

DroidLoom is a local desktop launcher for opening Android apps on a computer using ADB and SCRCPY. It has a native Python/Tkinter interface and does not send phone data to a service.

## Contributors

- **Bummerbla** — project owner and maintainer.
- **ChatGPT (OpenAI)** — major development contributor, including cross-platform launcher work, interface improvements, packaging, and documentation.

## Supported computers

- Windows 10 or newer.
- Linux desktop environments with Python 3 and Tkinter.
- macOS is not supported.

The app is Python standard-library only; there are no pip packages to install. The Linux desktop shortcut uses wmctrl to bring SCRCPY to the front when available. Windows uses its native window controls.

## Android compatibility

The launcher is not tied to a phone brand or model. It discovers Android devices through ADB and gets app names and packages from the connected phone.

- The SCRCPY virtual desktop requires Android 10 or newer. SCRCPY screen mirroring itself supports Android 5 or newer, but older Android versions cannot create this launcher's separate virtual desktop.
- PC audio forwarding requires Android 11 or newer.
- USB debugging must be enabled and authorized on the phone. On Windows, some phones also need their manufacturer's USB driver.
- A few manufacturers restrict secondary displays or input injection. Such restrictions vary by model and OS version.
- iPhones are not supported; SCRCPY uses Android's ADB interface.

See the official [SCRCPY project](https://github.com/Genymobile/scrcpy) for device requirements and downloads.

## Install on Linux

The installation is a few steps and does not require Python programming or pip packages. Install SCRCPY first; it supplies or works with ADB. On Debian or Ubuntu, install Python and Tkinter from the Software app or with sudo apt install python3 python3-tk. Other Linux versions use their own software app and package names. Follow the SCRCPY project's [official Linux installation guide](https://github.com/Genymobile/scrcpy/blob/master/doc/linux.md) to install SCRCPY.

1. Download the DroidLoom files from GitHub (green **Code** button → **Download ZIP**) and extract the ZIP file.
2. Open the extracted droidloom folder.
3. Open a terminal in that folder and run:

sh install-linux.sh

The installer checks Python and Tkinter, copies DroidLoom into your user account, and adds it to the applications menu and desktop when available. It does not need administrator access. Open **DroidLoom** from the applications menu when it finishes. If SCRCPY or ADB is not found automatically, use **Tools…** once to point DroidLoom to them.

For the first phone connection, enable **Developer options** and **USB debugging** on the phone, connect it over USB, and approve the prompt. Then select the device in DroidLoom.

## Install on Windows

Install Python 3 from [python.org](https://www.python.org/downloads/windows/) with Tcl/Tk support. Install SCRCPY using the [official Windows guide](https://github.com/Genymobile/scrcpy/blob/master/doc/windows.md); the official WinGet package is Genymobile.scrcpy.

Open PowerShell in the DroidLoom folder and run:

powershell -ExecutionPolicy Bypass -File .\install-windows.ps1

The installer adds shortcuts to the desktop and Start menu. If SCRCPY or ADB is not found automatically, use **Tools…** to select scrcpy.exe and adb.exe.

## Connect and use

1. Enable Developer options and USB debugging on the Android phone.
2. Connect by USB and approve the debugging prompt.
3. Open **DroidLoom**, choose the connected phone, and start a desktop display.
4. Apps are discovered at the same time. Select one to open it.

SCRCPY and ADB can be found from PATH, from their shared folder beside the app, or selected using **Tools…**. Their paths are saved in local settings.

## Features

- Resolution and DPI presets, plus a custom size field.
- Tablet/full-display or freeform app windows.
- Optional PC audio forwarding and phone screen-off behavior.
- Open app list with focus, maximize, and unfocus actions.
- App search, categories, editable app names, and locally drawn icons.

Display preferences and renamed apps stay in local settings and are excluded from this repository.

## Credits and copyright

ChatGPT (OpenAI) is credited as a major development contributor. Copyright is held by Bummerbla; ChatGPT is not a copyright holder or legal person. The MIT license remains unchanged.

## SCRCPY notes

Virtual display sizing is documented in the [virtual display guide](https://github.com/Genymobile/scrcpy/blob/master/doc/virtual-display.md). Audio support is described in the [audio guide](https://github.com/Genymobile/scrcpy/blob/master/doc/audio.md). App-specific behavior remains controlled by Android and the app developer.
