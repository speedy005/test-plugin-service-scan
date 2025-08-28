# -*- coding: utf-8 -*-
import os
import subprocess
import shutil

# --- Konfiguration ---
LOCAL_DIR = r"C:\speedyServiceScanUpdates"  # Lokaler Ordner mit den .py-Dateien
BOX_BASE_PATH = "/usr/lib/enigma2/python/Plugins/Extensions/speedyServiceScanUpdates"
OUTPUT_DIR = os.path.join(LOCAL_DIR, "locale")
PLUGIN_NAME = "speedyServiceScanUpdates"
LANGUAGES = ["de", "en", "tr", "es", "da", "ar"]

# gettext-Tools
GETTEXT_BIN = r"C:\gettext\bin"  # ggf. anpassen
XGETTEXT = shutil.which("xgettext") or os.path.join(GETTEXT_BIN, "xgettext.exe")
MSGINIT  = shutil.which("msginit")  or os.path.join(GETTEXT_BIN, "msginit.exe")
MSGFMT   = shutil.which("msgfmt")   or os.path.join(GETTEXT_BIN, "msgfmt.exe")

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

# --- Alle .py-Dateien sammeln ---
py_files = []
for root, _, files in os.walk(LOCAL_DIR):
    for f in files:
        if f.endswith(".py"):
            py_files.append(os.path.join(root, f))

if not py_files:
    print("⚠️ Keine .py-Dateien gefunden!")
    exit(1)

ensure_dir(OUTPUT_DIR)
pot_file = os.path.join(OUTPUT_DIR, f"{PLUGIN_NAME}.pot")

# --- 1) .pot-Datei erzeugen (alle .py zusammen) ---
relative_paths = [os.path.relpath(f, LOCAL_DIR).replace("\\", "/") for f in py_files]

cmd = [XGETTEXT, "--language=Python", "--keyword=_", "--output", pot_file, "--from-code=utf-8"] + relative_paths
result = subprocess.run(cmd, cwd=LOCAL_DIR, capture_output=True, text=True)
if result.returncode != 0:
    print(f"❌ Fehler bei xgettext:\n{result.stderr}")
    exit(1)

# --- 2) Pfade in .pot auf Box-Pfad anpassen ---
with open(pot_file, "r", encoding="utf-8") as f:
    content = f.read()

for rel_path in relative_paths:
    virtual_path = f"{BOX_BASE_PATH}/{rel_path}"
    content = content.replace(rel_path, virtual_path)

with open(pot_file, "w", encoding="utf-8") as f:
    f.write(content)

print(f"✅ .pot erstellt: {pot_file}")

# --- 3) .po-Dateien für alle Sprachen erstellen ---
for lang in LANGUAGES:
    lang_dir = os.path.join(OUTPUT_DIR, lang, "LC_MESSAGES")
    ensure_dir(lang_dir)
    po_file = os.path.join(lang_dir, f"{PLUGIN_NAME}.po")

    print(f"✨ Erstelle/überschreibe {po_file}...")
    cmd = [MSGINIT, "--no-translator", "--locale", lang, "--input", pot_file, "--output-file", po_file]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Fehler bei {lang} (msginit):\n{result.stderr}")
    else:
        print(f"✅ {po_file} erstellt")

# --- 4) .mo-Dateien kompilieren ---
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
