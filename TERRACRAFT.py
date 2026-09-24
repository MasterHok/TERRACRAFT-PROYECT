import sys
import os
import json
import subprocess
import threading
import time
import shutil
import zipfile
import urllib.request
import urllib.error
from typing import List, Optional

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QLineEdit, QComboBox, QPushButton,
    QProgressBar, QFrame, QSlider, QTabWidget, QPlainTextEdit,
    QMessageBox, QFileDialog, QScrollArea, QSizePolicy,
    QListWidget, QListWidgetItem
)
from PySide6.QtCore import (
    Qt, QThread, Signal, QUrl, QObject, QTimer,
    QRunnable, QThreadPool, Slot, QSize
)
from PySide6.QtGui import (
    QIcon, QMovie, QPainter, QColor, QLinearGradient, QTextCursor, QPixmap,
    QDesktopServices
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

import minecraft_launcher_lib


# ============================================================
# CONSTANTES
# ============================================================
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
LAUNCHER_NAME = "TERRARIANOS LAUNCHER"
LAUNCHER_VERSION = "3.0"
LAUNCHER_AUTHOR = "Sailor_Rei_Zora_Covennant_Cock_Master_64."

# Tabla Java ↔ Minecraft (según la wiki oficial)
JAVA_BY_MC = {
    # Minecraft < 1.6 requiere Java 5
    # (No incluido por ser demasiado antiguo)
    
    # Minecraft ≥ 1.6 requiere Java 6
    "1.6": "6", "1.6.1": "6", "1.6.2": "6", "1.6.4": "6",
    
    # Minecraft ≥ 1.12 requiere Java 8
    "1.7": "8", "1.7.1": "8", "1.7.2": "8", "1.7.3": "8", "1.7.4": "8", "1.7.5": "8",
    "1.7.6": "8", "1.7.7": "8", "1.7.8": "8", "1.7.9": "8", "1.7.10": "8",
    "1.8": "8", "1.8.1": "8", "1.8.2": "8", "1.8.3": "8", "1.8.4": "8",
    "1.8.5": "8", "1.8.6": "8", "1.8.7": "8", "1.8.8": "8", "1.8.9": "8",
    "1.9": "8", "1.9.1": "8", "1.9.2": "8", "1.9.3": "8", "1.9.4": "8",
    "1.10": "8", "1.10.1": "8", "1.10.2": "8",
    "1.11": "8", "1.11.1": "8", "1.11.2": "8",
    "1.12": "8", "1.12.1": "8", "1.12.2": "8",
    "1.13": "8", "1.13.1": "8", "1.13.2": "8",
    "1.14": "8", "1.14.1": "8", "1.14.2": "8", "1.14.3": "8", "1.14.4": "8",
    "1.15": "8", "1.15.1": "8", "1.15.2": "8",
    "1.16": "8", "1.16.1": "8", "1.16.2": "8", "1.16.3": "8", "1.16.4": "8", "1.16.5": "8",
    
    # Minecraft ≥ 1.17 requiere Java 16
    "1.17": "16", "1.17.1": "16",
    
    # Minecraft ≥ 1.18 requiere Java 17
    "1.18": "17", "1.18.1": "17", "1.18.2": "17",
    "1.19": "17", "1.19.1": "17", "1.19.2": "17", "1.19.3": "17", "1.19.4": "17",
    "1.20": "17", "1.20.1": "17", "1.20.2": "17", "1.20.3": "17", "1.20.4": "17",
    
    # Minecraft ≥ 1.20.5 requiere Java 21
    "1.20.5": "21", "1.20.6": "21",
    "1.21": "21", "1.21.1": "21", "1.21.2": "21", "1.21.3": "21",
    "1.21.4": "21", "1.21.5": "21", "1.21.6": "21", "1.21.7": "21",
    "1.21.8": "21", "1.21.9": "21", "1.21.10": "21", "1.21.11": "21",
    
    # Minecraft ≥ 26.1 requiere Java 25
    "26.1": "25", "26.1.2": "25", "26.2": "25",
}

def get_required_java(mc_version: str) -> str:
    """
    Devuelve la versión de Java que necesita esa versión de Minecraft.
    Primero intenta la API de Purpur; si falla, usa la tabla hardcodeada.
    """
    try:
        data = http_get_json(f"https://api.purpurmc.org/v2/purpur/{mc_version}", timeout=6)
        java = data.get("javaVersion") or data.get("java", {}).get("version")
        if java:
            return str(java)
    except Exception:
        pass
    return JAVA_BY_MC.get(mc_version, "21")


# ============================================================
# RUTAS Y HTTP
# ============================================================
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def get_working_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(".")


def http_get_json(url: str, timeout: int = 10) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def http_download(url: str, dest: str, timeout: int = 120, reporthook=None):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        total = int(r.headers.get("Content-Length", 0))
        downloaded = 0
        with open(dest, "wb") as f:
            while True:
                chunk = r.read(65536)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if reporthook and total > 0:
                    reporthook(downloaded, total)


# ============================================================
# HILO DE DESCARGA CLIENTE
# ============================================================
class DownloadThread(QThread):
    progress_updated = Signal(int)
    status_updated = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, version, minecraft_dir):
        super().__init__()
        self.version = version
        self.minecraft_dir = minecraft_dir

    def run(self):
        try:
            self.status_updated.emit(f"📥 Descargando versión {self.version}...")
            self.progress_updated.emit(10)

            def update_progress(progress):
                self.progress_updated.emit(10 + int(progress * 80))

            def update_status(status):
                self.status_updated.emit(f"📥 {status}")

            callback = {"setStatus": update_status, "setProgress": update_progress}
            minecraft_launcher_lib.install.install_minecraft_version(
                self.version, self.minecraft_dir, callback=callback
            )
            self.progress_updated.emit(100)
            self.status_updated.emit(f"✅ Versión {self.version} instalada")
            self.finished.emit(True, "")
        except Exception as e:
            self.finished.emit(False, str(e))


# ============================================================
# HILO DE DESCARGA DE JAVA
# ============================================================
class JavaDownloadThread(QThread):
    progress_updated = Signal(int)
    status_updated = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, java_version, java_base_dir):
        super().__init__()
        self.java_version = java_version
        self.java_base_dir = java_base_dir

    def run(self):
        try:
            version = self.java_version
            dest_dir = os.path.join(self.java_base_dir, version)
            zip_path = os.path.join(self.java_base_dir, f"java_{version}.zip")

            os.makedirs(self.java_base_dir, exist_ok=True)

            java_exe = os.path.join(dest_dir, "r", "bin", "java.exe")
            if os.path.exists(java_exe):
                self.progress_updated.emit(100)
                self.status_updated.emit(f"✅ Java {version} ya instalado")
                self.finished.emit(True, "")
                return

            self.status_updated.emit(f"📥 Descargando Java {version}...")
            self.progress_updated.emit(5)

            url = (
                f"https://api.adoptium.net/v3/binary/latest/{version}/ga/"
                f"windows/x64/jre/hotspot/normal/eclipse"
            )

            def hook(downloaded, total):
                percent = min(100, int(downloaded * 100 / total))
                self.progress_updated.emit(5 + int(percent * 0.70))

            http_download(url, zip_path, reporthook=hook)
            self.progress_updated.emit(78)

            self.status_updated.emit(f"📦 Extrayendo Java {version}...")
            if os.path.exists(dest_dir):
                try:
                    shutil.rmtree(dest_dir)
                except Exception:
                    pass
            os.makedirs(dest_dir, exist_ok=True)

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(dest_dir)

            try:
                os.remove(zip_path)
            except Exception:
                pass

            self.progress_updated.emit(92)

            renamed = False
            for item in os.listdir(dest_dir):
                full = os.path.join(dest_dir, item)
                if os.path.isdir(full) and os.path.exists(os.path.join(full, "bin", "java.exe")):
                    target = os.path.join(dest_dir, "r")
                    if os.path.exists(target):
                        try:
                            shutil.rmtree(target)
                        except Exception:
                            pass
                    os.rename(full, target)
                    renamed = True
                    break

            if not renamed:
                raise Exception("No se encontró la carpeta de Java extraída")

            java_exe = os.path.join(dest_dir, "r", "bin", "java.exe")
            if not os.path.exists(java_exe):
                raise Exception("Java no quedó en la ruta esperada")

            self.progress_updated.emit(100)
            self.status_updated.emit(f"✅ Java {version} instalado")
            self.finished.emit(True, "")
        except Exception as e:
            self.finished.emit(False, str(e))


# ============================================================
# HILO DE DESCARGA SERVIDOR
# ============================================================
class ServerDownloadThread(QThread):
    progress_updated = Signal(int)
    status_updated = Signal(str)
    log_message = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, version, server_dir):
        super().__init__()
        self.version = version
        self.server_dir = server_dir

    def run(self):
        try:
            self.status_updated.emit(f"📥 Descargando Purpur {self.version}...")
            self.progress_updated.emit(5)

            url = f"https://api.purpurmc.org/v2/purpur/{self.version}/latest/download"
            jar_path = os.path.join(self.server_dir, f"purpur-{self.version}.jar")
            os.makedirs(self.server_dir, exist_ok=True)

            def hook(downloaded, total):
                percent = min(100, int(downloaded * 100 / total))
                self.progress_updated.emit(5 + int(percent * 0.55))

            http_download(url, jar_path, reporthook=hook)
            self.progress_updated.emit(62)

            if not os.path.exists(jar_path):
                raise Exception("El archivo Purpur no se descargó")

            self.log_message.emit(f"✅ Purpur {self.version} descargado")

            with open(os.path.join(self.server_dir, "eula.txt"), "w") as f:
                f.write("eula=true\n")

            props_path = os.path.join(self.server_dir, "server.properties")
            if not os.path.exists(props_path):
                with open(props_path, "w") as f:
                    f.write("enable-command-block=true\n")
                    f.write("spawn-protection=0\n")
                    f.write(f"motd=Servidor Purpur {self.version}\n")
                    f.write("online-mode=false\n")
                    f.write("allow-flight=true\n")
                    f.write("view-distance=16\n")
                    f.write("max-players=20\n")
                    f.write("enforce-secure-profile=false\n")

            skins_dir = os.path.join(self.server_dir, "purpur", "plugins", "SkinsRestorer")
            config_path = os.path.join(skins_dir, "config.yml")

            os.makedirs(skins_dir, exist_ok=True)

            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                with open(config_path, "w", encoding="utf-8") as f:
                    for line in lines:
                        if "mineskinAPIKey:" in line:
                            f.write("                                mineskinAPIKey: msk_vgnPuerc_Az4QRgIAkvFa1ZF_unAPTdez1Az3w_XtHyUkGyRdNcfbY7x3XbQ9H3Bm_qhPY89E\n")
                        else:
                            f.write(line)       

            vainilla_dir = os.path.join(self.server_dir, "vainilla")
            os.makedirs(vainilla_dir, exist_ok=True)

            props_path = os.path.join(vainilla_dir, "server.properties")

            if os.path.exists(props_path):
                cambios = {
                    "max-players": "20",
                    "motd": f"Servidor Vanilla {self.version}",
                    "spawn-protection": "0",
                    "enable-command-block": "true",
                    "online-mode": "false",
                    "allow-flight": "true",
                    "view-distance": "16",
                    "simulation-distance": "16",
                    "enforce-secure-profile": "false",
                }

                with open(props_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                with open(props_path, "w", encoding="utf-8") as f:
                    for line in lines:
                        if "=" in line and not line.startswith("#"):
                            clave = line.split("=", 1)[0]

                            if clave in cambios:
                                f.write(f"{clave}={cambios[clave]}\n")
                                continue

                        f.write(line)

            self.status_updated.emit("📥 Descargando Geyser + Floodgate...")
            self.progress_updated.emit(72)

            plugin_dir = os.path.join(self.server_dir, "plugins")
            os.makedirs(plugin_dir, exist_ok=True)

            info = download_geyser_floodgate(plugin_dir, self.log_message)
            self.progress_updated.emit(95)

            if info:
                save_geyser_version(self.server_dir, info)

            self.progress_updated.emit(100)
            self.status_updated.emit(f"✅ Servidor {self.version} listo")
            self.finished.emit(True, "")
        except Exception as e:
            self.finished.emit(False, str(e))

# ============================================================
# HILO DE DESCARGA DE VANILLA
# ============================================================
class VanillaDownloadThread(QThread):
    progress_updated = Signal(int)
    status_updated = Signal(str)
    log_message = Signal(str)
    finished_download = Signal(bool, str)

    def __init__(self, version, server_dir):
        super().__init__()
        self.version = version
        self.server_dir = server_dir

    def run(self):
        try:
            self.status_updated.emit(f"📥 Consultando manifiesto de Mojang...")
            self.progress_updated.emit(2)

            # 1. Obtener manifiesto (con User-Agent completo)
            req = urllib.request.Request(
                "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json",
                headers={"User-Agent": USER_AGENT},
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                manifest = json.loads(r.read().decode())

            target = next(
                (item for item in manifest["versions"] if item["id"] == self.version),
                None
            )
            if not target:
                raise Exception(f"Versión {self.version} no encontrada en el manifiesto de Mojang")

            self.progress_updated.emit(5)
            self.status_updated.emit(f"📥 Obteniendo datos de Vanilla {self.version}...")

            # 2. Obtener URL de descarga del servidor
            req = urllib.request.Request(
                target["url"],
                headers={"User-Agent": USER_AGENT},
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                version_data = json.loads(r.read().decode())

            if "server" not in version_data.get("downloads", {}):
                raise Exception(
                    f"La versión {self.version} no tiene servidor descargable "
                    "(algunas versiones muy antiguas o snapshots no lo incluyen)"
                )

            server_info = version_data["downloads"]["server"]
            server_url = server_info["url"]
            expected_sha1 = server_info.get("sha1", "")

            self.log_message.emit(f"✅ URL obtenida: {server_url}")
            self.progress_updated.emit(10)

            # 3. Descargar
            self.status_updated.emit(f"📥 Descargando Vanilla {self.version}...")
            jar_path = os.path.join(self.server_dir, f"vanilla-{self.version}.jar")

            def hook(downloaded, total):
                if total > 0:
                    percent = min(100, int(downloaded * 100 / total))
                    self.progress_updated.emit(10 + int(percent * 0.8))

            req = urllib.request.Request(
                server_url,
                headers={"User-Agent": USER_AGENT},
            )
            with urllib.request.urlopen(req, timeout=120) as r:
                total = int(r.headers.get("Content-Length", 0))
                downloaded = 0
                with open(jar_path, "wb") as f:
                    while True:
                        chunk = r.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            hook(downloaded, total)

            self.log_message.emit(f"✅ Descargado: {jar_path}")
            self.progress_updated.emit(92)

            # 4. eula.txt
            with open(os.path.join(self.server_dir, "eula.txt"), "w") as f:
                f.write("eula=true\n")

            # 5. server.properties (si no existe)
            props_path = os.path.join(self.server_dir, "server.properties")
            if not os.path.exists(props_path):
                with open(props_path, "w") as f:
                    f.write("enable-command-block=true\n")
                    f.write("spawn-protection=0\n")
                    f.write(f"motd=Servidor Vanilla {self.version}\n")
                    f.write("online-mode=false\n")
                    f.write("allow-flight=true\n")
                    f.write("view-distance=16\n")
                    f.write("max-players=20\n")
                    f.write("enforce-secure-profile=false\n")

            self.progress_updated.emit(100)
            self.status_updated.emit(f"✅ Servidor Vanilla {self.version} listo")
            self.finished_download.emit(True, "")

        except urllib.error.HTTPError as e:
            self.finished_download.emit(
                False,
                f"HTTP {e.code} al descargar de Mojang.\n\n"
                "Prueba a abrir este enlace en el navegador para verificar acceso:\n"
                "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
            )
        except urllib.error.URLError as e:
            self.finished_download.emit(False, f"Error de red: {e.reason}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.finished_download.emit(False, str(e))

# ============================================================
# GEYSER
# ============================================================
def get_latest_geyser_version() -> Optional[str]:
    try:
        data = http_get_json(
            "https://download.geysermc.org/v2/projects/geyser/versions/latest",
            timeout=8
        )
        return data.get("version")
    except Exception as e:
        print(f"Error consultando versión Geyser: {e}")
        return None


def download_geyser_floodgate(plugin_dir: str, log_callback=None) -> Optional[str]:
    urls = {
        "Geyser-Spigot.jar": "https://download.geysermc.org/v2/projects/geyser/versions/latest/builds/latest/downloads/spigot",
        "Floodgate-Spigot.jar": "https://download.geysermc.org/v2/projects/floodgate/versions/latest/builds/latest/downloads/spigot",
        "Skin-Restorer.jar": "https://cdn.modrinth.com/data/TsLS8Py5/versions/ziIzW16f/SkinsRestorer.jar?mr_download_reason=standalone",
        "GeyserSkinManager-Spigot.jar": "https://github.com/Camotoy/GeyserSkinManager/releases/download/1.8/GeyserSkinManager-Spigot.jar",
    }
    version = get_latest_geyser_version()
    for fname, url in urls.items():
        try:
            if log_callback:
                log_callback.emit(f"⬇ Descargando {fname}...")
            dest = os.path.join(plugin_dir, fname)
            http_download(url, dest)
            if log_callback:
                log_callback.emit(f"✅ {fname} OK")
        except Exception as e:
            if log_callback:
                log_callback.emit(f"❌ Error con {fname}: {e}")
            return None
    return version


def save_geyser_version(server_dir: str, version: str):
    try:
        with open(os.path.join(server_dir, ".geyser_version"), "w") as f:
            f.write(version)
    except Exception as e:
        print(f"No se pudo guardar versión Geyser: {e}")


def load_geyser_version(server_dir: str) -> Optional[str]:
    path = os.path.join(server_dir, ".geyser_version")
    try:
        if os.path.exists(path):
            with open(path, "r") as f:
                return f.read().strip()
    except Exception:
        pass
    return None


# ============================================================
# HILO LECTOR DEL STDOUT DEL SERVIDOR
# ============================================================
class ServerReaderThread(QThread):
    line_received = Signal(str)
    process_ended = Signal(int)

    def __init__(self, process):
        super().__init__()
        self.process = process

    def run(self):
        try:
            for line in iter(self.process.stdout.readline, ""):
                if not line:
                    break
                self.line_received.emit(line.rstrip("\n"))
        except Exception:
            pass
        try:
            code = self.process.wait()
        except Exception:
            code = -1
        self.process_ended.emit(code)


# ============================================================
# TAREA QRunnable: consultar IPs
# ============================================================
class IPLookupSignals(QObject):
    result_ready = Signal(str, str)
    error_occurred = Signal(str)


class IPLookupTask(QRunnable):
    def __init__(self):
        super().__init__()
        self.signals = IPLookupSignals()

    @Slot()
    def run(self):
        ipv4 = self._fetch("https://api.ipify.org")
        ipv6 = self._fetch("https://api64.ipify.org")

        if ipv4 is None and ipv6 is None:
            self.signals.error_occurred.emit("No se pudo obtener ninguna IP pública")
            return

        if ipv6 and ipv4 and ipv6 == ipv4:
            ipv6 = None

        self.signals.result_ready.emit(
            ipv4 or "(no disponible)",
            ipv6 or "(solo IPv4)"
        )

    def _fetch(self, url: str) -> Optional[str]:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=6) as r:
                data = r.read().decode().strip()
                return data if data else None
        except Exception as e:
            print(f"Error consultando {url}: {e}")
            return None

# ============================================================
# TAREA QRunnable: vigilar proceso del cliente
# ============================================================
class ProcessWatcherSignals(QObject):
    finished = Signal()


class ProcessWatcherTask(QRunnable):
    def __init__(self, process):
        super().__init__()
        self.process = process
        self.signals = ProcessWatcherSignals()

    @Slot()
    def run(self):
        try:
            while True:
                if self.process.poll() is not None:
                    break
                time.sleep(0.5)
        except Exception:
            pass
        self.signals.finished.emit()

# ============================================================
# HILO: subir skin a Catbox (con diagnóstico)
# ============================================================
class SkinUploadThread(QThread):
    finished_upload = Signal(str, str)  # url, error_msg

    def __init__(self, ruta_local, userhash=""):
        super().__init__()
        self.ruta_local = ruta_local
        self.userhash = userhash

    def run(self):
        print(f"[Skin] === Iniciando subida de: {self.ruta_local}")
        try:
            import uuid

            if not os.path.exists(self.ruta_local):
                print(f"[Skin] ERROR: archivo no existe")
                self.finished_upload.emit("", "El archivo no existe")
                return

            size = os.path.getsize(self.ruta_local)
            print(f"[Skin] Tamaño del archivo: {size} bytes")

            with open(self.ruta_local, "rb") as f:
                file_data = f.read()

            print(f"[Skin] Archivo leído: {len(file_data)} bytes")

            boundary = "----TerraCraftBoundary" + uuid.uuid4().hex

            body = b""

            body += f"--{boundary}\r\n".encode()
            body += b'Content-Disposition: form-data; name="reqtype"\r\n\r\n'
            body += b"fileupload\r\n"

            if self.userhash:
                body += f"--{boundary}\r\n".encode()
                body += b'Content-Disposition: form-data; name="userhash"\r\n\r\n'
                body += f"{self.userhash}\r\n".encode()

            filename = os.path.basename(self.ruta_local)
            body += f"--{boundary}\r\n".encode()
            body += (
                f'Content-Disposition: form-data; name="fileToUpload"; '
                f'filename="{filename}"\r\n'
            ).encode()
            body += b"Content-Type: image/png\r\n\r\n"
            body += file_data + b"\r\n"
            body += f"--{boundary}--\r\n".encode()

            print(f"[Skin] Body construido: {len(body)} bytes")

            req = urllib.request.Request(
                "https://catbox.moe/user/api.php",
                data=body,
                headers={
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                    "User-Agent": USER_AGENT,
                },
            )

            print(f"[Skin] Enviando petición a Catbox...")

            with urllib.request.urlopen(req, timeout=60) as resp:
                response_text = resp.read().decode().strip()

            print(f"[Skin] Respuesta: {response_text[:200]}")

            if response_text.startswith("https://"):
                self.finished_upload.emit(response_text, "")
            else:
                self.finished_upload.emit("", f"Respuesta inesperada: {response_text[:200]}")

        except urllib.error.HTTPError as e:
            try:
                err_body = e.read().decode()[:300]
            except Exception:
                err_body = "(sin cuerpo)"
            print(f"[Skin] HTTPError {e.code}: {err_body}")
            self.finished_upload.emit("", f"HTTP {e.code}: {err_body}")
        except urllib.error.URLError as e:
            print(f"[Skin] URLError: {e.reason}")
            self.finished_upload.emit("", f"Error de red: {e.reason}")
        except Exception as e:
            import traceback
            print(f"[Skin] Exception: {type(e).__name__}: {e}")
            traceback.print_exc()
            self.finished_upload.emit("", f"Error: {type(e).__name__}: {e}")

# ============================================================
# HILO: descargar bytes de una skin desde una URL
# ============================================================
class SkinFetchThread(QThread):
    fetched = Signal(str, bytes)  # url, data (vacío si error)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            req = urllib.request.Request(
                self.url,
                headers={"User-Agent": "Mozilla/5.0 TerraCraft/1.0"}
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                data = r.read()
            self.fetched.emit(self.url, data)
        except Exception as e:
            print(f"[SkinFetch] Error descargando {self.url}: {e}")
            self.fetched.emit(self.url, b"")

# ============================================================
# FONDO ANIMADO
# ============================================================
class AnimatedBackground(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.movie = None
        self.setup_animation()

    def setup_animation(self):
        gif_path = resource_path(os.path.join("assets", "fondo.gif"))
        if os.path.exists(gif_path):
            self.movie = QMovie(gif_path)
            self.movie.setScaledSize(self.size())
            self.movie.frameChanged.connect(self.update)
            self.movie.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        if self.movie and self.movie.currentPixmap():
            scaled = self.movie.currentPixmap().scaled(
                self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
            )
            painter.drawPixmap(0, 0, scaled)
        else:
            gradient = QLinearGradient(0, 0, 0, self.height())
            gradient.setColorAt(0, QColor(26, 26, 46))
            gradient.setColorAt(0.5, QColor(22, 33, 62))
            gradient.setColorAt(1, QColor(15, 52, 96))
            painter.fillRect(self.rect(), gradient)
        painter.end()

    def resizeEvent(self, event):
        if self.movie:
            self.movie.setScaledSize(self.size())
        super().resizeEvent(event)


# ============================================================
# MÚSICA
# ============================================================
class BackgroundMusic(QObject):
    def __init__(self):
        super().__init__()
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.3)
        self.is_playing = False
        self.was_playing_before_pause = False
        self.player.mediaStatusChanged.connect(self.handle_media_status)

    def handle_media_status(self, status):
        if status == QMediaPlayer.EndOfMedia:
            self.player.setPosition(0)
            self.player.play()

    def play(self, file_path):
        if not os.path.exists(file_path):
            return
        try:
            self.stop()
            self.player.setSource(QUrl.fromLocalFile(file_path))
            self.player.play()
            self.is_playing = True
        except Exception as e:
            print(f"Error audio: {e}")

    def stop(self):
        if self.is_playing:
            self.player.stop()
            self.is_playing = False

    def pause_for_launch(self):
        if self.is_playing:
            self.was_playing_before_pause = True
            self.player.pause()
            self.is_playing = False
        # Si ya estaba pausada manualmente, was_playing_before_pause se queda como estaba (False)

    def resume_after_launch(self):
        if self.was_playing_before_pause:
            self.player.play()
            self.is_playing = True
            self.was_playing_before_pause = False

    def set_volume(self, volume):
        self.audio_output.setVolume(max(0.0, min(1.0, volume)))

    def toggle(self):
        if self.is_playing:
            self.player.pause()
            self.is_playing = False
        else:
            self.player.play()
            self.is_playing = True


# ============================================================
# LAUNCHER
# ============================================================
class TerrarianosLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.kill_orphan_java_processes()
        working_dir = get_working_dir()
        self.base_dir = working_dir
        self.minecraft_dir = os.path.join(working_dir, "minecraft")
        self.config_dir = os.path.join(working_dir, "config")
        self.server_dir = os.path.join(working_dir, "server")
        self.java_base_dir = os.path.join(working_dir, "java")
        self.settings_file = os.path.join(self.config_dir, "settings.json")
        self.setAttribute(Qt.WA_DeleteOnClose, True)

        for d in [self.minecraft_dir, self.config_dir, self.server_dir, self.java_base_dir]:
            os.makedirs(d, exist_ok=True)

        self.settings = {
            "username": "Jugador",
            "version": "1.21.4",
            "ram": 8,
            "server_version": "",
            "server_ram": 4,
            "known_server_versions": [],
            "music_volume": 0.3,
            "catbox_userhash": "",
            "my_skins": [],
        }
        self.load_settings()

        self.thread_pool = QThreadPool.globalInstance()

        # Cliente
        self.client_process = None
        self.client_watcher = None
        self.download_thread = None

        # Servidor
        self.server_process = None
        self.server_reader = None
        self.server_download_thread = None
        self.java_download_thread = None
        self.vanilla_download_thread = None
        self.server_running = False

        # Red
        self.api_status_msg = ""

        # Skin
        self.current_skin_index = 0
        self._preview_threads = []

        self.init_ui()
        self.init_background_music()
        self.check_version_installed()
        self.refresh_server_tab()

        self._migrate_old_server_files()

        QTimer.singleShot(300, self._load_ip_once)
        QTimer.singleShot(800, self.auto_update_geyser_on_start)

    # ---------- SETTINGS ----------
    def _migrate_old_server_files(self):
        """Mueve jars antiguos de server/ a server/purpur/ o server/vanilla/."""
        try:
            purpur_dir = os.path.join(self.server_dir, "purpur")
            vanilla_dir = os.path.join(self.server_dir, "vanilla")
            os.makedirs(purpur_dir, exist_ok=True)
            os.makedirs(vanilla_dir, exist_ok=True)

            for fname in os.listdir(self.server_dir):
                full = os.path.join(self.server_dir, fname)
                if not os.path.isfile(full):
                    continue
                if fname.startswith("purpur-") and fname.endswith(".jar"):
                    shutil.move(full, os.path.join(purpur_dir, fname))
                    print(f"[Migrate] {fname} → purpur/")
                elif fname.startswith("vanilla-") and fname.endswith(".jar"):
                    shutil.move(full, os.path.join(vanilla_dir, fname))
                    print(f"[Migrate] {fname} → vanilla/")

            # Migrar también eula.txt, server.properties, plugins/ viejos a purpur
            for legacy in ["eula.txt", "server.properties", "world", "plugins", "logs",
                           "banned-ips.json", "banned-players.json", "ops.json",
                           "whitelist.json", "usercache.json", "server.properties",
                           "cache", "libraries", "versions", ".geyser_version"]:
                old = os.path.join(self.server_dir, legacy)
                new = os.path.join(purpur_dir, legacy)
                if os.path.exists(old) and not os.path.exists(new):
                    shutil.move(old, new)
                    print(f"[Migrate] {legacy} → purpur/")
        except Exception as e:
            print(f"[Migrate] Error: {e}")

    def closeEvent(self, event):
        """Al cerrar el launcher, matar servidor y cliente si están corriendo."""
        # Detener servidor si está corriendo
        if self.server_process and self.server_process.poll() is None:
            try:
                if self.server_process.stdin:
                    self.server_process.stdin.write("stop\n")
                    self.server_process.stdin.flush()
            except Exception:
                pass
            # Esperar brevemente
            try:
                self.server_process.wait(timeout=5)
            except Exception:
                self._kill_process_tree(self.server_process)

        # Matar cliente si está corriendo
        if self.client_process and self.client_process.poll() is None:
            self._kill_process_tree(self.client_process)

        event.accept()

    def kill_orphan_java_processes(self):
        """Mata java.exe que estén usando el puerto 25565 o el PID quede huérfano."""
        if os.name != "nt":
            return
        try:
            # Buscar PIDs que estén escuchando en 25565 (servidor MC)
            result = subprocess.run(
                ["netstat", "-ano", "-p", "TCP"],
                capture_output=True, text=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            pids = set()
            for line in result.stdout.splitlines():
                if ":25565" in line and "LISTENING" in line:
                    parts = line.split()
                    if parts:
                        try:
                            pids.add(parts[-1])
                        except Exception:
                            pass

            for pid in pids:
                if pid and pid != "0":
                    subprocess.call(
                        ["taskkill", "/F", "/PID", pid],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                    print(f"[Cleanup] Matado java huérfano PID {pid} en puerto 25565")
        except Exception as e:
            print(f"[Cleanup] Error: {e}")

    def load_settings(self):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, "r") as f:
                    self.settings.update(json.load(f))
        except Exception as e:
            print(f"Error cargando settings: {e}")

    def save_settings(self):
        try:
            with open(self.settings_file, "w") as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Error guardando settings: {e}")

    # ---------- MÚSICA ----------
    def init_background_music(self):
        self.music = BackgroundMusic()
        for m in [
            resource_path(os.path.join("assets", "music.mp3")),
            resource_path(os.path.join("assets", "music.wav")),
            resource_path(os.path.join("assets", "background.mp3")),
            resource_path(os.path.join("assets", "theme.mp3")),
        ]:
            if os.path.exists(m):
                self.music.play(m)
                self.music.set_volume(self.settings.get("music_volume", 0.3))
                break
        self._update_volume_icon()

    def _update_volume_icon(self):
        if not hasattr(self, "volume_icon"):
            return
        if not self.music.is_playing:
            self.volume_icon.setText("🔇")
            return
        vol = self.volume_slider.value() / 100.0
        if vol == 0:
            self.volume_icon.setText("🔇")
        elif vol < 0.3:
            self.volume_icon.setText("🔈")
        elif vol < 0.7:
            self.volume_icon.setText("🔉")
        else:
            self.volume_icon.setText("🔊")

    def toggle_music_click(self, event):
        if not hasattr(self, "music"):
            return
        self.music.toggle()
        # Si el usuario pausa/reanuda manualmente, olvidamos el estado anterior
        self.music.was_playing_before_pause = False
        self._update_volume_icon()

    def change_volume(self, value):
        vol = value / 100.0
        if hasattr(self, "music"):
            self.music.set_volume(vol)
            self.settings["music_volume"] = vol
            self.save_settings()
            self._update_volume_icon()

    def _is_anything_running(self) -> bool:
        client_alive = (
            self.client_process is not None
            and self.client_process.poll() is None
        )
        return client_alive or self.server_running

    def _update_music_state(self):
        """Pausa si algo corre; reanuda solo si ambos están detenidos."""
        if self._is_anything_running():
            self.music.pause_for_launch()
        else:
            self.music.resume_after_launch()
        self._update_volume_icon()

    # ---------- UI ----------
    def init_ui(self):
        self.setWindowTitle("TERRACRAFT LAUNCHER")

        # Tamaño mínimo (nada se deforma por debajo de esto)
        self.setMinimumSize(800, 600)

        # Arrancar al 90% del alto de pantalla o 800x800 como máximo
        screen = QApplication.primaryScreen().availableGeometry()
        w = min(900, int(screen.width() * 0.8))
        h = min(850, int(screen.height() * 0.9))
        self.resize(w, h)

        icon_path = resource_path(os.path.join("assets", "icon.ico"))
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            png = resource_path(os.path.join("assets", "icon.png"))
            if os.path.exists(png):
                self.setWindowIcon(QIcon(png))

        self.background = AnimatedBackground(self)
        self.setCentralWidget(self.background)

        main_layout = QVBoxLayout(self.background)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(18, 18, 18, 18)

        self.apply_stylesheet()
        
        # TÍTULO (banner)
        title_layout = QHBoxLayout()

        banner_path = resource_path(os.path.join("assets", "banner.png"))
        title_label = QLabel()
        title_label.setObjectName("title_label")
        title_label.setAlignment(Qt.AlignCenter)

        if os.path.exists(banner_path):
            pixmap = QPixmap(banner_path)
            if not pixmap.isNull():
                # Escalar el banner a un alto máximo de 80px, manteniendo proporción
                scaled = pixmap.scaledToHeight(
                    130, Qt.SmoothTransformation
                )
                title_label.setPixmap(scaled)
        else:
            # Fallback: texto si no existe el banner
            title_label.setText("✦ TERRACRAFT LAUNCHER ✦")

        title_layout.addWidget(title_label)

        volume_widget = QWidget()
        volume_widget.setFixedWidth(240)  # ← sube el ancho para que quepa el Discord
        vlayout = QHBoxLayout(volume_widget)
        vlayout.setContentsMargins(0, 0, 0, 0)
        vlayout.setSpacing(12)

        # ---- Botón GitHub ----
        self.github_icon_button = QLabel()
        self.github_icon_button.setFixedSize(30, 30)
        self.github_icon_button.setAlignment(Qt.AlignCenter)
        self.github_icon_button.setToolTip("Ver código en GitHub")
        self.github_icon_button.setCursor(Qt.PointingHandCursor)

        github_path = resource_path(os.path.join("assets", "github.png"))
        if os.path.exists(github_path):
            github_pixmap = QPixmap(github_path)
            if not github_pixmap.isNull():
                self.github_icon_button.setPixmap(github_pixmap.scaled(
                    28, 28, Qt.KeepAspectRatio, Qt.SmoothTransformation
                ))
        else:
            self.github_icon_button.setText("🐙")
            self.github_icon_button.setStyleSheet("color: #ffffff; font-size: 20px;")

        self.github_icon_button.mousePressEvent = lambda e: self.open_github_link()
        vlayout.addWidget(self.github_icon_button)

        # ---- Botón Discord ----
        self.discord_button = QLabel()
        self.discord_button.setFixedSize(40, 40)
        self.discord_button.setAlignment(Qt.AlignCenter)
        self.discord_button.setToolTip("Unirse al Discord")
        self.discord_button.setCursor(Qt.PointingHandCursor)

        discord_path = resource_path(os.path.join("assets", "discord.png"))
        if os.path.exists(discord_path):
            discord_pixmap = QPixmap(discord_path)
            if not discord_pixmap.isNull():
                self.discord_button.setPixmap(discord_pixmap.scaled(
                    40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation
                ))
        else:
            # Fallback: emoji
            self.discord_button.setText("💬")
            self.discord_button.setStyleSheet(
                "color: #5865F2; font-size: 20px;"
            )

        self.discord_button.mousePressEvent = self.open_discord_link
        vlayout.addWidget(self.discord_button)

        # ---- Icono de sonido ----
        self.volume_icon = QLabel("🔊")
        self.volume_icon.setFixedSize(30, 30)
        self.volume_icon.setAlignment(Qt.AlignCenter)
        self.volume_icon.setStyleSheet("color: #00d4ff; font-size: 20px;")
        self.volume_icon.mousePressEvent = self.toggle_music_click
        vlayout.addWidget(self.volume_icon)

        # ---- Slider ----
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(int(self.settings.get("music_volume", 0.3) * 100))
        self.volume_slider.setFixedWidth(100)
        self.volume_slider.valueChanged.connect(self.change_volume)
        vlayout.addWidget(self.volume_slider)

        # ---- Botón carpeta ----
        self.folder_button = QPushButton("📁")
        self.folder_button.setObjectName("folder_button")
        self.folder_button.setFixedSize(34, 34)
        self.folder_button.setToolTip("Abrir carpeta del launcher")
        self.folder_button.clicked.connect(self.open_launcher_folder)
        vlayout.addWidget(self.folder_button)

        title_layout.addWidget(volume_widget)
        main_layout.addLayout(title_layout)

        # TABS
        self.tabs = QTabWidget()
        self.tabs.setObjectName("main_tabs")
        main_layout.addWidget(self.tabs)

        self.client_tab = QWidget()
        self.build_client_tab(self.client_tab)
        self.tabs.addTab(self.client_tab, "🎮 Cliente")

        self.server_tab = QWidget()
        self.build_server_tab(self.server_tab)
        self.tabs.addTab(self.server_tab, "🖥️ Servidor")

        self.log_tab = QWidget()
        self.build_log_tab(self.log_tab)
        self.tabs.addTab(self.log_tab, "📜 Log")

        self.network_tab = QWidget()
        self.build_network_tab(self.network_tab)
        self.tabs.addTab(self.network_tab, "🌐 Red")

        self.skin_tab = QWidget()
        self.build_skin_tab(self.skin_tab)
        self.tabs.addTab(self.skin_tab, "🎨 Skins de Purpur")
        self.tabs.currentChanged.connect(self._on_tab_changed)

        self.mods_tab = QWidget()
        self.build_mods_tab(self.mods_tab)
        self.tabs.addTab(self.mods_tab, "🧩 Mods Spigot")

        self.info_tab = QWidget()
        self.build_info_tab(self.info_tab)
        self.tabs.addTab(self.info_tab, "ℹ️ Info")

    def apply_stylesheet(self):
        self.setStyleSheet("""
            QMainWindow, QWidget { background: transparent; }

            QLabel#title_label {
                color: #00d4ff;
                font-size: 30px;
                font-weight: bold;
                padding: 6px;
                font-family: 'Segoe UI', Arial;
            }
            QLabel#subtitle_label {
                color: #a8d8ea;
                font-size: 12px;
                padding: 2px;
            }
            QLabel {
                color: #e0e0e0;
                font-size: 12px;
                font-family: 'Segoe UI', Arial;
            }
            QLabel#field_label {
                font-size: 13px;
                font-weight: bold;
                color: #00d4ff;
                padding: 2px 0px;
            }
            QLabel#ram_note {
                color: #a8d8ea;
                font-style: italic;
                font-size: 11px;
                padding: 2px 0px;
            }
            QLabel#panel_title {
                color: #00d4ff;
                font-size: 14px;
                font-weight: bold;
                padding: 0 0 4px 0;
            }

            QFrame#panel {
                background: rgba(0, 0, 0, 0.35);
                border: 2px solid rgba(0, 168, 204, 0.35);
                border-radius: 10px;
            }

            QLineEdit, QComboBox {
                background: rgba(0, 0, 0, 0.6);
                color: #00d4ff;
                border: 2px solid #00a8cc;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
                min-height: 26px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 2px solid #00d4ff;
                background: rgba(0, 0, 0, 0.8);
            }
            QComboBox::drop-down {
                border: none;
                width: 22px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #00d4ff;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background: rgba(10, 10, 20, 0.98);
                color: #00d4ff;
                selection-background-color: rgba(0, 212, 255, 0.3);
                selection-color: white;
                padding: 4px;
                border: 2px solid #00a8cc;
                font-size: 13px;
            }
            QComboBox QAbstractItemView::item {
                min-height: 26px;
                padding: 4px 8px;
            }

            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #00a8cc, stop:1 #007a99);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 13px;
                min-height: 30px;
            }
            QPushButton:hover:!disabled {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #00d4ff, stop:1 #00a8cc);
            }
            QPushButton:disabled { background: #555; color: #888; }

            QPushButton#start_button {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ff6b6b, stop:1 #ee5a24);
                font-size: 20px;
                min-height: 50px;
                letter-spacing: 3px;
                border-radius: 10px;
            }
            QPushButton#start_button:hover:!disabled {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ff7979, stop:1 #ff6b6b);
            }

            QPushButton#server_main_button {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #7f5af0, stop:1 #5a3fc0);
                font-size: 18px;
                min-height: 48px;
                letter-spacing: 2px;
                border-radius: 10px;
            }
            QPushButton#server_main_button:hover:!disabled {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #9b7aff, stop:1 #7f5af0);
            }

            QPushButton#copy_button {
                min-height: 20px;
                min-width: 40px;
                max-width: 40px;
                padding: 4px;
                font-size: 14px;
            }

            QPushButton#delete_button {
                min-height: 30px;
                min-width: 38px;
                max-width: 38px;
                padding: 2px;
                font-size: 14px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #c0392b, stop:1 #8b1e1e);
            }
            QPushButton#delete_button:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e74c3c, stop:1 #c0392b);
            }

            QPushButton#folder_button {
                min-height: 28px;
                min-width: 34px;
                max-width: 34px;
                padding: 2px;
                font-size: 15px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #007a99, stop:1 #005a73);
            }
            QPushButton#folder_button:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #00a8cc, stop:1 #007a99);
            }

            QProgressBar {
                border: 2px solid #00a8cc;
                border-radius: 8px;
                text-align: center;
                color: white;
                background: rgba(0, 0, 0, 0.6);
                font-weight: bold;
                min-height: 24px;
                font-size: 12px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00a8cc, stop:0.5 #00d4ff, stop:1 #7f5af0);
                border-radius: 6px;
            }

            QTabWidget::pane {
                border: 2px solid rgba(0, 168, 204, 0.4);
                border-radius: 8px;
                background: rgba(0, 0, 0, 0.25);
                top: -1px;
            }
            QTabBar::tab {
                background: rgba(0, 0, 0, 0.5);
                color: #a8d8ea;
                padding: 10px 18px;
                border: 2px solid rgba(0, 168, 204, 0.4);
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: rgba(0, 168, 204, 0.35);
                color: #00d4ff;
                border-color: #00d4ff;
            }
            QTabBar::tab:hover:!selected {
                background: rgba(0, 168, 204, 0.2);
                color: #00d4ff;
            }

            QPlainTextEdit {
                background: rgba(0, 0, 0, 0.85);
                color: #7fff7f;
                border: 2px solid #00a8cc;
                border-radius: 6px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                padding: 6px;
            }

            QLabel#ip_display {
                color: #00d4ff;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 13px;
                font-weight: bold;
                padding: 1px 10px;
                background: rgba(0, 0, 0, 0.5);
                border-radius: 6px;
                border: 1px solid rgba(0, 168, 204, 0.5);
                min-width: 380px;
            }
            QLabel#status_info {
                color: #a8d8ea;
                font-size: 11px;
                padding: 10px;
            }
        """)

    def make_panel(self, title_text):
        frame = QFrame()
        frame.setObjectName("panel")
        outer = QVBoxLayout(frame)
        outer.setContentsMargins(14, 12, 14, 14)
        outer.setSpacing(10)

        title = QLabel(title_text)
        title.setObjectName("panel_title")
        outer.addWidget(title)

        content = QVBoxLayout()
        content.setSpacing(10)
        outer.addLayout(content)

        return frame, content

    # ============================================================
    # CLIENTE
    # ============================================================
    def build_client_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setSpacing(10)
        layout.setContentsMargins(14, 14, 14, 14)

        panel, _ = self.make_panel("Configuración del Jugador")
        grid = QGridLayout()
        grid.setSpacing(10)
        grid.setColumnStretch(1, 1)

        grid.addWidget(self._field("👤 Nombre:"), 0, 0)
        self.username_input = QLineEdit(self.settings["username"])
        self.username_input.textChanged.connect(self.update_settings)
        grid.addWidget(self.username_input, 0, 1)

        grid.addWidget(self._field("📦 Versión:"), 1, 0)

        version_row = QHBoxLayout()
        version_row.setSpacing(8)

        self.version_combo = QComboBox()
        self.version_combo.setEditable(True)
        self.version_combo.currentTextChanged.connect(self.on_client_version_changed)
        version_row.addWidget(self.version_combo, stretch=1)

        self.delete_client_button = QPushButton("🗑")
        self.delete_client_button.setObjectName("delete_button")
        self.delete_client_button.setToolTip("Eliminar esta versión del cliente")
        self.delete_client_button.clicked.connect(self.delete_client_version)
        version_row.addWidget(self.delete_client_button)

        grid.addLayout(version_row, 1, 1)

        grid.addWidget(self._field("💾 RAM:"), 2, 0)
        self.ram_combo = QComboBox()
        self.ram_combo.addItems(["2 GB", "4 GB", "6 GB", "8 GB", "12 GB", "16 GB"])
        self.ram_combo.setCurrentText(f"{self.settings['ram']} GB")
        self.ram_combo.currentTextChanged.connect(self.update_settings)
        grid.addWidget(self.ram_combo, 2, 1)

        panel.layout().addLayout(grid)
        layout.addWidget(panel)

        self.client_progress = QProgressBar()
        self.client_progress.setRange(0, 100)
        layout.addWidget(self.client_progress)

        self.client_status = QLabel("✅ Listo")
        self.client_status.setAlignment(Qt.AlignCenter)
        self.client_status.setStyleSheet("""
            font-size: 13px; font-weight: bold; color: #00d4ff;
            padding: 8px; background: rgba(0,0,0,0.4);
            border-radius: 6px; min-height: 34px;
        """)
        layout.addWidget(self.client_status)

        self.start_button = QPushButton("▶ COMENZAR")
        self.start_button.setObjectName("start_button")
        self.start_button.clicked.connect(self.start_game)
        layout.addWidget(self.start_button)

        layout.addStretch()

        self.load_versions()

    def _field(self, text):
        lbl = QLabel(text)
        lbl.setObjectName("field_label")
        return lbl

    def on_client_version_changed(self):
        self.settings["version"] = self.version_combo.currentText()
        self.save_settings()
        self.check_version_installed()

    # ============================================================
    # SERVIDOR
    # ============================================================
    def build_server_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setSpacing(10)
        layout.setContentsMargins(14, 14, 14, 14)

        panel, _ = self.make_panel("Configuración del Servidor")
        grid = QGridLayout()
        grid.setSpacing(10)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)

        # ---- Fila 0: Servidor | Versión | 🗑 ----
        grid.addWidget(self._field("⚙️ Servidor:"), 0, 0)

        self.server_type_combo = QComboBox()
        self.server_type_combo.addItems(["Purpur", "Vanilla"])
        self.server_type_combo.setCurrentText(self.settings.get("server_type", "Purpur"))
        self.server_type_combo.currentTextChanged.connect(self.on_server_type_changed)
        self.server_type_combo.setMinimumWidth(110)
        grid.addWidget(self.server_type_combo, 0, 1)

        grid.addWidget(self._field("📦 Versión:"), 0, 2)

        # Sub-layout horizontal: combo versión + botón eliminar
        version_row = QHBoxLayout()
        version_row.setSpacing(6)

        self.server_version_combo = QComboBox()
        self.server_version_combo.setEditable(True)
        self.server_version_combo.setInsertPolicy(QComboBox.NoInsert)
        self.server_version_combo.lineEdit().setPlaceholderText("Versión...")
        self.server_version_combo.currentTextChanged.connect(self.on_server_version_changed)
        version_row.addWidget(self.server_version_combo, stretch=1)

        self.delete_server_button = QPushButton("🗑")
        self.delete_server_button.setObjectName("delete_button")
        self.delete_server_button.setToolTip("Eliminar esta versión del servidor")
        self.delete_server_button.clicked.connect(self.delete_server_version)
        version_row.addWidget(self.delete_server_button)

        grid.addLayout(version_row, 0, 3)

        # ---- Fila 1: Nota de Java ----
        self.java_info_label = QLabel("💡 Java requerido: (elige una versión)")
        self.java_info_label.setObjectName("ram_note")
        self.java_info_label.setWordWrap(True)
        grid.addWidget(self.java_info_label, 1, 0, 1, 4)

        # ---- Fila 2: RAM ----
        grid.addWidget(self._field("💾 RAM:"), 2, 0)
        self.server_ram_combo = QComboBox()
        self.server_ram_combo.addItems(["2 GB", "4 GB", "6 GB", "8 GB", "12 GB", "16 GB"])
        self.server_ram_combo.setCurrentText(f"{self.settings.get('server_ram', 4)} GB")
        self.server_ram_combo.currentTextChanged.connect(self.on_server_ram_changed)
        grid.addWidget(self.server_ram_combo, 2, 1)

        ram_note = QLabel("💡 2-5 jugadores → 4 GB · 10-20 jugadores → 8 GB")
        ram_note.setObjectName("ram_note")
        ram_note.setWordWrap(True)
        grid.addWidget(ram_note, 2, 2, 1, 2)

        panel.layout().addLayout(grid)
        layout.addWidget(panel)

        self.server_main_button = QPushButton("⬇ INSTALAR SERVIDOR")
        self.server_main_button.setObjectName("server_main_button")
        self.server_main_button.clicked.connect(self.server_main_action)
        layout.addWidget(self.server_main_button)

        self.server_progress = QProgressBar()
        self.server_progress.setRange(0, 100)
        self.server_progress.setValue(0)
        layout.addWidget(self.server_progress)

        self.server_status = QLabel("Selecciona o escribe una versión para empezar")
        self.server_status.setAlignment(Qt.AlignCenter)
        self.server_status.setStyleSheet("""
            font-size: 12px; font-weight: bold; color: #b19cd9;
            padding: 8px; background: rgba(0,0,0,0.4);
            border-radius: 6px; min-height: 32px;
        """)
        layout.addWidget(self.server_status)

        layout.addStretch()

        self.load_server_versions()

    def on_server_type_changed(self, server_type):
        self.settings["server_type"] = server_type
        self.save_settings()
        self.load_server_versions()
        # Refrescar el botón porque el jar cambia según tipo
        self.refresh_server_tab()
        self._update_java_info_label(self.server_version_combo.currentText().strip())

    def load_server_versions(self):
        """Carga versiones según el tipo de servidor seleccionado."""
        server_type = self.server_type_combo.currentText()
        known = self.settings.get("known_server_versions", [])

        if server_type == "Purpur":
            fallback = ["1.21.11", "1.21.10", "1.21.8", "1.21.4", "1.20.6", "1.14.4"]
            initial = known if known else fallback
            self._populate_server_versions(initial)
            # Fetch de la API de Purpur
            def fetch():
                try:
                    data = http_get_json("https://api.purpurmc.org/v2/purpur/", timeout=10)
                    versions = list(reversed(data.get("versions", [])))
                    QTimer.singleShot(0, lambda: self._populate_server_versions(versions + known))
                except Exception as e:
                    print(f"Error cargando versiones Purpur: {e}")
            threading.Thread(target=fetch, daemon=True).start()

        else:  # Vanilla
            # Versiones de Vanilla desde el manifiesto de Mojang
            def fetch():
                try:
                    data = http_get_json("https://piston-meta.mojang.com/mc/game/version_manifest_v2.json", timeout=15)
                    versions = [v["id"] for v in data.get("versions", []) if v["type"] == "release"]
                    QTimer.singleShot(0, lambda: self._populate_server_versions(versions))
                except Exception as e:
                    print(f"Error cargando versiones Vanilla: {e}")
                    QTimer.singleShot(0, lambda: self._populate_server_versions(["1.21.4", "1.20.6", "1.19.4", "1.18.2", "1.16.5", "1.12.2"]))
            threading.Thread(target=fetch, daemon=True).start()

    def get_current_server_dir(self):
        """Devuelve server/purpur o server/vanilla según el tipo seleccionado."""
        server_type = self.server_type_combo.currentText().lower()  # 'purpur' o 'vanilla'
        path = os.path.join(self.server_dir, server_type)
        os.makedirs(path, exist_ok=True)
        return path

    def get_server_jar_path(self):
        v = self.server_version_combo.currentText().strip()
        if not v:
            return None
        server_type = self.server_type_combo.currentText().lower()
        return os.path.join(self.get_current_server_dir(), f"{server_type}-{v}.jar")
    
    # ============================================================
    # LOG
    # ============================================================
    def build_log_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setSpacing(10)
        layout.setContentsMargins(14, 14, 14, 14)

        header = QLabel(
            "📜 Consola del servidor — escribe comandos y pulsa Enter para enviarlos."
        )
        header.setObjectName("panel_title")
        header.setWordWrap(True)
        layout.addWidget(header)

        self.server_log = QPlainTextEdit()
        self.server_log.setReadOnly(False)
        self.server_log.setMaximumBlockCount(3000)
        self.server_log.setPlaceholderText(
            "Aquí verás el log del servidor.\n"
            "Cuando esté corriendo, escribe comandos (ej: 'say hola') y pulsa Enter."
        )
        self.server_log.installEventFilter(self)
        layout.addWidget(self.server_log, stretch=1)

    def eventFilter(self, obj, event):
        if obj is self.server_log and event.type() == event.Type.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if not (event.modifiers() & Qt.ShiftModifier):
                    self.send_server_command()
                    return True
        return super().eventFilter(obj, event)

    def send_server_command(self):
        if not self.server_running or not self.server_process:
            self._clear_last_user_line()
            return

        text = self.server_log.toPlainText()
        lines = text.split("\n")
        if not lines:
            return
        last = lines[-1].strip()
        if not last:
            return

        try:
            self.server_process.stdin.write(last + "\n")
            self.server_process.stdin.flush()
            self.append_server_log(f"> {last}")
        except Exception as e:
            self.append_server_log(f"[Launcher] Error enviando comando: {e}")

        cursor = self.server_log.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.server_log.setTextCursor(cursor)
        self.server_log.insertPlainText("\n")

    def _clear_last_user_line(self):
        cursor = self.server_log.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.select(QTextCursor.LineUnderCursor)
        cursor.removeSelectedText()
        self.server_log.setTextCursor(cursor)

    # ============================================================
    # VERSIONES DEL SERVIDOR
    # ============================================================
    def load_server_versions(self):
        known = self.settings.get("known_server_versions", [])
        fallback = ["1.21.11", "1.21.10", "1.21.8", "1.21.4", "1.20.6"]
        initial = known if known else fallback
        self._populate_server_versions(initial)

        def fetch():
            try:
                data = http_get_json("https://api.purpurmc.org/v2/purpur/", timeout=10)
                versions = list(reversed(data.get("versions", [])))
                QTimer.singleShot(0, lambda: self._populate_server_versions(versions + known))
            except Exception as e:
                print(f"Error cargando versiones Purpur: {e}")

        threading.Thread(target=fetch, daemon=True).start()

    def _populate_server_versions(self, versions):
        current = self.server_version_combo.currentText().strip()
        seen = set()
        unique = []
        for v in versions:
            if v and v not in seen:
                seen.add(v)
                unique.append(v)

        self.server_version_combo.blockSignals(True)
        self.server_version_combo.clear()
        self.server_version_combo.addItems(unique)
        self.server_version_combo.blockSignals(False)

        target = current or self.settings.get("server_version") or ""
        if target and target in unique:
            self.server_version_combo.setCurrentText(target)
        elif target:
            self.server_version_combo.setEditText(target)

        self.refresh_server_tab()

    def on_server_version_changed(self, text):
        text = text.strip()
        self.settings["server_version"] = text
        self.save_settings()
        self._update_java_info_label(text)
        self.refresh_server_tab()

    def _update_java_info_label(self, mc_version):
        if not mc_version:
            self.java_info_label.setText("💡 Java requerido: (elige una versión)")
            return
        try:
            java_ver = get_required_java(mc_version)
            java_exe = os.path.join(self.java_base_dir, java_ver, "r", "bin", "java.exe")
            if os.path.exists(java_exe):
                self.java_info_label.setText(
                    f"☕ Java requerido: Java {java_ver} (ya instalado)"
                )
            else:
                self.java_info_label.setText(
                    f"☕ Java requerido: Java {java_ver} (se descargará al instalar)"
                )
        except Exception as e:
            self.java_info_label.setText(f"☕ Java requerido: (error: {e})")

    def on_server_ram_changed(self, text):
        try:
            self.settings["server_ram"] = int(text.split()[0])
            self.save_settings()
        except Exception:
            pass

    def is_server_installed(self):
        jar = self.get_server_jar_path()
        return jar is not None and os.path.exists(jar)

    def refresh_server_tab(self):
        if self.server_running:
            self.server_main_button.setText("⏹ DETENER SERVIDOR")
            self.server_main_button.setEnabled(True)
            self.server_status.setText("🟢 Servidor en ejecución")
            return

        v = self.server_version_combo.currentText().strip()
        server_type = self.server_type_combo.currentText()

        if not v:
            self.server_main_button.setText("⬇ INSTALAR SERVIDOR")
            self.server_main_button.setEnabled(False)
            self.server_status.setText("Selecciona o escribe una versión para empezar")
            return

        if self.is_server_installed():
            self.server_main_button.setText("▶ ARRANCAR SERVIDOR")
            self.server_main_button.setEnabled(True)
            java_ver = get_required_java(v)
            self.server_status.setText(
                f"✅ Servidor {server_type} {v} listo (Java {java_ver})"
            )
        else:
            self.server_main_button.setText("⬇ INSTALAR SERVIDOR")
            self.server_main_button.setEnabled(True)
            self.server_status.setText(
                f"📥 Servidor {server_type} {v} no instalado"
            )

    def server_main_action(self):
        if self.server_running:
            self.stop_server()
        elif self.is_server_installed():
            self.start_server()
        else:
            self.install_server()

    # ---------- INSTALAR SERVIDOR ----------
    def install_server(self):
        v = self.server_version_combo.currentText().strip()
        if not v:
            QMessageBox.warning(self, "Aviso", "Selecciona o escribe una versión primero.")
            return

        server_type = self.server_type_combo.currentText()

        # Validar solo si es Purpur (la API de Vanilla no necesita esta validación,
        # porque las versiones vienen del manifiesto oficial)
        if server_type == "Purpur":
            try:
                http_get_json(f"https://api.purpurmc.org/v2/purpur/{v}", timeout=8)
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    QMessageBox.critical(
                        self, "Versión inválida",
                        f"❌ La versión '{v}' no existe en Purpur.\n\n"
                        "Revisa la ortografía o prueba con otra versión."
                    )
                else:
                    QMessageBox.critical(
                        self, "Error de red",
                        f"No se pudo contactar la API de Purpur (HTTP {e.code})."
                    )
                return
            except Exception as e:
                QMessageBox.critical(
                    self, "Error de red",
                    f"No se pudo verificar la versión:\n{e}"
                )
                return

        required_java = get_required_java(v)
        java_exe = os.path.join(self.java_base_dir, required_java, "r", "bin", "java.exe")

        if not os.path.exists(java_exe):
            # Descargar Java primero
            self.server_main_button.setEnabled(False)
            self.server_main_button.setText("⏳ DESCARGANDO JAVA...")
            self.server_progress.setValue(0)
            self.server_status.setText(f"📥 Descargando Java {required_java}...")
            self.server_log.clear()
            self.append_server_log(f"=== Instalando Java {required_java} ===\n")

            self.java_download_thread = JavaDownloadThread(required_java, self.java_base_dir)
            self.java_download_thread.progress_updated.connect(self.server_progress.setValue)
            self.java_download_thread.status_updated.connect(self.server_status.setText)
            self.java_download_thread.finished.connect(
                lambda ok, err: self.on_java_download_finished(ok, err, v)
            )
            self.java_download_thread.start()
            return

        # ✅ Java ya existe → descargar el servidor directamente
        self._download_server(v)


    # ============================================================
    # Método APARTE (fuera de install_server, al mismo nivel)
    # ============================================================
    def _download_server(self, v):
        """Bifurca entre Purpur y Vanilla según el selector."""
        server_type = self.server_type_combo.currentText()
        if server_type == "Purpur":
            self._download_purpur(v)
        else:
            self._download_vanilla(v)

    def on_java_download_finished(self, success, error_msg, server_version):
        if success:
            self.append_server_log("✅ Java listo. Continuando con el servidor...\n")
            self.server_progress.setValue(0)
            self._download_purpur(server_version)
        else:
            self.server_progress.setValue(0)
            self.server_main_button.setEnabled(True)
            self.append_server_log(f"❌ Error descargando Java: {error_msg}")
            QMessageBox.critical(
                self, "Error Java",
                f"❌ No se pudo descargar Java:\n{error_msg}"
            )
            self.refresh_server_tab()
            self._update_java_info_label(server_version)

    def _download_purpur(self, v):
        self.server_main_button.setEnabled(False)
        self.server_main_button.setText("⏳ DESCARGANDO...")
        self.server_progress.setValue(0)
        self.server_status.setText(f"📥 Instalando servidor {v}...")
        self.append_server_log(f"=== Instalando servidor Purpur {v} ===\n")

        self.server_download_thread = ServerDownloadThread(v, self.get_current_server_dir())
        self.server_download_thread.progress_updated.connect(self.server_progress.setValue)
        self.server_download_thread.status_updated.connect(self.server_status.setText)
        self.server_download_thread.log_message.connect(self.append_server_log)
        self.server_download_thread.finished.connect(self.on_server_download_finished)
        self.server_download_thread.start()
        pass

    def _download_vanilla(self, v):
        """Descarga el servidor Vanilla con QThread (señales correctas)."""
        self.server_main_button.setEnabled(False)
        self.server_main_button.setText("⏳ DESCARGANDO...")
        self.server_progress.setValue(0)
        self.server_status.setText(f"📥 Descargando Vanilla {v}...")
        self.append_server_log(f"=== Instalando servidor Vanilla {v} ===\n")

        self.vanilla_download_thread = VanillaDownloadThread(v, self.get_current_server_dir())
        self.vanilla_download_thread.progress_updated.connect(self.server_progress.setValue)
        self.vanilla_download_thread.status_updated.connect(self.server_status.setText)
        self.vanilla_download_thread.log_message.connect(self.append_server_log)
        self.vanilla_download_thread.finished_download.connect(self.on_server_download_finished)
        self.vanilla_download_thread.start()

    def on_server_download_finished(self, success, error_msg):
        self.server_main_button.setEnabled(True)
        if success:
            v = self.server_version_combo.currentText().strip()
            known = self.settings.get("known_server_versions", [])
            if v and v not in known:
                known.append(v)
                self.settings["known_server_versions"] = known
                self.save_settings()

            self.server_progress.setValue(100)
            self.append_server_log("\n✅ Instalación completada.")
            self._update_java_info_label(v)
            QMessageBox.information(
                self, "Servidor instalado",
                "✅ El servidor se ha instalado correctamente.\n\n"
                "Presiona 'ARRANCAR SERVIDOR' para arrancarlo."
            )
        else:
            self.server_progress.setValue(0)
            self.append_server_log(f"\n❌ Error: {error_msg}")
            QMessageBox.critical(self, "Error", f"❌ {error_msg}")
        self.refresh_server_tab()

    # ---------- ARRANCAR SERVIDOR ----------
    def start_server(self):
        if self.server_running:
            return
        if not self.is_server_installed():
            QMessageBox.warning(self, "Aviso", "El servidor no está instalado.")
            return

        v = self.server_version_combo.currentText().strip()
        required_java = get_required_java(v)
        java_path = os.path.join(self.java_base_dir, required_java, "r", "bin", "java.exe")

        if not os.path.exists(java_path):
            QMessageBox.critical(
                self, "Java no instalado",
                f"Esta versión requiere Java {required_java} y no está instalado.\n\n"
                "Pulsa 'INSTALAR SERVIDOR' de nuevo para descargarlo."
            )
            return

        self._actually_start_server(java_path, required_java)

    def _actually_start_server(self, java_path: str, java_ver: str):
        jar_name = os.path.basename(self.get_server_jar_path())
        ram = self.settings.get("server_ram", 4)
        xms = min(ram, 4)

        cmd = [
            java_path,
            f"-Xmx{ram}G",
            f"-Xms{xms}G",
            "-jar", jar_name,
            "nogui"
        ]

        try:
            creationflags = 0
            if os.name == "nt":
                # Nueva sesión de proceso: permite matar el árbol completo
                creationflags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP

            self.server_process = subprocess.Popen(
                cmd,
                cwd=self.get_current_server_dir(),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding="utf-8",
                errors="replace",
                creationflags=creationflags,
            )
            self.server_running = True
            self.append_server_log(
                f"=== Servidor iniciado (Java {java_ver}, RAM: {ram}G) ===\n"
            )

            self.server_reader = ServerReaderThread(self.server_process)
            self.server_reader.line_received.connect(self.append_server_log)
            self.server_reader.process_ended.connect(self.on_server_ended)
            self.server_reader.start()

            self._update_music_state()
            self.refresh_server_tab()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo lanzar el servidor:\n{e}")
            self.server_running = False
            self.refresh_server_tab()
            self._update_music_state()

    def _kill_process_tree(self, process):
        """Mata el proceso y todos sus hijos (Windows usa taskkill /T)."""
        if process is None:
            return
        if process.poll() is not None:
            return
        try:
            if os.name == "nt":
                # /T mata árbol completo, /F fuerza, /PID el proceso
                subprocess.call(
                    ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            else:
                process.kill()
        except Exception as e:
            print(f"Error matando proceso: {e}")
        finally:
            try:
                process.wait(timeout=5)
            except Exception:
                pass

    def append_server_log(self, line):
        self.server_log.appendPlainText(line)

    def stop_server(self):
        if not self.server_running or not self.server_process:
            return
        reply = QMessageBox.question(
            self, "Detener servidor",
            "¿Detener el servidor?\n\nSe guardará el mundo y se cerrará limpiamente.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        self.server_main_button.setEnabled(False)
        self.server_status.setText("⏳ Deteniendo servidor...")

        try:
            if self.server_process.stdin:
                self.server_process.stdin.write("stop\n")
                self.server_process.stdin.flush()
        except Exception as e:
            print(f"Error enviando stop: {e}")

        def force_kill():
            if self.server_process and self.server_process.poll() is None:
                self.append_server_log("[Launcher] Forzando cierre del servidor...")
                self._kill_process_tree(self.server_process)

        QTimer.singleShot(15000, force_kill)  # 15s en vez de 20s

    def on_server_ended(self, exit_code):
        self.server_running = False
        self.server_process = None
        self.append_server_log(f"\n=== Servidor terminado (código {exit_code}) ===")
        self.refresh_server_tab()
        self._update_music_state()

    # ---------- GEYSER ----------
    def auto_update_geyser_on_start(self):
        def worker():
            try:
                purpur_dir = os.path.join(self.server_dir, "purpur")
                plugin_dir = os.path.join(purpur_dir, "plugins")
                os.makedirs(plugin_dir, exist_ok=True)

                local = load_geyser_version(purpur_dir)
                latest = get_latest_geyser_version()

                if latest is None:
                    self.api_status_msg = "⚠️ Sin conexión a la API de GeyserMC"
                    QTimer.singleShot(0, self.update_api_status_display)
                    return

                geyser_exists = os.path.exists(os.path.join(plugin_dir, "Geyser-Spigot.jar"))

                if local == latest and geyser_exists:
                    self.api_status_msg = f"✅ Geyser/Floodgate al día ({latest})"
                    QTimer.singleShot(0, self.update_api_status_display)
                    return

                info = download_geyser_floodgate(plugin_dir, None)
                if info:
                    save_geyser_version(purpur_dir, info)
                    self.api_status_msg = f"✅ Geyser/Floodgate actualizados a {info}"
                else:
                    self.api_status_msg = "⚠️ No se pudo actualizar Geyser/Floodgate"
                QTimer.singleShot(0, self.update_api_status_display)
            except Exception as e:
                self.api_status_msg = f"⚠️ Error al actualizar Geyser: {e}"
                QTimer.singleShot(0, self.update_api_status_display)

        threading.Thread(target=worker, daemon=True).start()

    def update_api_status_display(self):
        if hasattr(self, "api_status_label"):
            self.api_status_label.setText(self.api_status_msg)

    # ============================================================
    # RED
    # ============================================================
    def build_network_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setSpacing(1)
        layout.setContentsMargins(14, 14, 14, 14)

        info_label = QLabel(
            "🌐 Direcciones para conectarse a tu servidor.\n"
            "El crossplay Java ↔ Bedrock es posible gracias a Geyser/Floodgate."
        )
        info_label.setWordWrap(True)
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setStyleSheet("color: #a8d8ea; padding: 4px; font-size: 12px;")
        layout.addWidget(info_label)

        panel_java, content_java = self.make_panel("☕ Java Edition")
        self.java_ipv4_value = self._make_copy_row(
            content_java, "IPv4:", "Consultando...", self.copy_java_ipv4
        )
        self.java_ipv6_value = self._make_copy_row(
            content_java, "IPv6:", "Consultando...", self.copy_java_ipv6
        )
        layout.addWidget(panel_java)

        panel_bedrock, content_bedrock = self.make_panel("📱 Bedrock Edition (PC / Móvil / Consola)    PUERTO: 19132")
        self.bedrock_ipv4_value = self._make_copy_row(
            content_bedrock, "IPv4:", "Consultando...", self.copy_bedrock_ipv4
        )
        self.bedrock_ipv6_value = self._make_copy_row(
            content_bedrock, "IPv6:", "Consultando...", self.copy_bedrock_ipv6
        )
        layout.addWidget(panel_bedrock)

        self.api_status_label = QLabel("")
        self.api_status_label.setObjectName("status_info")
        self.api_status_label.setWordWrap(True)
        layout.addWidget(self.api_status_label)

        info_footer = QLabel(
            "ℹ️ Las direcciones se consultan al abrir el launcher.\n"
            "Geyser/Floodgate se actualizan automáticamente al iniciar.\n"
            "Si cambia tu IP pública o hay nueva versión, reinicia el launcher."
        )
        info_footer.setWordWrap(True)
        info_footer.setObjectName("ram_note")
        info_footer.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_footer)

        layout.addStretch()

    def _make_copy_row(self, parent_layout, label_text, initial_value, copy_callback):
        row = QHBoxLayout()
        row.setSpacing(8)

        lbl = QLabel(label_text)
        lbl.setObjectName("field_label")
        lbl.setFixedWidth(50)
        row.addWidget(lbl)

        value_lbl = QLabel(initial_value)
        value_lbl.setObjectName("ip_display")
        value_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        row.addWidget(value_lbl, stretch=1)

        btn = QPushButton("📋")
        btn.setObjectName("copy_button")
        btn.setToolTip("Copiar al portapapeles")
        btn.clicked.connect(copy_callback)
        row.addWidget(btn)

        parent_layout.addLayout(row)
        return value_lbl

    def _copy_to_clipboard(self, text):
        if not text or text in ("Consultando...", "(no disponible)", "(solo IPv4)"):
            QMessageBox.information(self, "Nada que copiar", "Todavía no hay datos disponibles.")
            return
        QApplication.clipboard().setText(text)
        QMessageBox.information(self, "Copiado", f"✅ Copiado al portapapeles:\n\n{text}")

    def copy_java_ipv4(self):
        self._copy_to_clipboard(self.java_ipv4_value.text())

    def copy_java_ipv6(self):
        self._copy_to_clipboard(self.java_ipv6_value.text())

    def copy_bedrock_ipv4(self):
        self._copy_to_clipboard(self.bedrock_ipv4_value.text())

    def copy_bedrock_ipv6(self):
        self._copy_to_clipboard(self.bedrock_ipv6_value.text())

    def _load_ip_once(self):
        for lbl in (self.java_ipv4_value, self.java_ipv6_value,
                    self.bedrock_ipv4_value, self.bedrock_ipv6_value):
            lbl.setText("Consultando...")

        task = IPLookupTask()
        task.signals.result_ready.connect(self.on_ip_ready)
        task.signals.error_occurred.connect(self.on_ip_error)
        self.thread_pool.start(task)

    def on_ip_ready(self, ipv4, ipv6):
        if ipv4 and ipv4 not in ("(no disponible)",):
            self.java_ipv4_value.setText(f"{ipv4}:25565")
        else:
            self.java_ipv4_value.setText("(no disponible)")

        if ipv6 and ipv6 not in ("(solo IPv4)", "(no disponible)"):
            self.java_ipv6_value.setText(f"[{ipv6}]:25565")
        else:
            self.java_ipv6_value.setText("(no disponible)")

        if ipv4 and ipv4 not in ("(no disponible)",):
            self.bedrock_ipv4_value.setText(ipv4)
        else:
            self.bedrock_ipv4_value.setText("(no disponible)")

        if ipv6 and ipv6 not in ("(solo IPv4)", "(no disponible)"):
            self.bedrock_ipv6_value.setText(ipv6)
        else:
            self.bedrock_ipv6_value.setText("(no disponible)")

        if not self.api_status_msg:
            self.api_status_msg = "✅ IPs consultadas correctamente"
            self.update_api_status_display()

    def on_ip_error(self, error_msg):
        for lbl in (self.java_ipv4_value, self.java_ipv6_value,
                    self.bedrock_ipv4_value, self.bedrock_ipv6_value):
            lbl.setText("(no disponible)")
        self.api_status_msg = f"⚠️ Error de red: {error_msg}"
        self.update_api_status_display()

    # ============================================================
    # SKIN DE SERVIDOR
    # ============================================================
    def build_skin_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setSpacing(8)
        layout.setContentsMargins(14, 0, 14, 14)

        header = QLabel(
            "🎨 Pega la URL directa de una skin PNG (64×64). "
            "Usa las flechas para navegar entre tus skins."
        )
        header.setWordWrap(True)
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("color: #a8d8ea; padding: 2px; font-size: 12px;")
        layout.addWidget(header)

        # ---- Panel de añadir URL ----
        panel_up, content_up = self.make_panel("🔗 Añadir skin desde URL")

        url_row = QHBoxLayout()
        url_row.setSpacing(8)

        self.skin_url_input = QLineEdit()
        self.skin_url_input.setPlaceholderText("https://ejemplo.com/skin.png")
        self.skin_url_input.returnPressed.connect(self.add_skin_from_url)
        url_row.addWidget(self.skin_url_input, stretch=1)

        btn_paste = QPushButton("📋")
        btn_paste.setObjectName("copy_button")
        btn_paste.setToolTip("Pegar desde el portapapeles")
        btn_paste.clicked.connect(self.paste_url_from_clipboard)
        url_row.addWidget(btn_paste)

        btn_add = QPushButton("➕ Añadir")
        btn_add.setObjectName("refresh_button")
        btn_add.clicked.connect(self.add_skin_from_url)
        url_row.addWidget(btn_add)

        content_up.addLayout(url_row)

        self.skin_url_status = QLabel("Pega una URL directa a un PNG de skin (64×64 o 64×32).")
        self.skin_url_status.setObjectName("ram_note")
        self.skin_url_status.setWordWrap(True)
        content_up.addWidget(self.skin_url_status)

        layout.addWidget(panel_up)

        # ---- Panel de previsualización ----
        panel_view, content_view = self.make_panel("🔍 Previsualización")

        grid = QGridLayout()
        grid.setSpacing(6)
        grid.setColumnStretch(1, 1)

        # --- Fila 0: flechas + vistas ---
        self.btn_skin_prev = QPushButton("◀")
        self.btn_skin_prev.setObjectName("refresh_button")
        self.btn_skin_prev.setFixedSize(40, 40)
        self.btn_skin_prev.setToolTip("Skin anterior")
        self.btn_skin_prev.clicked.connect(self.prev_skin)
        grid.addWidget(self.btn_skin_prev, 0, 0, alignment=Qt.AlignVCenter)

        views_row = QHBoxLayout()
        views_row.setSpacing(20)

        front_col = QVBoxLayout()
        front_col.setSpacing(4)
        front_lbl = QLabel("Frente")
        front_lbl.setAlignment(Qt.AlignCenter)
        front_lbl.setStyleSheet("color: #a8d8ea; font-size: 11px; font-weight: bold;")
        front_col.addWidget(front_lbl)

        self.skin_preview_front = QLabel("Sin skin")
        self.skin_preview_front.setFixedSize(155, 155)
        self.skin_preview_front.setAlignment(Qt.AlignCenter)
        self.skin_preview_front.setStyleSheet(
            "background: rgba(0,0,0,0.4); border-radius: 8px; "
            "border: 2px solid rgba(0,168,204,0.5); color: #666;"
        )
        front_col.addWidget(self.skin_preview_front)
        views_row.addLayout(front_col)

        back_col = QVBoxLayout()
        back_col.setSpacing(4)
        back_lbl = QLabel("Atrás")
        back_lbl.setAlignment(Qt.AlignCenter)
        back_lbl.setStyleSheet("color: #a8d8ea; font-size: 11px; font-weight: bold;")
        back_col.addWidget(back_lbl)

        self.skin_preview_back = QLabel("Sin skin")
        self.skin_preview_back.setFixedSize(155, 155)
        self.skin_preview_back.setAlignment(Qt.AlignCenter)
        self.skin_preview_back.setStyleSheet(
            "background: rgba(0,0,0,0.4); border-radius: 8px; "
            "border: 2px solid rgba(0,168,204,0.5); color: #666;"
        )
        back_col.addWidget(self.skin_preview_back)
        views_row.addLayout(back_col)

        grid.addLayout(views_row, 0, 1)

        self.btn_skin_next = QPushButton("▶")
        self.btn_skin_next.setObjectName("refresh_button")
        self.btn_skin_next.setFixedSize(40, 40)
        self.btn_skin_next.setToolTip("Siguiente skin")
        self.btn_skin_next.clicked.connect(self.next_skin)
        grid.addWidget(self.btn_skin_next, 0, 2, alignment=Qt.AlignVCenter)

        # --- Fila 1: 📋 (izq) y 🗑 (der) ---
        self.btn_skin_copy = QPushButton("📋")
        self.btn_skin_copy.setObjectName("copy_button")
        self.btn_skin_copy.setToolTip("Copiar comando /skin url ...")
        self.btn_skin_copy.setFixedSize(40, 40)
        self.btn_skin_copy.clicked.connect(self.copy_current_skin)
        self.btn_skin_copy.setEnabled(False)
        grid.addWidget(self.btn_skin_copy, 1, 0, alignment=Qt.AlignLeft)

        self.btn_skin_delete = QPushButton(" 🗑 ")
        self.btn_skin_delete.setObjectName("delete_button")
        self.btn_skin_delete.setToolTip("Eliminar esta skin de la lista")
        self.btn_skin_delete.setFixedSize(60, 60)
        self.btn_skin_delete.clicked.connect(self.delete_current_skin)
        self.btn_skin_delete.setEnabled(False)
        grid.addWidget(self.btn_skin_delete, 1, 2, alignment=Qt.AlignRight)

        # --- Fila 2: (x/x) a la izq, nombre a la der ---
        self.skin_index_label = QLabel("—")
        self.skin_index_label.setStyleSheet(
            "color: #00d4ff; font-size: 13px; font-weight: bold; padding: 2px;"
        )
        grid.addWidget(self.skin_index_label, 2, 0, alignment=Qt.AlignLeft)

        content_view.addLayout(grid)
        layout.addWidget(panel_view)
        layout.addStretch()

        # Cargar las skins al entrar a la pestaña
        QTimer.singleShot(200, self.refresh_skins_view)

    def refresh_skins_view(self):
        """Actualiza el índice actual y refresca la previsualización."""
        skins = self.settings.get("my_skins", [])
        if self.current_skin_index >= len(skins):
            self.current_skin_index = max(0, len(skins) - 1)
        if self.current_skin_index < 0:
            self.current_skin_index = 0
        self.render_current_skin()

    def _on_tab_changed(self, index):
        """Cuando se cambia a la pestaña Skin, refresca la vista."""
        if index == self.tabs.indexOf(self.skin_tab):
            QTimer.singleShot(50, self.refresh_skins_view)    

    def render_current_skin(self):
        """Descarga la skin actual y renderiza las vistas frontal y trasera."""
        skins = self.settings.get("my_skins", [])

        if not skins:
            self.skin_preview_front.setText("Sin skins")
            self.skin_preview_front.setPixmap(QPixmap())
            self.skin_preview_back.setText("Sin skins")
            self.skin_preview_back.setPixmap(QPixmap())
            self.skin_index_label.setText("—")
            self.btn_skin_prev.setEnabled(False)
            self.btn_skin_next.setEnabled(False)
            self.btn_skin_copy.setEnabled(False)
            self.btn_skin_delete.setEnabled(False)
            return

        # Corregir índice fuera de rango
        if self.current_skin_index < 0:
            self.current_skin_index = 0
        if self.current_skin_index >= len(skins):
            self.current_skin_index = len(skins) - 1

        skin = skins[self.current_skin_index]

        # Actualizar info
        self.skin_index_label.setText(
            f"({self.current_skin_index + 1}/{len(skins)})"
        )
        self.btn_skin_prev.setEnabled(self.current_skin_index > 0)
        self.btn_skin_next.setEnabled(self.current_skin_index < len(skins) - 1)
        self.btn_skin_copy.setEnabled(True)
        self.btn_skin_delete.setEnabled(True)

        # Estado de carga
        self.skin_preview_front.setPixmap(QPixmap())
        self.skin_preview_front.setText("⏳ Cargando...")
        self.skin_preview_back.setPixmap(QPixmap())
        self.skin_preview_back.setText("⏳ Cargando...")

                # Descargar en thread
        thread = SkinFetchThread(skin["url"])
        thread.fetched.connect(self._on_skin_downloaded_for_preview)
        self._preview_threads.append(thread)
        thread.finished.connect(
            lambda t=thread: self._preview_threads.remove(t)
            if t in self._preview_threads else None
        )
        thread.start()

    def paste_url_from_clipboard(self):
        """Pega el contenido del portapapeles en el campo de URL."""
        text = QApplication.clipboard().text().strip()
        if text:
            self.skin_url_input.setText(text)
            self.skin_url_input.setFocus()

    def add_skin_from_url(self):
        """Valida la URL pegada y añade la skin a la lista."""
        url = self.skin_url_input.text().strip()

        if not url:
            QMessageBox.warning(self, "Aviso", "Pega una URL primero.")
            return

        if not url.startswith(("http://", "https://")):
            QMessageBox.warning(
                self, "URL inválida",
                "La URL debe empezar por http:// o https://"
            )
            return

        # Evitar duplicados
        skins = self.settings.get("my_skins", [])
        if any(s.get("url") == url for s in skins):
            QMessageBox.information(
                self, "Ya existe",
                "Esa URL ya está en tu lista."
            )
            return

        self.skin_url_status.setText("🔍 Validando URL...")
        self.skin_url_status.setStyleSheet("color: #00d4ff; font-weight: bold;")

        thread = SkinFetchThread(url)
        thread.fetched.connect(
            lambda u, data: self._on_url_validated(u, data)
        )
        self._preview_threads.append(thread)
        thread.finished.connect(
            lambda t=thread: self._preview_threads.remove(t)
            if t in self._preview_threads else None
        )
        thread.start()

    def _on_url_validated(self, url, data):
        """Comprueba que la imagen sea PNG válida y de dimensiones correctas."""
        if not data:
            self.skin_url_status.setText("❌ No se pudo descargar la imagen")
            self.skin_url_status.setStyleSheet("color: #e74c3c; font-weight: bold;")
            QMessageBox.critical(
                self, "Error de descarga",
                "No se pudo descargar la imagen desde esa URL.\n\n"
                "Comprueba que:\n"
                "• La URL apunta al archivo .png directamente\n"
                "• El enlace es público (sin login)\n"
                "• La imagen sigue existiendo"
            )
            return

        try:
            from PIL import Image
            import io

            img = Image.open(io.BytesIO(data))
            size = img.size

            if size not in [(64, 64), (64, 32)]:
                self.skin_url_status.setText(
                    f"❌ La imagen mide {size[0]}×{size[1]}, debe ser 64×64 o 64×32"
                )
                self.skin_url_status.setStyleSheet("color: #e74c3c; font-weight: bold;")
                QMessageBox.critical(
                    self, "Dimensiones incorrectas",
                    f"La imagen mide {size[0]}×{size[1]} píxeles.\n\n"
                    "Debe medir 64×64 (moderna) o 64×32 (clásica)."
                )
                return

        except Exception as e:
            self.skin_url_status.setText("❌ El archivo no es una imagen válida")
            self.skin_url_status.setStyleSheet("color: #e74c3c; font-weight: bold;")
            QMessageBox.critical(
                self, "Formato inválido",
                f"No se pudo leer la imagen como PNG:\n{e}"
            )
            return

        # Guardar en la lista
        nombre = url.split("/")[-1].split("?")[0] or "skin.png"
        skins = self.settings.get("my_skins", [])
        skins.append({
            "url": url,
            "name": nombre,
            "timestamp": time.time(),
        })
        self.settings["my_skins"] = skins
        self.save_settings()

        # Seleccionar la nueva
        self.current_skin_index = len(skins) - 1

        self.skin_url_status.setText(f"✅ Añadida: {nombre}")
        self.skin_url_status.setStyleSheet("color: #7fff7f; font-weight: bold;")
        self.skin_url_input.clear()

        self.refresh_skins_view()    

    def _on_skin_downloaded_for_preview(self, url, data):
        """Renderiza las vistas frontal y trasera desde los bytes descargados."""
        if not data:
            self.skin_preview_front.setText("❌ Error")
            self.skin_preview_back.setText("❌ Error")
            return

        try:
            from skinpy import Skin, Perspective
            from PIL import Image
            import io

            skin_image = Image.open(io.BytesIO(data)).convert("RGBA")
            skin = Skin.from_image(skin_image)

            persp_front = Perspective(x="left", y="front", z="up", scaling_factor=8)
            front_img = skin.to_isometric_image(persp_front)
            self._set_preview_pil(self.skin_preview_front, front_img)

            persp_back = Perspective(x="right", y="back", z="up", scaling_factor=8)
            back_img = skin.to_isometric_image(persp_back)
            self._set_preview_pil(self.skin_preview_back, back_img)

        except ImportError:
            self.skin_preview_front.setText("❌ Falta skinpy")
            self.skin_preview_back.setText("❌ Falta skinpy")
        except Exception as e:
            print(f"[SkinPreview] Error renderizando: {e}")
            self.skin_preview_front.setText("❌ Error")
            self.skin_preview_back.setText("❌ Error")

    def _set_preview_pil(self, label, pil_image):
        """Convierte una imagen PIL a QPixmap y la muestra."""
        import io
        try:
            buffer = io.BytesIO()
            pil_image.save(buffer, format="PNG")
            pixmap = QPixmap()
            pixmap.loadFromData(buffer.getvalue())
            if not pixmap.isNull():
                label.setPixmap(pixmap.scaled(
                    130, 130, Qt.KeepAspectRatio, Qt.SmoothTransformation
                ))
            else:
                label.setText("🖼️")
        except Exception as e:
            print(f"[SkinPreview] Error mostrando: {e}")
            label.setText("❌")

    def prev_skin(self):
        if self.current_skin_index > 0:
            self.current_skin_index -= 1
            self.render_current_skin()

    def next_skin(self):
        skins = self.settings.get("my_skins", [])
        if self.current_skin_index < len(skins) - 1:
            self.current_skin_index += 1
            self.render_current_skin()

    def copy_current_skin(self):
        skins = self.settings.get("my_skins", [])
        if 0 <= self.current_skin_index < len(skins):
            self.copy_skin_command(skins[self.current_skin_index]["url"])

    def delete_current_skin(self):
        skins = self.settings.get("my_skins", [])
        if 0 <= self.current_skin_index < len(skins):
            self.delete_skin(self.current_skin_index)

    def copy_skin_command(self, url):
        comando = f'/skin url "{url}"'
        QApplication.clipboard().setText(comando)
        QMessageBox.information(
            self, "Copiado",
            f"✅ Copiado al portapapeles:\n\n{comando}"
        )

    def delete_skin(self, index):
        skins = self.settings.get("my_skins", [])
        if index < 0 or index >= len(skins):
            return

        skin = skins[index]
        reply = QMessageBox.question(
            self, "Eliminar skin",
            f"¿Quieres quitar esta skin de la lista?\n\n{skin['url']}\n\n"
            "Solo se elimina de tu lista local. El archivo en Catbox sigue ahí.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        skins.pop(index)
        self.settings["my_skins"] = skins
        self.save_settings()
        self.refresh_skins_view()

    # ============================================================
    # MODS / PLUGINS
    # ============================================================
    def build_mods_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setSpacing(8)
        layout.setContentsMargins(14, 14, 14, 14)

        header = QLabel(
            "🧩 Añade plugins de Spigot (.jar). "
            "Puedes activarlos o desactivarlos sin reiniciar el servidor."
        )
        header.setWordWrap(True)
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("color: #a8d8ea; padding: 2px; font-size: 12px;")
        layout.addWidget(header)

        # Panel de añadir plugin
        panel_up, content_up = self.make_panel("➕ Añadir plugin")

        row = QHBoxLayout()
        row.setSpacing(8)

        self.plugin_source_combo = QComboBox()
        self.plugin_source_combo.addItems(["Desde archivo...", "Desde URL..."])
        self.plugin_source_combo.currentTextChanged.connect(self.on_plugin_source_changed)
        row.addWidget(self.plugin_source_combo, stretch=1)

        self.plugin_path_input = QLineEdit()
        self.plugin_path_input.setPlaceholderText("Ruta del archivo .jar")
        self.plugin_path_input.setVisible(True)
        row.addWidget(self.plugin_path_input, stretch=2)

        btn_browse = QPushButton("📁")
        btn_browse.setObjectName("copy_button")
        btn_browse.setToolTip("Seleccionar archivo .jar")
        btn_browse.clicked.connect(self.browse_plugin_file)
        btn_browse.setVisible(True)
        row.addWidget(btn_browse)

        btn_add = QPushButton("➕ Añadir")
        btn_add.setObjectName("refresh_button")
        btn_add.clicked.connect(self.add_plugin)
        row.addWidget(btn_add)

        content_up.addLayout(row)

        self.plugin_status_label = QLabel("Listo para añadir plugins.")
        self.plugin_status_label.setObjectName("ram_note")
        self.plugin_status_label.setWordWrap(True)
        content_up.addWidget(self.plugin_status_label)

        layout.addWidget(panel_up)

        # Lista de plugins
        panel_list, content_list = self.make_panel("📋 Plugins instalados")

        self.plugin_list_widget = QListWidget()
        self.plugin_list_widget.setStyleSheet("""
            QListWidget {
                background: rgba(0, 0, 0, 0.5);
                border: 2px solid rgba(0, 168, 204, 0.5);
                border-radius: 6px;
                color: #e0e0e0;
                font-size: 13px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid rgba(0, 168, 204, 0.2);
            }
            QListWidget::item:selected {
                background: rgba(0, 212, 255, 0.3);
                color: white;
            }
        """)
        content_list.addWidget(self.plugin_list_widget)

        # Botones de acción para el plugin seleccionado
        actions_row = QHBoxLayout()
        actions_row.setSpacing(10)
        actions_row.addStretch()

        self.btn_toggle_plugin = QPushButton("🔄 Activar/Desactivar")
        self.btn_toggle_plugin.setObjectName("refresh_button")
        self.btn_toggle_plugin.clicked.connect(self.toggle_selected_plugin)
        self.btn_toggle_plugin.setEnabled(False)
        actions_row.addWidget(self.btn_toggle_plugin)

        self.btn_delete_plugin = QPushButton("🗑 Eliminar")
        self.btn_delete_plugin.setObjectName("delete_button")
        self.btn_delete_plugin.setMinimumWidth(120)
        self.btn_delete_plugin.clicked.connect(self.delete_selected_plugin)
        self.btn_delete_plugin.setEnabled(False)
        actions_row.addWidget(self.btn_delete_plugin)

        actions_row.addStretch()
        content_list.addLayout(actions_row)

        layout.addWidget(panel_list)

        # Conectar selección de la lista
        self.plugin_list_widget.itemSelectionChanged.connect(self.on_plugin_selected)

        # Cargar plugins al mostrar la pestaña
        QTimer.singleShot(200, self.refresh_plugins_list)

    def on_plugin_source_changed(self, text):
        """Muestra u oculta los controles según el origen seleccionado."""
        is_file = text == "Desde archivo..."
        self.plugin_path_input.setVisible(is_file)
        self.plugin_path_input.setPlaceholderText(
            "Ruta del archivo .jar" if is_file else "https://ejemplo.com/plugin.jar"
        )
        # El botón de examinar solo se muestra para archivos
        for i in range(self.plugin_path_input.parent().layout().count()):
            w = self.plugin_path_input.parent().layout().itemAt(i).widget()
            if isinstance(w, QPushButton) and w.text() == "📁":
                w.setVisible(is_file)

    def browse_plugin_file(self):
        """Abre un diálogo para seleccionar un archivo .jar."""
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar plugin (.jar)", "",
            "Archivos JAR (*.jar)"
        )
        if ruta:
            self.plugin_path_input.setText(ruta)

    def get_plugins_dir(self):
        """Devuelve la ruta a la carpeta de plugins del servidor (solo Purpur)."""
        return os.path.join(self.server_dir, "purpur", "plugins")

    def refresh_plugins_list(self):
        """Carga la lista de plugins desde la carpeta plugins/."""
        self.plugin_list_widget.clear()
        plugins_dir = self.get_plugins_dir()

        if not os.path.exists(plugins_dir):
            self.plugin_status_label.setText("La carpeta de plugins no existe todavía. Instala un servidor primero.")
            return

        try:
            files = os.listdir(plugins_dir)
        except Exception as e:
            self.plugin_status_label.setText(f"Error al leer la carpeta: {e}")
            return

        plugin_files = [f for f in files if f.endswith((".jar", ".jar.disabled"))]

        if not plugin_files:
            self.plugin_status_label.setText("No hay plugins instalados.")
            return

        for f in sorted(plugin_files):
            item = QListWidgetItem()
            if f.endswith(".jar.disabled"):
                item.setText(f"❌ {f[:-9]} (desactivado)")
                item.setForeground(QColor("#888"))
            else:
                item.setText(f"✅ {f} (activado)")
                item.setForeground(QColor("#7fff7f"))
            item.setData(Qt.UserRole, f)
            self.plugin_list_widget.addItem(item)

        self.plugin_status_label.setText(f"{len(plugin_files)} plugin(s) encontrado(s).")
        self.on_plugin_selected()

    def on_plugin_selected(self):
        """Habilita o deshabilita los botones según la selección."""
        has_selection = len(self.plugin_list_widget.selectedItems()) > 0
        self.btn_toggle_plugin.setEnabled(has_selection)
        self.btn_delete_plugin.setEnabled(has_selection)

    def add_plugin(self):
        """Añade un plugin desde archivo o URL."""
        source = self.plugin_source_combo.currentText()
        path_or_url = self.plugin_path_input.text().strip()

        if not path_or_url:
            QMessageBox.warning(self, "Aviso", "Selecciona un archivo o pega una URL.")
            return

        plugins_dir = self.get_plugins_dir()
        os.makedirs(plugins_dir, exist_ok=True)

        if source == "Desde archivo...":
            if not os.path.isfile(path_or_url):
                QMessageBox.critical(self, "Error", "El archivo no existe.")
                return
            filename = os.path.basename(path_or_url)
            dest = os.path.join(plugins_dir, filename)

            if os.path.exists(dest):
                reply = QMessageBox.question(
                    self, "Ya existe",
                    f"El plugin {filename} ya existe. ¿Sobrescribir?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return

            try:
                shutil.copy2(path_or_url, dest)
                self.plugin_status_label.setText(f"✅ Plugin añadido: {filename}")
                self.plugin_path_input.clear()
                self.refresh_plugins_list()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo copiar el archivo:\n{e}")

        else:  # Desde URL
            # Descargar en un hilo para no bloquear la UI
            self.plugin_status_label.setText("📥 Descargando plugin...")

            def worker():
                try:
                    filename = path_or_url.split("/")[-1].split("?")[0]
                    if not filename.endswith(".jar"):
                        filename = "plugin.jar"
                    dest = os.path.join(plugins_dir, filename)
                    http_download(path_or_url, dest)
                    QTimer.singleShot(0, lambda: self._on_plugin_downloaded(filename))
                except Exception as e:
                    QTimer.singleShot(0, lambda: self._on_plugin_download_error(str(e)))

            threading.Thread(target=worker, daemon=True).start()

    def _on_plugin_downloaded(self, filename):
        self.plugin_status_label.setText(f"✅ Plugin descargado: {filename}")
        self.plugin_path_input.clear()
        self.refresh_plugins_list()

    def _on_plugin_download_error(self, error_msg):
        self.plugin_status_label.setText(f"❌ Error al descargar: {error_msg}")
        QMessageBox.critical(self, "Error", f"No se pudo descargar el plugin:\n{error_msg}")

    def toggle_selected_plugin(self):
        """Activa o desactiva el plugin seleccionado renombrando el archivo."""
        items = self.plugin_list_widget.selectedItems()
        if not items:
            return

        filename = items[0].data(Qt.UserRole)
        plugins_dir = self.get_plugins_dir()
        old_path = os.path.join(plugins_dir, filename)

        if not os.path.exists(old_path):
            QMessageBox.critical(self, "Error", "El archivo ya no existe.")
            self.refresh_plugins_list()
            return

        if filename.endswith(".jar"):
            new_filename = filename + ".disabled"
        elif filename.endswith(".jar.disabled"):
            new_filename = filename[:-9]  # Quita ".disabled"
        else:
            return

        new_path = os.path.join(plugins_dir, new_filename)

        try:
            os.rename(old_path, new_path)
            self.refresh_plugins_list()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo renombrar el archivo:\n{e}")

    def delete_selected_plugin(self):
        """Elimina el plugin seleccionado."""
        items = self.plugin_list_widget.selectedItems()
        if not items:
            return

        filename = items[0].data(Qt.UserRole)
        plugins_dir = self.get_plugins_dir()
        filepath = os.path.join(plugins_dir, filename)

        reply = QMessageBox.question(
            self, "Eliminar plugin",
            f"¿Eliminar permanentemente {filename}?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        try:
            os.remove(filepath)
            self.refresh_plugins_list()
            self.plugin_status_label.setText(f"🗑 {filename} eliminado.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo eliminar:\n{e}")

    # ============================================================
    # INFO / CRÉDITOS
    # ============================================================
    def build_info_tab(self, parent):
        # Contenedor con scroll por si no cabe todo
        outer = QVBoxLayout(parent)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                background: rgba(0,0,0,0.3); width: 8px; border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #00a8cc; border-radius: 4px; min-height: 30px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(10)
        layout.setContentsMargins(14, 14, 14, 14)

        # ---- Bloque autor ----
        panel_author, content_author = self.make_panel("👤 Creador")

        author_row = QHBoxLayout()
        author_row.setSpacing(20)

        # Foto (si existe assets/author.png)
        author_photo = QLabel()
        author_photo.setFixedSize(120, 120)
        author_photo.setAlignment(Qt.AlignCenter)
        author_photo.setStyleSheet(
            "background: rgba(0,0,0,0.4); border-radius: 60px; "
            "border: 2px solid rgba(0,168,204,0.6); color: #666;"
        )

        author_path = resource_path(os.path.join("assets", "author.png"))
        if os.path.exists(author_path):
            pixmap = QPixmap(author_path)
            if not pixmap.isNull():
                # Escalar y recortar circular (aproximado, con fondo redondeado)
                scaled = pixmap.scaled(
                    116, 116, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
                )
                author_photo.setPixmap(scaled)
        else:
            author_photo.setText("🖼️\nSin foto")

        author_row.addWidget(author_photo)

        author_info = QVBoxLayout()
        author_info.setSpacing(6)

        name_lbl = QLabel(LAUNCHER_AUTHOR)
        name_lbl.setStyleSheet(
            "color: #00d4ff; font-size: 22px; font-weight: bold; padding: 4px 0;"
        )
        author_info.addWidget(name_lbl)

        role_lbl = QLabel("Desarrollador y creador del proyecto TERRACRAFT")
        role_lbl.setWordWrap(True)
        role_lbl.setStyleSheet("color: #a8d8ea; font-size: 13px;")
        author_info.addWidget(role_lbl)

        author_info.addStretch()

        author_row.addLayout(author_info, stretch=1)
        content_author.addLayout(author_row)
        layout.addWidget(panel_author)

        # ---- Bloque versión ----
        panel_version, content_version = self.make_panel("Terrarianos Launcher")

        version_grid = QGridLayout()
        version_grid.setSpacing(10)
        version_grid.setColumnStretch(1, 1)

        # Fila con la versión actual
        version_lbl = QLabel("Versión:")
        version_lbl.setObjectName("field_label")
        version_grid.addWidget(version_lbl, 0, 0)

        version_val = QLabel(f"v{LAUNCHER_VERSION}")
        version_val.setStyleSheet("color: #00d4ff; font-size: 13px; font-weight: bold;")
        version_val.setTextInteractionFlags(Qt.TextSelectableByMouse)
        version_grid.addWidget(version_val, 0, 1)

        content_version.addLayout(version_grid)

        # Texto descriptivo del proyecto
        descripcion = QLabel(
            "Terrarianos Launcher es un proyecto personal creado para facilitar el acceso "
            "a Minecraft Java \n\n"
            "A como entiendo MINECRAFT o sus archivos son libres pero es como tener los "
            "ingredientes de un pastel pero no la receta o la guia de como encender el Horno. \n"
            "Cuando compras MINECRAFT, practicamente solo pagas por un CHEF que hace todo "
            "el TRABAJO. \n\n"
            "Este proyecto fue HECHO CON AMOR Y SIN FINES DE LUCRO, "
            "eres libre de hacer con el lo que quieras. \n\n"
            "Este proyecto nacion debido a 3 motivos Principales:\n\n"
            "1= Facilitar el Juego a usuarios que no cuentan con este o se les dificulta "
            "el adquirirlo . \n\n"
            "2= Facilitar compartir el juego facilmente con la menor cantidad de archivos "
            "gracias a que se desarrollo con la idea que el usuario final monte el Juego y "
            "esto gracias a que pesa menos de 1 MB sin incluir assets y mods opcionales. \n\n"
            "3= Facilitar archivos limpios y seguros al usuario Final dandole la oportunidad "
            "de mirar y analizar el codigo de cada archivo del Proyecto. \n\n"
            
        )
        descripcion.setWordWrap(True)
        descripcion.setTextInteractionFlags(Qt.TextSelectableByMouse)
        descripcion.setStyleSheet(
            "color: #e0e0e0; font-size: 12px; padding: 8px 4px; "
            "line-height: 160%;"
        )
        content_version.addWidget(descripcion)

        layout.addWidget(panel_version)

        # ---- Bloque librerías ----
        panel_libs, content_libs = self.make_panel("📚 Librerías Python y dependencias")

        libs_grid = QGridLayout()
        libs_grid.setSpacing(6)
        libs_grid.setColumnStretch(1, 1)

        librerias = [
            ("PySide6",              "Interfaz gráfica (Qt6)"),
            ("minecraft-launcher-lib", "Descarga y lanzamiento del cliente"),
            ("Pillow (PIL)",         "Procesamiento de imágenes y skins"),
            ("skinpy",               "Render 3D de skins (frente / atrás)"),
            ("urllib",               "Peticiones HTTP (stdlib)"),
            ("zipfile",              "Extracción de Java portable (stdlib)"),
            ("threading",            "Descargas en segundo plano (stdlib)"),
            ("subprocess",           "Gestión de procesos de Java (stdlib)"),
            ("json",                 "Configuración y API de Purpur (stdlib)"),
            ("shutil",               "Copiar y mover archivos (stdlib)"),
        ]

        for i, (nombre, descripcion) in enumerate(librerias):
            nombre_lbl = QLabel(nombre)
            nombre_lbl.setStyleSheet(
                "color: #00d4ff; font-size: 13px; font-weight: bold; "
                "font-family: 'Consolas', monospace; padding: 2px 0;"
            )
            nombre_lbl.setMinimumWidth(180)
            libs_grid.addWidget(nombre_lbl, i, 0)

            desc_lbl = QLabel(f"— {descripcion}")
            desc_lbl.setStyleSheet("color: #e0e0e0; font-size: 12px; padding: 2px 0;")
            desc_lbl.setWordWrap(True)
            libs_grid.addWidget(desc_lbl, i, 1)

        content_libs.addLayout(libs_grid)
        layout.addWidget(panel_libs)

        # ---- Bloque agradecimientos ----
        panel_thanks, content_thanks = self.make_panel("💖 Para TERRARIANOS:")

        thanks_text = QLabel(
            "Este Grupo me hizo quien soy ahora.\n\n"
            "MUCHAS GRACIAS AL GRUPO TERRARIANOS , ya que este me dio su confianza de ser "
            "ADMINISTRADOR y esto me llevo a desarrollar y aprender temas relacionados a "
            "PROGRAMACION y GRACIAS al ADMINISTRADOR Raven_117 quien fue quien confio en mi "
            "y me dio el ROL de ADMIN. \n\n"
            "FINALMENTE GRACIAS a TODOS \n\n"
            "Lo que FUE, ES y SERA el rumbo del SERVIDOR TERRARIANO es GRACIAS a TODOS,"
            "tanto en BUENOS como MALOS MOMENTOS \n\n"
            "GRACIAS"
        )
        thanks_text.setWordWrap(True)
        thanks_text.setStyleSheet("color: #a8d8ea; font-size: 12px; padding: 4px;")
        content_thanks.addWidget(thanks_text)
        layout.addWidget(panel_thanks)

        # ---- Botones ----
        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(10)
        buttons_row.addStretch()

        btn_github = QPushButton("  Ver código en GitHub")
        github_icon_path = resource_path(os.path.join("assets", "github.png"))
        if os.path.exists(github_icon_path):
            btn_github.setIcon(QIcon(github_icon_path))
            btn_github.setIconSize(QSize(20, 20))
        btn_github.setObjectName("refresh_button")
        btn_github.setToolTip("Abrir el repositorio del proyecto")
        btn_github.clicked.connect(self.open_github_link)
        buttons_row.addWidget(btn_github)

        btn_discord = QPushButton("💬 Unirse al Discord")
        btn_discord.setObjectName("refresh_button")
        btn_discord.clicked.connect(lambda: self.open_discord_link(None))
        buttons_row.addWidget(btn_discord)

        btn_copy = QPushButton("📋 Copiar info")
        btn_copy.setObjectName("refresh_button")
        btn_copy.clicked.connect(self.copy_launcher_info)
        buttons_row.addWidget(btn_copy)

        buttons_row.addStretch()
        layout.addLayout(buttons_row)

        layout.addStretch()

        scroll.setWidget(container)
        outer.addWidget(scroll)

    def _info_row(self, grid, row, label, value):
        """Añade una fila label: valor al grid."""
        lbl = QLabel(label)
        lbl.setObjectName("field_label")
        grid.addWidget(lbl, row, 0)

        val = QLabel(value)
        val.setStyleSheet("color: #e0e0e0; font-size: 13px;")
        val.setWordWrap(True)
        val.setTextInteractionFlags(Qt.TextSelectableByMouse)
        grid.addWidget(val, row, 1)

    def copy_launcher_info(self):
        """Copia la info del launcher al portapapeles."""
        info = (
            f"{LAUNCHER_NAME} v{LAUNCHER_VERSION}\n"
            f"Creado por: {LAUNCHER_AUTHOR}\n"
            f"Python: {sys.version.split()[0]}\n"
            f"Cliente: Minecraft Java vanilla\n"
            f"Servidor: Purpur / Vanilla\n"
            f"Java: 8 / 16 / 17 / 21 / 25 (auto)\n"
            f"\n"
            f"Librerías: PySide6, minecraft-launcher-lib, Pillow, skinpy, urllib"
        )
        QApplication.clipboard().setText(info)
        QMessageBox.information(self, "Copiado", "✅ Info copiada al portapapeles.")

    # ============================================================
    # ACCIONES: CARPETA Y ELIMINAR
    # ============================================================
    def open_launcher_folder(self):
        try:
            path = self.base_dir
            if os.name == "nt":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo abrir la carpeta:\n{e}")

    def open_github_link(self):
        """Abre el repositorio del proyecto en el navegador."""
        url = "https://github.com/TU_USUARIO/TU_REPOSITORIO"  # ← cambia por tu URL real
        QDesktopServices.openUrl(QUrl(url))

    def open_discord_link(self, event):
        """Abre el enlace de Discord en el navegador."""
        url = "https://discord.gg/3KgY7d4ZSW"  # ← cambia por tu link real
        QDesktopServices.openUrl(QUrl(url))

    def delete_client_version(self):
        version = self.version_combo.currentText().strip()
        if not version:
            QMessageBox.warning(self, "Aviso", "No hay ninguna versión seleccionada.")
            return

        version_dir = os.path.join(self.minecraft_dir, "versions", version)
        if not os.path.exists(version_dir):
            QMessageBox.information(
                self, "No está instalada",
                f"La versión '{version}' no está instalada en el cliente."
            )
            return

        reply = QMessageBox.question(
            self, "Eliminar versión del cliente",
            f"¿Eliminar la versión '{version}' del cliente?\n\n"
            f"Se borrará:\n{version_dir}\n\n"
            "Esto NO afecta al servidor.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        try:
            shutil.rmtree(version_dir)
            QMessageBox.information(
                self, "Eliminada",
                f"✅ La versión '{version}' se ha eliminado del cliente."
            )
            self.check_version_installed()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo eliminar la versión:\n{e}")

    def delete_server_version(self):
        version = self.server_version_combo.currentText().strip()
        if not version:
            QMessageBox.warning(self, "Aviso", "No hay ninguna versión seleccionada.")
            return

        server_type = self.server_type_combo.currentText()
        jar_path = self.get_server_jar_path()
        if not jar_path:
            return

        if not os.path.exists(jar_path):
            QMessageBox.information(
                self, "No está instalado",
                f"El servidor {server_type} {version} no está instalado."
            )
            return

        reply = QMessageBox.question(
            self, "Eliminar servidor",
            f"¿Eliminar el servidor {server_type} {version}?\n\n"
            f"Se borrará:\n{os.path.basename(jar_path)}\n\n"
            "El mundo (server/world/) NO se borra, pero el servidor no arrancará "
            "hasta que lo reinstales.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        try:
            os.remove(jar_path)
            QMessageBox.information(
                self, "Eliminado",
                f"✅ El servidor {server_type} {version} se ha eliminado."
            )
            self.refresh_server_tab()  # ← importante: refresca el botón
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo eliminar el servidor:\n{e}")

    # ============================================================
    # CLIENTE (lógica)
    # ============================================================
    def load_versions(self):
        try:
            versions = self.get_available_versions()
            self.version_combo.clear()
            self.version_combo.addItems(versions)
            if self.settings["version"] in versions:
                self.version_combo.setCurrentText(self.settings["version"])
            else:
                self.version_combo.setCurrentText(versions[0] if versions else "1.21.4")
        except Exception as e:
            print(f"Error cargando versiones: {e}")
            self.version_combo.addItems(["1.21.4", "1.21.3", "1.20.6"])
            self.version_combo.setCurrentText("1.21.4")

    def get_available_versions(self) -> List[str]:
        try:
            versions = minecraft_launcher_lib.utils.get_available_versions(self.minecraft_dir)
            version_list = [v["id"] for v in versions if v["type"] == "release"]
            if version_list:
                return version_list[:20]
        except Exception as e:
            print(f"Error obteniendo versiones: {e}")
        return ["1.21.4", "1.21.3", "1.20.6", "1.20.4"]

    def check_version_installed(self):
        version = self.version_combo.currentText()
        try:
            installed = minecraft_launcher_lib.utils.get_installed_versions(self.minecraft_dir)
            is_installed = any(v["id"] == version for v in installed)
            if is_installed:
                self.start_button.setText("▶ JUGAR")
                self.client_status.setText(f"✅ Versión {version} instalada")
            else:
                self.start_button.setText("⬇ DESCARGAR Y JUGAR")
                self.client_status.setText(f"📥 Versión {version} no instalada")
            return is_installed
        except Exception:
            self.start_button.setText("⬇ DESCARGAR Y JUGAR")
            return False

    def update_settings(self):
        self.settings["username"] = self.username_input.text()
        self.settings["version"] = self.version_combo.currentText()
        ram_text = self.ram_combo.currentText()
        try:
            self.settings["ram"] = int(ram_text.split()[0])
        except Exception:
            pass
        self.save_settings()

    def check_java(self):
        try:
            java_path = minecraft_launcher_lib.utils.get_java_executable()
            return bool(java_path)
        except Exception:
            return False

    def start_game(self):
        if self.client_process and self.client_process.poll() is None:
            QMessageBox.warning(self, "Aviso", "Minecraft ya está en ejecución.")
            return

        version = self.version_combo.currentText()
        username = self.username_input.text()
        ram = self.settings["ram"]

        if not self.check_java():
            reply = QMessageBox.question(
                self, "Java no encontrado",
                "Java no está instalado.\n¿Seleccionar javaw.exe manualmente?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                fp, _ = QFileDialog.getOpenFileName(self, "Seleccionar javaw.exe", "", "javaw.exe")
                if fp:
                    os.environ["JAVA_HOME"] = os.path.dirname(fp)
                else:
                    return
            else:
                return

        installed = minecraft_launcher_lib.utils.get_installed_versions(self.minecraft_dir)
        version_installed = any(v["id"] == version for v in installed)

        if not version_installed:
            self.start_button.setEnabled(False)
            self.start_button.setText("⏳ DESCARGANDO...")
            self.client_progress.setValue(0)
            self.client_status.setText(f"📥 Descargando {version}...")

            self.download_thread = DownloadThread(version, self.minecraft_dir)
            self.download_thread.progress_updated.connect(self.client_progress.setValue)
            self.download_thread.status_updated.connect(self.client_status.setText)
            self.download_thread.finished.connect(self.on_client_download_finished)
            self.download_thread.start()
            return

        self._launch_game(version, username, ram)

    def on_client_download_finished(self, success, error_msg):
        self.start_button.setEnabled(True)
        if success:
            self.client_status.setText("✅ Versión instalada")
            self.check_version_installed()
            QMessageBox.information(
                self, "Descarga completada",
                "✅ Versión instalada.\n\nPresiona 'JUGAR' para iniciar."
            )
        else:
            self.client_status.setText(f"❌ Error: {error_msg[:60]}")
            QMessageBox.critical(self, "Error", f"❌ {error_msg}")

    def _launch_game(self, version, username, ram):
        try:
            self.start_button.setEnabled(False)
            self.start_button.setText("⏳ INICIANDO...")
            self.client_progress.setValue(100)
            self.client_status.setText("🚀 Iniciando Minecraft...")

            options = {"username": username, "uuid": "0" * 32, "token": "0"}
            command = minecraft_launcher_lib.command.get_minecraft_command(
                version, self.minecraft_dir, options
            )

            if ram:
                jvm = [f"-Xmx{ram}G", f"-Xms{min(ram, 4)}G"]
                command = [command[0]] + jvm + command[1:]

            self.client_process = subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            self._update_music_state()
            self.client_status.setText("🟢 Minecraft en ejecución")

            QMessageBox.information(
                self,
                "¡Gracias por usar TERRACRAFT!",
                "🎮 El juego se abrirá en unos instantes.\n"
                "(Tardará unos segundos).\n\n"
                "El launcher seguirá abierto.\n"
                "Cuando cierres Minecraft, el botón volverá a 'JUGAR'.\n\n"
                "✨ ¡Gracias y que lo disfrutes! ✨"
            )

            watcher = ProcessWatcherTask(self.client_process)
            watcher.signals.finished.connect(self.on_client_closed)
            self.client_watcher = watcher
            self.thread_pool.start(watcher)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"❌ {e}")
            self.start_button.setEnabled(True)
            self.start_button.setText("▶ JUGAR")
            self._update_music_state()

    def on_client_closed(self):
        self.client_process = None
        self.start_button.setEnabled(True)
        self.start_button.setText("▶ JUGAR")
        self.client_progress.setValue(0)
        self.client_status.setText("✅ Listo")
        self._update_music_state()


# ============================================================
# MAIN
# ============================================================
def main():
    app = QApplication(sys.argv)

    icon_path = resource_path(os.path.join("assets", "icon.ico"))
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    else:
        png = resource_path(os.path.join("assets", "icon.png"))
        if os.path.exists(png):
            app.setWindowIcon(QIcon(png))

    window = TerrarianosLauncher()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
