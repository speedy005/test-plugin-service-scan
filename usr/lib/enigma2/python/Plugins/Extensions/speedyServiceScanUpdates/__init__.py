# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals  # Für Py2 Unicode-Kompatibilität
from Components.config import config, ConfigSubsection, ConfigYesNo
from Components.Language import language
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, SCOPE_LANGUAGE
import os
import gettext
import sys

PluginLanguageDomain = "speedyServiceScanUpdates"

# Dynamisch den Pfad ermitteln (funktioniert für Extensions und SystemPlugins)
plugin_path = resolveFilename(SCOPE_PLUGINS, str("Extensions/" + PluginLanguageDomain + "/locale/"))
if not os.path.exists(plugin_path):
    plugin_path = resolveFilename(SCOPE_PLUGINS, str("SystemPlugins/" + PluginLanguageDomain + "/locale/"))

PluginLanguagePath = plugin_path


def isDreamOS():
    try:
        from enigma import eMediaDatabase
    except ImportError:
        return False
    else:
        return True


def localeInit():
    lang = language.getLanguage()[:2]

    # Py2/3 kompatibles Setzen der Umgebungsvariable
    if sys.version_info[0] < 3:
        os.environ["LANGUAGE"] = str(lang.encode("utf-8"))
    else:
        os.environ["LANGUAGE"] = str(lang)

    gettext.bindtextdomain("enigma2", resolveFilename(SCOPE_LANGUAGE))
    gettext.textdomain("enigma2")
    gettext.bindtextdomain(PluginLanguageDomain, PluginLanguagePath)


def _(txt):
    # Py2/3 Unicode-sicher
    if sys.version_info[0] < 3 and isinstance(txt, unicode):
        txt = txt.encode("utf-8")

    t = gettext.dgettext(PluginLanguageDomain, txt)
    if t == txt:
        t = gettext.gettext(txt)

    # Py2: Rückgabe als Unicode
    if sys.version_info[0] < 3:
        t = t.decode("utf-8") if isinstance(t, str) else t

    return t


# Direkt bei Pluginstart die Übersetzung initialisieren
localeInit()

# Callback nur registrieren, wenn es kein DreamOS ist
if not isDreamOS():
    language.addCallback(localeInit)


#######################################################
# Konfiguration initialisieren
config.plugins.speedyservicescanupdates = ConfigSubsection()
config.plugins.speedyservicescanupdates.add_new_tv_services = ConfigYesNo(default=True)
config.plugins.speedyservicescanupdates.add_new_radio_services = ConfigYesNo(default=True)
config.plugins.speedyservicescanupdates.clear_bouquet = ConfigYesNo(default=False)
