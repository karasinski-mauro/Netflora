# -*- coding: utf-8 -*-
import os
import sys
import tempfile
import textwrap

from qgis.PyQt.QtCore import QSettings, Qt, QUrl
from qgis.PyQt.QtGui import QDesktopServices, QPixmap
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.core import QgsApplication, Qgis, QgsMessageLog

import importlib
import subprocess


def ensure_numpy():
    major, minor = sys.version_info[:2]
    if (major, minor) in [(3, 9), (3, 10), (3, 11)]:
        target = "numpy==1.26.4"
    elif (major, minor) == (3, 12):
        target = "numpy==2.0.2"
    else:
        target = "numpy"

    try:
        import numpy  # noqa: F401

        return True
    except Exception:
        pass

    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", target])
        importlib.invalidate_caches()
        import numpy  # noqa: F401

        return True
    except Exception as exc:
        QMessageBox.critical(
            None,
            "Netflora - NumPy missing",
            (
                "Failed to install NumPy automatically.\n"
                "Please open the OSGeo4W Shell and run:\n\n"
                f'  "{sys.executable}" -m pip install --upgrade {target}\n\n'
                f"Error: {exc}"
            ),
        )
        return False


def _log(message: str):
    try:
        QgsMessageLog.logMessage(message, "Netflora", level=Qgis.Info)
    except Exception:
        pass


def _plugin_root() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def _metadata_value(key: str, default: str = "") -> str:
    metadata_path = os.path.join(_plugin_root(), "metadata.txt")
    try:
        with open(metadata_path, "r", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith(f"{key}="):
                    return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return default


def _icon_file_url(filename: str) -> str:
    path = os.path.join(_plugin_root(), "common", "icons", filename)
    return QUrl.fromLocalFile(path).toString()


def _plugin_icon_pixmap():
    path = os.path.join(_plugin_root(), "icon.png")
    pixmap = QPixmap(path)
    return pixmap if not pixmap.isNull() else None


def _build_welcome_html() -> str:
    return textwrap.dedent(
        f"""
        <div style="font-family:Segoe UI, Arial, sans-serif; line-height:1.5; min-width:560px;">
          <div style="text-align:center; margin-bottom:16px;">
            <img src="{_icon_file_url('Netflora.png')}" width="140" style="margin:0 8px;">
            <img src="{_icon_file_url('Embrapa-Acre.png')}" width="140" style="margin:0 8px;">
            <img src="{_icon_file_url('Fundo-JBS.png')}" width="140" style="margin:0 8px;">
          </div>
          <h2 style="margin-bottom:8px;">Netflora</h2>
          <p>
            The Netflora Project involves the application of geotechnologies in forest automation
            and carbon stock mapping in native forest areas in Western Amazonia. It is an initiative
            developed by Embrapa Acre with sponsorship from the JBS Fund for the Amazon.
          </p>
          <p>
            Here we focus on the "Forest Inventory using drones" component. Drones and artificial
            intelligence are used to automate forest inventory stages for identifying strategic species.
            More than 50,000 hectares of forest areas have already been mapped to compose the Netflora dataset.
          </p>
          <p>
            <b>Author:</b> Mauro Alessandro Karasinski<br>
            <b>Institution:</b> Embrapa Acre<br>
            <b>Page:</b> <a href="https://www.embrapa.br/acre/netflora">https://www.embrapa.br/acre/netflora</a><br>
            <b>Support:</b> <a href="https://fundojbsamazonia.org/">https://fundojbsamazonia.org/</a>
          </p>
        </div>
        """
    ).strip()


def show_welcome_message_once():
    version = _metadata_value("version", "unknown").replace(".", "_")
    settings = QSettings()
    key = f"netflora/welcome_shown_{version}"
    if settings.value(key, False, type=bool):
        return

    box = QMessageBox()
    box.setWindowTitle("Welcome to Netflora")
    pixmap = _plugin_icon_pixmap()
    if pixmap is not None:
        box.setIconPixmap(pixmap.scaledToWidth(72, Qt.SmoothTransformation))
    box.setTextFormat(Qt.RichText)
    box.setText(_build_welcome_html())
    box.setStandardButtons(QMessageBox.Ok)
    box.exec()

    settings.setValue(key, True)


def _build_help_html(missing_pkg: str = "onnxruntime"):
    cmds_cpu = [
        "pip install --upgrade pip",
        "pip install matplotlib seaborn",
        "pip install onnxruntime",
    ]
    cmds_gpu = [
        "pip install --upgrade pip",
        "pip install matplotlib seaborn",
        "pip uninstall -y onnxruntime",
        "pip install onnxruntime-gpu==1.18.0",
    ]
    cmds_alt = [
        "pip install --upgrade pip",
        "pip install matplotlib seaborn",
        "pip install onnxruntime-directml",
        "pip install onnxruntime-openvino",
    ]

    pt = textwrap.dedent(
        f"""
        <h2>Dependencias externas necessarias</h2>
        <p>O Netflora precisa de bibliotecas Python (ex.: <code>{missing_pkg}</code>) que nao vem com o plugin.</p>
        <ol>
          <li>Abra o <b>OSGeo4W Shell</b>.</li>
          <li>Escolha apenas uma das opcoes abaixo, de acordo com o seu hardware:</li>
        </ol>
        <h3>1. Somente CPU</h3>
        <pre>{"\n".join(cmds_cpu)}</pre>
        <h3>2. GPU NVIDIA</h3>
        <pre>{"\n".join(cmds_gpu)}</pre>
        <h3>3. GPU Intel/AMD</h3>
        <pre>{"\n".join(cmds_alt)}</pre>
        <p>Depois da instalacao, reinicie o QGIS.</p>
        """
    )

    en = textwrap.dedent(
        f"""
        <h2>External dependencies required</h2>
        <p>Netflora needs Python packages (e.g. <code>{missing_pkg}</code>) which are not bundled with the plugin.</p>
        <ol>
          <li>Open the <b>OSGeo4W Shell</b>.</li>
          <li>Choose only one of the options below depending on your hardware:</li>
        </ol>
        <h3>1. CPU only</h3>
        <pre>{"\n".join(cmds_cpu)}</pre>
        <h3>2. NVIDIA GPU</h3>
        <pre>{"\n".join(cmds_gpu)}</pre>
        <h3>3. Intel/AMD GPU</h3>
        <pre>{"\n".join(cmds_alt)}</pre>
        <p>After installation, restart QGIS.</p>
        """
    )

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Netflora - Dependency guide</title>
<style>
body{{font-family:Segoe UI, Arial, sans-serif; margin:20px; line-height:1.55}}
pre{{background:#111;color:#eee;padding:12px;border-radius:8px;white-space:pre-wrap}}
</style>
</head>
<body>
<h1>Netflora - Dependency guide</h1>
{pt}
<hr>
{en}
</body></html>
"""


def open_help_html(missing_pkg: str = "onnxruntime"):
    html_doc = _build_help_html(missing_pkg=missing_pkg)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
    tmp.write(html_doc.encode("utf-8"))
    tmp.close()
    QDesktopServices.openUrl(QUrl.fromLocalFile(tmp.name))
    return tmp.name


def show_missing_dep_message(missing_pkg: str = "onnxruntime"):
    QMessageBox.warning(
        None,
        "Netflora - Missing dependencies",
        (
            f"The required component is not installed: '{missing_pkg}'.\n\n"
            "A guide will be opened with the steps to install it in the QGIS Python "
            "environment. After finishing, restart QGIS."
        ),
        QMessageBox.Ok,
    )


class NetfloraPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.provider = None

    def initGui(self):
        missing = None
        try:
            import onnxruntime  # noqa: F401
        except Exception:
            missing = "onnxruntime"

        try:
            from .netflora_provider import NetfloraProvider

            self.provider = NetfloraProvider()
            QgsApplication.processingRegistry().addProvider(self.provider)
            _log("Netflora provider registered.")
        except Exception as exc:
            QMessageBox.critical(None, "Netflora", f"Failed to register provider:\n{exc}")
            return

        show_welcome_message_once()

        if missing:
            _log(f"Dependency missing: {missing}")
            show_missing_dep_message(missing_pkg=missing)
            open_help_html(missing_pkg=missing)

    def unload(self):
        if self.provider is not None:
            try:
                QgsApplication.processingRegistry().removeProvider(self.provider)
            except Exception:
                pass
            self.provider = None
            _log("Netflora provider unregistered.")
