# -*- coding: utf-8 -*-
from __future__ import print_function, division, unicode_literals
import os
import shutil
import zipfile
import io
import sys

try:
    import requests
except ImportError:
    requests = None

# --- Plugin-Pfad dynamisch ermitteln ---
plugin_path = None
for base in (
    "/usr/lib/enigma2/python/Plugins/Extensions",
    "/usr/lib/enigma2/python/Plugins/SystemPlugins"
):
    possible = os.path.join(base, "speedyServiceScanUpdates")
    if os.path.isdir(possible):
        plugin_path = possible
        break

# --- Enigma2 imports ---
from enigma import ePixmap, getDesktop, eTimer
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.Standby import TryQuitMainloop
from Components.ConfigList import ConfigListScreen
from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.Label import Label
from Components.ProgressBar import ProgressBar
from Components.config import config, ConfigSubsection, ConfigYesNo, getConfigListEntry
from Plugins.Plugin import PluginDescriptor
from Tools.Directories import resolveFilename, SCOPE_CONFIG

from . import _

# ===== Constants / Paths =====
UPDATE_URL = "https://github.com/speedy005/speedyServiceScanUpdates/archive/refs/heads/main.zip"
DOWNLOAD_PATH = "/tmp/ServiceScanUpdates-main.zip"
EXTRACT_DIR = "/tmp/ServiceScanUpdates"
TARGET_DIR = "/usr/lib/enigma2/python/Plugins/Extensions/speedyServiceScanUpdates"

# ===== Config =====
config.plugins.speedyservicescanupdates = ConfigSubsection()
config.plugins.speedyservicescanupdates.add_new_tv_services = ConfigYesNo(default=True)
config.plugins.speedyservicescanupdates.add_new_radio_services = ConfigYesNo(default=True)
config.plugins.speedyservicescanupdates.clear_bouquet = ConfigYesNo(default=False)

# ===== Version =====
def read_version():
    if not plugin_path:
        return u"Unknown version"
    vf = os.path.join(plugin_path, "version.txt")
    try:
        with io.open(vf, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return u"Unknown version"

version = read_version()

# ===== Utility =====
def _safe_msg(session, text, mtype=MessageBox.TYPE_INFO, timeout=5):
    try:
        session.open(MessageBox, text, type=mtype, timeout=timeout)
    except Exception:
        pass

# ===== ServiceScan Import =====
ServiceScan = None
try:
    from Screens.ServiceScan import ServiceScan
except ImportError:
    try:
        from Plugins.SystemPlugins.ServiceScan.plugin import ServiceScan
    except ImportError:
        pass

# ===== SSUUpdateScreen =====
class SSUUpdateScreen(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        desktop = getDesktop(0)
        width = desktop.size().width()

        # Skin abhängig von der Auflösung setzen
        if width >= 1920:
            self.skin = u"""<screen name="SSUUpdateScreen" position="center,170" size="1200,820" title="speedy Service Scan Updates">
                <widget name="progress" position="10,100" size="1180,50" />
                <widget name="status" position="12,160" size="1180,250" font="Regular;30" valign="center" halign="center" zPosition="1" />
                <widget name="progresstext" position="12,415" size="1180,350" font="Regular;30" valign="center" halign="center" />
                <widget name="key_red" position="3,4" size="295,70" font="Regular;30" halign="center" valign="center" />
                <widget name="key_green" foregroundColor="green" position="305,3" size="300,70" font="Regular;30" halign="center" valign="center" />
                <widget name="key_yellow" foregroundColor="yellow" position="609,3" size="300,70" font="Regular;30" halign="center" valign="center" />
                <widget name="key_blue" foregroundColor="blue" position="917,4" size="295,70" font="Regular;30" halign="center" valign="center" />
                <widget name="version" position="488,769" size="200,30" font="Regular;30" valign="center" halign="center" zPosition="1" />
                <eLabel text="HELP" position="1110,753" size="80,35" backgroundColor="#777777" valign="center" halign="center" font="Regular;24" zPosition="5" />
                <ePixmap pixmap="skin_default/buttons/vkey_exit.png" position="1041,761" size="35,25" scale="stretch" alphatest="on" zPosition="6" />
                <ePixmap pixmap="skin_default/buttons/blue.png" position="909,5" size="5,70" scale="stretch" alphatest="on" zPosition="1" />
                <ePixmap pixmap="skin_default/buttons/yellow.png" position="601,4" size="5,70" scale="stretch" alphatest="on" zPosition="1" />
                <ePixmap pixmap="skin_default/buttons/green.png" position="300,5" size="5,70" scale="stretch" alphatest="on" zPosition="1" />
                <ePixmap pixmap="skin_default/buttons/red.png" position="5,5" size="5,70" scale="stretch" alphatest="on" zPosition="1" />
            </screen>"""
        else:
            self.skin = u"""<screen name="SSUUpdateScreen" position="410,170" size="1100,820" title="speedy Service Scan Updates">
                <widget name="progress" position="10,100" size="1050,50" />
                <widget name="status" position="10,160" size="1050,200" font="Regular;30" valign="center" halign="center" />
                <widget name="progresstext" position="11,373" size="1050,297" font="Regular;30" valign="center" halign="center" />
                <widget name="key_red" position="13,2" size="250,70" font="Regular;30" halign="center" valign="center" />
                <widget name="key_green" foregroundColor="green" position="277,3" size="250,70" font="Regular;30" halign="center" valign="center" />
                <widget name="key_yellow" foregroundColor="yellow" position="538,4" size="250,70" font="Regular;30" halign="center" valign="center" />
                <widget name="key_blue" position="798,5" foregroundColor="blue" size="250,70" font="Regular;30" halign="center" valign="center" />
                <widget name="version" position="364,752" size="300,50" font="Regular;30" valign="center" halign="center" />
                <eLabel text="HELP" position="930,761" size="80,35" backgroundColor="#777777" valign="center" halign="center" font="Regular;24" zPosition="5" />
                <ePixmap pixmap="skin_default/buttons/vkey_exit.png" position="841,761" size="35,25" scale="stretch" alphatest="on" zPosition="6" />
                <ePixmap pixmap="skin_default/buttons/blue.png" position="791,5" size="5,70" scale="stretch" alphatest="on" />
                <ePixmap pixmap="skin_default/buttons/yellow.png" position="529,2" size="5,70" scale="stretch" alphatest="on" />
                <ePixmap pixmap="skin_default/buttons/green.png" position="269,2" size="5,70" scale="stretch" alphatest="on" />
                <ePixmap pixmap="skin_default/buttons/red.png" position="5,5" size="5,70" scale="stretch" alphatest="on" />
            </screen>"""

        # GUI-Komponenten initialisieren
        self['status'] = Label(_("Bereit"))
        self['progress'] = ProgressBar()
        self['progresstext'] = Label("")
        self['key_red'] = Button(_("Beenden"))
        self['key_green'] = Button(_("Start"))
        self['key_yellow'] = Button(_("Abbrechen"))
        self['key_blue'] = Button(_("Update prüfen"))
        self['version'] = Label(version)

        # Aktionen definieren
        self['actions'] = ActionMap(['ColorActions', 'OkCancelActions'], {
            'red': self.exit,
            'green': self.start_update,
            'yellow': self.cancel,
            'blue': self.check_update,
            'ok': self.start_update,
            'cancel': self.exit
        }, -1)

        self.download_progress = 0
        self.timer = eTimer()
        self.timer.callback.append(self._update_gui)
        self.timer.start(100, True)

    # --- GUI aktualisieren ---
    def _update_gui(self):
        self['progress'].setValue(min(self.download_progress, 100))
        self['progresstext'].setText(u"{}%".format(min(self.download_progress, 100)))

    def exit(self):
        self.close()

    # --- Update abschließen ---
    def _finish_update(self):
        try:
            update_folder = os.path.join(EXTRACT_DIR, "speedyServiceScanUpdates-main", "speedyServiceScanUpdates")
            if not os.path.isdir(update_folder):
                self['status'].setText(_("Fehler: Ordner speedyServiceScanUpdates nicht gefunden."))
                return

            if not os.path.isdir(TARGET_DIR):
                os.makedirs(TARGET_DIR)

            # Dateien kopieren (Python2/3 kompatibel)
            for item in os.listdir(update_folder):
                s = os.path.join(update_folder, item)
                d = os.path.join(TARGET_DIR, item)
                if os.path.isdir(s):
                    if os.path.exists(d):
                        shutil.rmtree(d)
                    shutil.copytree(s, d)
                else:
                    shutil.copy2(s, d)

            self['status'].setText(_("Update erfolgreich abgeschlossen."))
            self.session.openWithCallback(
                self.restartGUI,
                MessageBox,
                _("Update abgeschlossen. GUI neu starten?"),
                MessageBox.TYPE_YESNO
            )

        except Exception as e:
            print("Fehler beim Abschluss des Updates:", str(e))
            self['status'].setText(_("Update konnte nicht abgeschlossen werden."))

    def check_update(self):
        if not requests:
            self['status'].setText(_("Requests-Modul fehlt"))
            return
        self['status'].setText(_("Prüfe auf Updates..."))
        try:
            r = requests.get("https://raw.githubusercontent.com/speedy005/speedyServiceScanUpdates/main/version.txt", timeout=10)
            if r.status_code == 200:
                remote_version = r.text.strip()
                if remote_version > version:
                    self['status'].setText(_("Update verfügbar"))
                else:
                    self['status'].setText(_("Kein Update verfügbar"))
            else:
                self['status'].setText(_("Kein Update verfügbar"))
        except Exception as e:
            print("Fehler beim Update-Check:", str(e))
            self['status'].setText(_("Update-Check fehlgeschlagen."))

    def start_update(self):
        if not requests:
            self['status'].setText(_("Requests-Modul fehlt"))
            return
        self['status'].setText(_("Update wird heruntergeladen..."))
        try:
            r = requests.get(UPDATE_URL, stream=True, timeout=20)
            if r.status_code == 200:
                total_size = int(r.headers.get('Content-Length', 0))
                self.download_progress = 0
                with open(DOWNLOAD_PATH, 'wb') as f:
                    for data in r.iter_content(chunk_size=1024):
                        if data:
                            f.write(data)
                            self.download_progress += len(data) * 100 // max(total_size, 1)
                            self._update_gui()
                with zipfile.ZipFile(DOWNLOAD_PATH, 'r') as zip_ref:
                    zip_ref.extractall(EXTRACT_DIR)
                self._finish_update()
            else:
                self['status'].setText(_("Download fehlgeschlagen"))
        except Exception as e:
            print("Fehler beim Download:", str(e))
            self['status'].setText(_("Download fehlgeschlagen"))

    def cancel(self):
        self['status'].setText(_("Update abgebrochen"))
        self.close()

    def restartGUI(self, answer):
        if answer:
            self.session.open(TryQuitMainloop, 3)
        else:
            self.close()
