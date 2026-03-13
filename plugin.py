# -*- coding: utf-8 -*-
import sys
import tempfile
import textwrap

from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtGui import QDesktopServices
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
