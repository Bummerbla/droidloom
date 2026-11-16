# DroidLoom for Linux

DroidLoom is a local desktop launcher for opening Android apps on a Linux computer through ADB and SCRCPY. It uses a native Python/Tkinter interface and does not send phone data to a web service.

## Requirements

- Linux desktop environment.
- Python 3 with Tkinter.
- SCRCPY and ADB installed or their locations available to choose in DroidLoom.
- Android 10 or newer for SCRCPY's virtual display; audio forwarding requires Android 11 or newer.
- USB debugging enabled and authorized on the phone.

DroidLoom discovers Android devices through ADB and is not tied to a phone brand or model. Some manufacturers require extra USB drivers or debugging permissions. iPhones are not supported.

## Install

Install Python 3, Tkinter, and SCRCPY using your distribution's package manager or the [official SCRCPY Linux guide](https://github.com/Genymobile/scrcpy/blob/master/doc/linux.md). Then run from this folder:

```sh
sh install-linux.sh
```

The installer places DroidLoom in your local user data folder and adds it to the applications menu and desktop when available. If SCRCPY or ADB is not found, use **Tools…** in the app to select them.

## Connect and use

1. Enable Developer options and USB debugging on the Android phone.
2. Connect it by USB and approve the debugging prompt.
3. Open DroidLoom, choose the connected phone, and start a desktop display.
4. Apps are discovered at the same time; select one to open it.

## Features

- Resolution/DPI presets and a custom display size.
- Tablet/full-display or freeform app windows.
- Optional PC audio forwarding and phone screen-off behavior.
- Open app list with focus, maximize, and unfocus actions.
- Search, categories, editable app names, and locally drawn icon marks.

Preferences and renamed apps stay local in `launcher_settings.json` and `app_names.json`; those files are excluded from this repository.

## SCRCPY

See the [official SCRCPY project](https://github.com/Genymobile/scrcpy) for device requirements and downloads. Virtual display sizing is covered in the [virtual display guide](https://github.com/Genymobile/scrcpy/blob/master/doc/virtual-display.md), and audio support is covered in the [audio guide](https://github.com/Genymobile/scrcpy/blob/master/doc/audio.md).
