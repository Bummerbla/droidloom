#!/usr/bin/env sh
set -eu

SOURCE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
DATA_HOME=${XDG_DATA_HOME:-"$HOME/.local/share"}
APP_DIR="$DATA_HOME/droidloom"
APPLICATIONS_DIR="$DATA_HOME/applications"
ICONS_DIR="$DATA_HOME/icons/hicolor/scalable/apps"

if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 is required. Install Python 3 and Tkinter, then run this installer again."
    exit 1
fi
if ! python3 -c 'import tkinter' >/dev/null 2>&1; then
    echo "Tkinter is missing. Install your distribution's Python Tk package (often python3-tk), then retry."
    exit 1
fi

mkdir -p "$APP_DIR" "$APPLICATIONS_DIR" "$ICONS_DIR"
cp "$SOURCE_DIR/launcher.py" "$APP_DIR/launcher.py"
cp "$SOURCE_DIR/droidloom.svg" "$ICONS_DIR/droidloom.svg"
cp "$SOURCE_DIR/droidloom.svg" "$APP_DIR/droidloom.svg"
cp "$SOURCE_DIR/README.md" "$APP_DIR/README.md"
for user_file in launcher_settings.json app_names.json; do
    if [ -f "$SOURCE_DIR/$user_file" ] && [ ! -f "$APP_DIR/$user_file" ]; then
        cp "$SOURCE_DIR/$user_file" "$APP_DIR/$user_file"
    fi
done

cat > "$APPLICATIONS_DIR/droidloom.desktop" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=DroidLoom
Comment=Open Android apps on your computer
Exec=python3 "$APP_DIR/launcher.py"
Icon=droidloom
Terminal=false
Categories=Utility;
StartupNotify=true
EOF
chmod 755 "$APPLICATIONS_DIR/droidloom.desktop"

if command -v xdg-user-dir >/dev/null 2>&1; then
    DESKTOP_DIR=$(xdg-user-dir DESKTOP 2>/dev/null || printf '%s' "$HOME/Desktop")
else
    DESKTOP_DIR="$HOME/Desktop"
fi
if [ -d "$DESKTOP_DIR" ]; then
    cp "$APPLICATIONS_DIR/droidloom.desktop" "$DESKTOP_DIR/DroidLoom.desktop"
    chmod 755 "$DESKTOP_DIR/DroidLoom.desktop"
    if command -v gio >/dev/null 2>&1; then
        gio set "$DESKTOP_DIR/DroidLoom.desktop" metadata::trusted true 2>/dev/null || true
    fi
fi

echo "DroidLoom is installed in your applications menu."
echo "SCRCPY and ADB must be installed or selected once in the app with Tools…"
