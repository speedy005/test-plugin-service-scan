# -*- coding: utf-8 -*-
import os
import polib
from deep_translator import GoogleTranslator
from pathlib import Path

# --- Konfiguration ---
source_root = r"C:\speedyServiceScanUpdates\locale"  # Wurzelverzeichnis für die Suche nach .po-Dateien
languages = {
    "en": "English",
    "tr": "Turkish",
    "es": "Spanish",
    "da": "Danish",
    "ar": "Arabic"
}

# --- Translator initialisieren ---
translator = GoogleTranslator(source='auto')

# Alle .po-Dateien rekursiv finden
po_files = list(Path(source_root).rglob("*.po"))

if not po_files:
    raise FileNotFoundError(f"Keine .po-Dateien gefunden in {source_root}")

for po_path in po_files:
    po = polib.pofile(po_path)

    # Berechne relativen Pfad vom Quellordner
    relative_path = po_path.relative_to(source_root)
    for lang_code, lang_name in languages.items():
        # Zielordner unter Beibehaltung der Struktur
        target_path = Path(source_root) / lang_code / relative_path.parent
        target_path.mkdir(parents=True, exist_ok=True)

        translated_po = polib.POFile()
        translated_po.metadata = po.metadata.copy()

        translation_cache = {}

        print(f"Übersetze {po_path} nach {lang_name}...")

        for entry in po:
            if entry.msgid not in translation_cache:
                try:
                    translation_cache[entry.msgid] = translator.translate(entry.msgid, target=lang_code)
                except Exception as e:
                    print(f"Fehler bei Übersetzung '{entry.msgid}': {e}")
                    translation_cache[entry.msgid] = entry.msgid

            translated_po.append(polib.POEntry(msgid=entry.msgid, msgstr=translation_cache[entry.msgid]))

        po_file_path = target_path / po_path.name
        mo_file_path = target_path / po_path.name.replace(".po", ".mo")
        translated_po.save(po_file_path)
        translated_po.save_as_mofile(mo_file_path)

        print(f"{lang_name} fertig: {po_file_path} / {mo_file_path}")

print("Alle Übersetzungen abgeschlossen!")
