# -*- coding: utf-8 -*-
import polib
from deep_translator import GoogleTranslator
from pathlib import Path

# --- Konfiguration ---
source_root = r"C:\speedyServiceScanUpdates\locale\de"  # Deutsch als Ausgang
languages = {
    "en": "English",
    "tr": "Turkish",
    "es": "Spanish",
    "da": "Danish",
    "ar": "Arabic"
}

# Alle .po-Dateien unter Deutsch rekursiv suchen
po_files = list(Path(source_root).rglob("*.po"))
if not po_files:
    raise FileNotFoundError(f"Keine .po-Dateien gefunden in {source_root}")

# Translator vorbereiten
translator = GoogleTranslator(source='de')  # Deutsch als Ausgangssprache

for po_path in po_files:
    po = polib.pofile(po_path)
    relative_subpath = po_path.relative_to(source_root).parent

    for lang_code, lang_name in languages.items():
        target_path = Path(source_root).parent / lang_code / relative_subpath
        target_path.mkdir(parents=True, exist_ok=True)

        translated_po = polib.POFile()
        translated_po.metadata = po.metadata.copy()

        print(f"Übersetze {po_path} nach {lang_name}...")

        for entry in po:
            try:
                translated_text = translator.translate(entry.msgid, target=lang_code)
            except Exception as e:
                print(f"Fehler bei Übersetzung von '{entry.msgid}': {e}")
                translated_text = entry.msgid  # Fallback: Originaltext

            # msgid bleibt Deutsch, msgstr wird übersetzt
            translated_entry = polib.POEntry(
                msgid=entry.msgid,
                msgstr=translated_text,
                occurrences=entry.occurrences,  # Pfade zu den Python-Dateien bleiben erhalten
                flags=entry.flags,
                comment=entry.comment,
                tcomment=entry.tcomment,
                previous_msgctxt=entry.previous_msgctxt,
                previous_msgid=entry.previous_msgid,
                previous_msgid_plural=entry.previous_msgid_plural
            )

            translated_po.append(translated_entry)

        # Speicherpfade für .po und .mo
        po_file_path = target_path / po_path.name
        mo_file_path = target_path / po_path.name.replace(".po", ".mo")
        translated_po.save(po_file_path)
        translated_po.save_as_mofile(mo_file_path)

        print(f"{lang_name} fertig: {po_file_path} / {mo_file_path}")

print("Alle Übersetzungen abgeschlossen!")
