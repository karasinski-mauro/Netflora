# -*- coding: utf-8 -*-
import sys, tempfile, textwrap
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.PyQt.QtGui import QDesktopServices
from qgis.PyQt.QtCore import QUrl
from qgis.core import QgsApplication, Qgis, QgsMessageLog


import sys, subprocess, importlib

def ensure_numpy():
    major, minor = sys.version_info[:2]
    if (major, minor) in [(3,9),(3,10),(3,11)]:
        target = "numpy==1.26.4"
    elif (major, minor) == (3,12):
        target = "numpy==2.0.2"
    else:
        target = "numpy"  # fallback, pega o mais novo

    try:
        import numpy  # noqa
        return True
    except Exception:
        pass

    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", target])
        importlib.invalidate_caches()
        import numpy  # noqa
        return True
    except Exception as e:
        from qgis.PyQt.QtWidgets import QMessageBox
        QMessageBox.critical(
            None, "Netflora — NumPy missing",
            f"Failed to install NumPy automatically.\n"
            f"Please open the OSGeo4W Shell and run:\n\n"
            f'  "{sys.executable}" -m pip install --upgrade {target}\n\n'
            f"Error: {e}"
        )
        return False



def _log(msg: str):
    try:
        QgsMessageLog.logMessage(msg, "Netflora", level=Qgis.Info)
    except Exception:
        pass


# ---------- helpHTML ----------
def _build_help_html(missing_pkg: str = "onnxruntime"):
    py = sys.executable

    cmds_cpu = [
        f'pip install --upgrade pip',
        f'pip install matplotlib seaborn',
        f'pip install onnxruntime',  # só CPU
    ]
    cmds_gpu = [
        f'pip install --upgrade pip',
        f'pip install matplotlib seaborn',
        f'pip uninstall -y onnxruntime',   # remover CPU antes
        f'pip install onnxruntime-gpu==1.18.0',  # GPU NVIDIA
    ]
    cmds_alt = [
        f'pip install --upgrade pip',
        f'pip install matplotlib seaborn',
        f'pip install onnxruntime-directml',   # GPU Intel/AMD
        f'pip install onnxruntime-openvino',   # Intel OpenVINO
    ]

    cmd_block_cpu = "\n".join(cmds_cpu)
    cmd_block_gpu = "\n".join(cmds_gpu)
    cmd_block_alt = "\n".join(cmds_alt)

    pt = textwrap.dedent(f"""
    <h2>Dependências externas necessárias</h2>
    <p>O Netflora precisa de bibliotecas Python (ex.: <code>{missing_pkg}</code>) que <b>não</b> vêm com o plugin.</p>
    <ol>
      <li>Abra o <b>OSGeo4W Shell</b> (Menu Iniciar → OSGeo4W Shell).</li>
      <li>Escolha <b>APENAS UMA</b> das opções abaixo, de acordo com o seu hardware:</li>
    </ol>
    <h3>1. Somente CPU (mais lento, mas funciona em qualquer PC)</h3>
    <pre>{cmd_block_cpu}</pre>
    <h3>2. GPU NVIDIA (recomendado, muito mais rápido)</h3>
    <pre>{cmd_block_gpu}</pre>
    <h3>3. GPU Intel/AMD (opcional)</h3>
    <pre>{cmd_block_alt}</pre>
    <p>Depois de instalar, <b>reinicie o QGIS</b>.</p>
    """)

    en = textwrap.dedent(f"""
    <h2>External dependencies required</h2>
    <p>Netflora needs Python packages (e.g., <code>{missing_pkg}</code>) which are <b>not</b> bundled with the plugin.</p>
    <ol>
      <li>Open the <b>OSGeo4W Shell</b> (Start Menu → OSGeo4W Shell).</li>
      <li>Choose <b>ONLY ONE</b> of the options below, depending on your hardware:</li>
    </ol>
    <h3>1. CPU only (slower, but works everywhere)</h3>
    <pre>{cmd_block_cpu}</pre>
    <h3>2. NVIDIA GPU (recommended, much faster)</h3>
    <pre>{cmd_block_gpu}</pre>
    <h3>3. Intel/AMD GPU (optional)</h3>
    <pre>{cmd_block_alt}</pre>
    <p>After installation, <b>restart QGIS</b>.</p>
    """)

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Netflora — Instalação de dependências</title>
<style>
body{{font-family:Segoe UI, Arial, sans-serif; margin:20px; line-height:1.55}}
pre{{background:#111;color:#eee;padding:12px;border-radius:8px;white-space:pre-wrap}}
</style>
</head>
<body>
<h1>Netflora — Guia de instalação de dependências</h1>
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
        "Netflora — Dependências ausentes",
        (
            f"O componente necessário não está instalado: '{missing_pkg}'.\n\n"
            "Será aberto um guia com o passo a passo para instalar usando o "
            "Python do QGIS (OSGeo4W). Após concluir, reinicie o QGIS."
        ),
        QMessageBox.Ok
    )

# ---------- Plugin ----------
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
        except Exception as e:
            QMessageBox.critical(None, "Netflora", f"Failed to register provider:\n{e}")
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
