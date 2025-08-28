# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals

import os
import sys
import zipfile
import shutil
import tempfile
import re
import traceback
import gettext

version = "3.5"

# Python 2/3 kompatible urllib
try:
    import urllib2 as urllib_request
except ImportError:
    import urllib.request as urllib_request

from Plugins.Plugin import PluginDescriptor
from Components.config import config, ConfigSubsection, ConfigYesNo
from Tools.Directories import resolveFilename, SCOPE_CONFIG
from Screens.MessageBox import MessageBox
from Screens.Standby import TryQuitMainloop

# ServiceScan kompatibel importieren
try:
    from Screens.ServiceScan import ServiceScan
except ImportError:
    from Components.ServiceScan import ServiceScan

from .SSULameDBParser import SSULameDBParser

PY2 = sys.version_info[0] == 2

# ===== Lokalisierung =====
PLUGIN_PATH = "/usr/lib/enigma2/python/Plugins/Extensions/speedyServiceScanUpdates/"
locale_dir = os.path.join(PLUGIN_PATH, "locale")
try:
    import locale
    lang = locale.getdefaultlocale()[0]
except Exception:
    lang = "en"

if os.path.isdir(locale_dir):
    gettext.bindtextdomain("speedyservicescanupdates", locale_dir)
    gettext.textdomain("speedyservicescanupdates")
    _ = gettext.gettext
else:
    _ = lambda s: s

# ===== Globale Variablen =====
baseServiceScan_execBegin = None
baseServiceScan_execEnd = None
preScanDB = None

LOGFILE = "/tmp/speedyServiceScanUpdates.log"
VERSION_FILE = os.path.join(PLUGIN_PATH, "version.txt")
GITHUB_VERSION_URL = "https://raw.githubusercontent.com/speedy005/speedyServiceScanUpdates/main/version.txt"
GITHUB_ZIP_URL = "https://github.com/speedy005/speedyServiceScanUpdates/archive/refs/heads/main.zip"

# ===== Logging =====
def log(msg):
    try:
        with open(LOGFILE, "a") as f:
            f.write(msg + "\n")
    except Exception:
        pass
    try:
        print(msg)
    except Exception:
        pass

def dictHasKey(dictionary, key):
    return key in dictionary if not PY2 else dictionary.has_key(key)

def safeClose(db):
    if hasattr(db, "close"):
        try:
            db.close()
        except Exception:
            pass

# ===== Python 2/3 kompatible copytree =====
def copytree_compat(src, dst):
    if not os.path.exists(dst):
        os.makedirs(dst)
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            copytree_compat(s, d)
        else:
            shutil.copy2(s, d)

# ===== ServiceScan Wrapper =====
def ServiceScan_execBegin(self):
    flags = "N/A"
    try:
        flags = self.scanList[self.run]["flags"]
    except Exception:
        pass
    log("[speedyServiceScanUpdates] ServiceScan_execBegin [%s]" % str(flags))

    global preScanDB
    try:
        if not preScanDB and (config.plugins.speedyservicescanupdates.add_new_tv_services.value or
                              config.plugins.speedyservicescanupdates.add_new_radio_services.value):
            preScanDB = SSULameDBParser(resolveFilename(SCOPE_CONFIG) + "/lamedb")
    except Exception as e:
        log("[speedyServiceScanUpdates] Fehler beim Laden preScanDB: %s" % e)

    try:
        if baseServiceScan_execBegin:
            baseServiceScan_execBegin(self)
    except Exception as e:
        log("[speedyServiceScanUpdates] Fehler beim Aufruf baseServiceScan_execBegin: %s" % e)

def ServiceScan_execEnd(self, onClose=True):
    flags = "N/A"
    try:
        flags = self.scanList[self.run]["flags"]
    except Exception:
        pass

    state_val = getattr(self, "state", -1)
    log("[speedyServiceScanUpdates] ServiceScan_execEnd (%d) [%s]" % (state_val, str(flags)))

    try:
        if getattr(self, "state", None) == getattr(self, "DONE", None):
            if config.plugins.speedyservicescanupdates.add_new_tv_services.value or \
               config.plugins.speedyservicescanupdates.add_new_radio_services.value:

                postScanDB = SSULameDBParser(resolveFilename(SCOPE_CONFIG) + "/lamedb")
                postScanServices = postScanDB.getServices()
                safeClose(postScanDB)

                global preScanDB
                if preScanDB:
                    preScanServices = preScanDB.getServices()
                    newTVServices = []
                    newRadioServices = []

                    for service_ref in postScanServices.keys():
                        if not dictHasKey(preScanServices, service_ref):
                            if SSULameDBParser.isVideoService(service_ref):
                                newTVServices.append(service_ref)
                            elif SSULameDBParser.isRadioService(service_ref):
                                newRadioServices.append(service_ref)

                    from .SSUBouquetHandler import SSUBouquetHandler
                    bh = SSUBouquetHandler()

                    def _apply(side, items):
                        if not items:
                            return
                        bh.addToIndexBouquet(side)
                        if config.plugins.speedyservicescanupdates.clear_bouquet.value:
                            bh.createSSUBouquet(items, side)
                        else:
                            if bh.doesSSUBouquetFileExists(side):
                                bh.appendToSSUBouquet(items, side)
                            else:
                                bh.createSSUBouquet(items, side)

                    if newTVServices and config.plugins.speedyservicescanupdates.add_new_tv_services.value:
                        _apply("tv", newTVServices)
                    if newRadioServices and config.plugins.speedyservicescanupdates.add_new_radio_services.value:
                        _apply("radio", newRadioServices)

                    try:
                        bh.reloadBouquets()
                    except Exception:
                        pass
                    preScanDB = None
    except Exception as e:
        log("[speedyServiceScanUpdates] Fehler in ServiceScan_execEnd: %s" % e)

    try:
        if baseServiceScan_execEnd:
            baseServiceScan_execEnd(self)
    except Exception as e:
        log("[speedyServiceScanUpdates] Fehler beim Aufruf baseServiceScan_execEnd: %s" % e)

# ===== Update-Funktionen =====
def get_current_version():
    try:
        with open(VERSION_FILE, 'r') as f:
            ver = f.read().strip()
            log("[speedyServiceScanUpdates] Lokale Version: %s" % ver)
            return ver
    except Exception as e:
        log("[speedyServiceScanUpdates] Fehler beim Lesen der lokalen Version: %s" % e)
        return "0.0"

def parse_version(version):
    if not version:
        return (0, 0, 0)
    try:
        v = version.strip().lower()
        if v.startswith("v"):
            v = v[1:]
        parts = re.findall(r"\d+", v)
        while len(parts) < 3:
            parts.append("0")
        return tuple(map(int, parts[:3]))
    except Exception as e:
        log("[speedyServiceScanUpdates] Fehler beim Parsen der Version '%s': %s" % (version, e))
        return (0, 0, 0)

def get_remote_version():
    try:
        response = urllib_request.urlopen(GITHUB_VERSION_URL).read()
        if not PY2:
            response = response.decode("utf-8")
        remote_ver = response.strip().split()[0]
        log("[speedyServiceScanUpdates] Remote-Version vom GitHub: %s" % remote_ver)
        return remote_ver
    except Exception as e:
        log("[speedyServiceScanUpdates] Fehler beim Abrufen der Remote-Version: %s" % e)
        return None

def download_and_install_update(session):
    tmp_dir = None
    try:
        tmp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(tmp_dir, "plugin_update.zip")

        log("[speedyServiceScanUpdates] " + _("Lade Update herunter..."))
        req = urllib_request.urlopen(GITHUB_ZIP_URL)
        with open(zip_path, "wb") as f:
            f.write(req.read())
        log("[speedyServiceScanUpdates] " + _("Download abgeschlossen: %s") % zip_path)

        log("[speedyServiceScanUpdates] " + _("Entpacke Update..."))
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(tmp_dir)

        extracted_root = None
        for name in os.listdir(tmp_dir):
            candidate = os.path.join(tmp_dir, name,
                                     "usr", "lib", "enigma2", "python", "Plugins", "Extensions",
                                     "speedyServiceScanUpdates")
            if os.path.exists(candidate):
                extracted_root = candidate
                break

        if not extracted_root or not os.path.exists(extracted_root):
            raise Exception(_("Entpacktes Plugin-Verzeichnis nicht gefunden!"))

        log("[speedyServiceScanUpdates] " + _("Kopiere Dateien nach: %s") % PLUGIN_PATH)

        for item in os.listdir(extracted_root):
            src_path = os.path.join(extracted_root, item)
            dest_path = os.path.join(PLUGIN_PATH, item)
            if os.path.isdir(src_path):
                copytree_compat(src_path, dest_path)
            else:
                shutil.copy2(src_path, dest_path)

        remote_version = get_remote_version()
        if remote_version:
            try:
                with open(VERSION_FILE, "w") as vf:
                    vf.write(remote_version + "\n")
                log("[speedyServiceScanUpdates] " + _("Lokale version.txt aktualisiert auf %s") % remote_version)
            except Exception as e:
                log("[speedyServiceScanUpdates] " + _("Konnte version.txt nicht schreiben: %s") % e)

        log("[speedyServiceScanUpdates] " + _("Update erfolgreich installiert!"))

        def restartGUI(answer):
            try:
                if answer:
                    log("[speedyServiceScanUpdates] " + _("Starte GUI neu..."))
                    session.open(TryQuitMainloop, 3)
                else:
                    log("[speedyServiceScanUpdates] " + _("Benutzer möchte GUI nicht neustarten."))
            except Exception as e:
                log("[speedyServiceScanUpdates] " + _("Fehler beim Neustart-Aufruf: %s") % e)

        try:
            session.openWithCallback(
                restartGUI, MessageBox,
                _("Update erfolgreich installiert!\nSoll die GUI jetzt neu gestartet werden?"),
                MessageBox.TYPE_YESNO
            )
        except Exception as e:
            log("[speedyServiceScanUpdates] " + _("Konnte Restart-MessageBox nicht öffnen: %s") % e)

    except Exception as e:
        log("[speedyServiceScanUpdates] " + _("Fehler beim Update: %s") % e)
        traceback.print_exc()
        try:
            session.open(MessageBox, _("Fehler beim Update:\n%s") % str(e), MessageBox.TYPE_ERROR)
        except Exception:
            pass
    finally:
        if tmp_dir:
            try:
                shutil.rmtree(tmp_dir, ignore_errors=True)
            except Exception:
                pass

# ===== Autostart Hook =====
def autostart(reason, **kwargs):
    if reason == 0 and "session" in kwargs:
        global baseServiceScan_execBegin, baseServiceScan_execEnd
        session = kwargs["session"]

        if baseServiceScan_execBegin is None:
            baseServiceScan_execBegin = ServiceScan.execBegin
        ServiceScan.execBegin = ServiceScan_execBegin

        if baseServiceScan_execEnd is None:
            baseServiceScan_execEnd = ServiceScan.execEnd
        ServiceScan.execEnd = ServiceScan_execEnd

        log("[speedyServiceScanUpdates] " + _("Autostart: ServiceScan Wrapper aktiv."))

# ===== Menü & Setup =====
def precheck_update_and_open(session, **kwargs):
    from .SSUSetupScreen import SSUSetupScreen

    def open_plugin():
        try:
            session.open(SSUSetupScreen)
        except Exception as e:
            log("[speedyServiceScanUpdates] " + _("Fehler beim Öffnen des SetupScreens: %s") % e)

    try:
        current_version = get_current_version()
        remote_version = get_remote_version()

        if remote_version and parse_version(remote_version) > parse_version(current_version):
            def callback(choice):
                if choice:
                    log("[speedyServiceScanUpdates] " + _("Benutzer bestätigt Update → starte Download"))
                    download_and_install_update(session)
                else:
                    log("[speedyServiceScanUpdates] " + _("Benutzer hat Update abgelehnt."))
                    open_plugin()

            session.openWithCallback(
                callback, MessageBox,
                _("Eine neue Version %s ist verfügbar.\nMöchten Sie das Update installieren?") % remote_version,
                MessageBox.TYPE_YESNO
            )
        else:
            open_plugin()

    except Exception as e:
        log("[speedyServiceScanUpdates] " + _("Fehler bei Updateprüfung: %s") % e)
        open_plugin()

def SSUMenuItem(menuid, **kwargs):
    if menuid == "scan":
        return [(_("speedy ServiceScanUpdates Setup"), precheck_update_and_open, "servicescanupdates", None)]
    return []

def menu(menuid, **kwargs):
    if menuid == "mainmenu":
        return [(_("speedyServiceScanUpdates") + " " + _("Setup"), precheck_update_and_open,
                 "speedyservicescanupdates_mainmenu", 50)]
    return []

# ===== Plugin Descriptor =====
def Plugins(**kwargs):
    # Konfiguration hinzufügen
    if not hasattr(config.plugins, "speedyservicescanupdates"):
        config.plugins.speedyservicescanupdates = ConfigSubsection()
        config.plugins.speedyservicescanupdates.add_new_tv_services = ConfigYesNo(default=True)
        config.plugins.speedyservicescanupdates.add_new_radio_services = ConfigYesNo(default=True)
        config.plugins.speedyservicescanupdates.clear_bouquet = ConfigYesNo(default=False)

    return [
        PluginDescriptor(where=[PluginDescriptor.WHERE_SESSIONSTART, PluginDescriptor.WHERE_AUTOSTART],
                         fnc=autostart),
        PluginDescriptor(name=_("speedy ServiceScanUpdates Setup"),
                         description=_("Updates during service scan"),
                         where=PluginDescriptor.WHERE_PLUGINMENU,
                         icon="plugin.png",
                         fnc=precheck_update_and_open),
        PluginDescriptor(name=_("speedy ServiceScanUpdates Setup"),
                         description=_("Updates during service scan"),
                         where=PluginDescriptor.WHERE_EXTENSIONSMENU,
                         icon="plugin.png",
                         fnc=precheck_update_and_open),
        PluginDescriptor(where=PluginDescriptor.WHERE_MENU, fnc=menu),
        PluginDescriptor(where=PluginDescriptor.WHERE_MENU, fnc=SSUMenuItem)
    ]
