# -*- coding: utf-8 -*-
import os
import subprocess
import shutil

# --- Konfiguration ---
PLUGIN_DIR = r"C:\speedyServiceScanUpdates"  # Ordner, wo die .py-Dateien liegen
PLUGIN_NAME = os.path.basename(PLUGIN_DIR)     # z. B. "MeinPlugin"
OUTPUT_DIR = os.path.join(PLUGIN_DIR, "locale")
POT_FILE = os.path.join(OUTPUT_DIR, f"{PLUGIN_NAME}.pot")
LANGUAGES = ["de", "en", "tr", "es", "da", "ar"]

# gettext-Tools
GETTEXT_BIN = r"C:\gettext\bin"  # ggf. anpassen
XGETTEXT = shutil.which("xgettext") or os.path.join(GETTEXT_BIN, "xgettext.exe")
MSGINIT  = shutil.which("msginit")  or os.path.join(GETTEXT_BIN, "msginit.exe")
MSGFMT   = shutil.which("msgfmt")   or os.path.join(GETTEXT_BIN, "msgfmt.exe")

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

# --- 1) .pot-Datei erzeugen ---
print("🔍 Erzeuge neue .pot-Datei aus allen .py...")
ensure_dir(OUTPUT_DIR)

# Alle .py-Dateien im Plugin-Verzeichnis sammeln
py_files = []
for root, _, files in os.walk(PLUGIN_DIR):
    for f in files:
        if f.endswith(".py"):
            py_files.append(os.path.join(root, f))

if py_files:
    cmd = [XGETTEXT, "--language=Python", "--keyword=_", "--output", POT_FILE] + py_files
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("❌ Fehler bei xgettext:\n", result.stderr)
        exit(1)
    else:
        print(f"✅ .pot erstellt: {POT_FILE}")
else:
    print("⚠️ Keine .py-Dateien gefunden!")
    exit(1)

# --- 2) .po-Dateien immer neu erstellen ---
for lang in LANGUAGES:
    lang_dir = os.path.join(OUTPUT_DIR, lang, "LC_MESSAGES")
    ensure_dir(lang_dir)

    po_file = os.path.join(lang_dir, f"{PLUGIN_NAME}.po")

    print(f"✨ Erstelle/überschreibe {po_file}...")
    cmd = [MSGINIT, "--no-translator", "--locale", lang, "--input", POT_FILE, "--output-file", po_file]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Fehler bei {lang} (msginit):\n{result.stderr}")
    else:
        print(f"✅ {po_file} erstellt")

# --- 3) .mo-Dateien kompilieren ---
for lang in LANGUAGES:
    lang_dir = os.path.join(OUTPUT_DIR, lang, "LC_MESSAGES")
    po_file = os.path.join(lang_dir, f"{PLUGIN_NAME}.po")
    mo_file = os.path.join(lang_dir, f"{PLUGIN_NAME}.mo")

    if os.path.exists(po_file):
        print(f"🛠️ Kompiliere {po_file} → {mo_file}...")
        cmd = [MSGFMT, po_file, "-o", mo_file]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Fehler bei {lang} (msgfmt):\n{result.stderr}")
        else:
            print(f"✅ .mo erstellt: {mo_file}")
    else:
        print(f"⚠️ PO-Datei fehlt: {po_file}")
