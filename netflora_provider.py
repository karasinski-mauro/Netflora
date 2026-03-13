# -*- coding: utf-8 -*-
import os
from qgis.core import QgsProcessingProvider, QgsApplication, QgsMessageLog, Qgis
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QCoreApplication

from .flight_planner.alg_flight_planner import NetfloraFlightPlanner
from .detection.amazonia.madeireiros import DET_Amazonia_Madeireiros
from .detection.amazonia.nao_madeireiros import DET_Amazonia_NaoMadeireiros
from .detection.amazonia.palmeiras import DET_Amazonia_Palmeiras
from .detection.amazonia.ecologico import DET_Amazonia_Ecologico
from .detection.amazonia.acai_solteiro import DET_Amazonia_Acai_Solteiro
from .detection.amazonia.acai_touceira import DET_Amazonia_Acai_Touceira
from .detection.amazonia.castanheira import DET_Amazonia_Castanheira
from .detection.amazonia.invasora import DET_Amazonia_Invasora
from .detection.amazonia.geral import DET_Amazonia_Geral

from .detection.cerrado.carvao import DET_Cerrado_Carvao
from .detection.cerrado.nao_madeireiros import DET_Cerrado_NaoMadeireiros
from .detection.cerrado.palmeiras import DET_Cerrado_Palmeiras

from .detection.mata_atlantica.madeireiro import DET_MA_Madeireiro
from .detection.mata_atlantica.nao_madeireiro import DET_MA_NaoMadeireiro
from .detection.mata_atlantica.palmeiras import DET_MA_Palmeiras
from .detection.mata_atlantica.araucaria import DET_MA_Araucaria

from .detection.caatinga.palmeiras import DET_Caatinga_Palmeiras
from .detection.pantanal.palmeiras import DET_Pantanal_Palmeiras
from .detection.pampa.palmeiras import DET_Pampa_Palmeiras

from .detection.custom.custom import DET_Custom 


def _icon_path_png():
    """
    Tenta localizar common/icons/icon.png relativo a este arquivo.
    Ajusta 1 nível acima caso este provider esteja numa subpasta.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "common", "icons", "icon.png"),
        os.path.join(os.path.dirname(here), "common", "icons", "icon.png"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None

def _icon_path_svg():
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "common", "icons", "icon.svg"),
        os.path.join(os.path.dirname(here), "common", "icons", "icon.svg"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


class NetfloraProvider(QgsProcessingProvider):
    def id(self):
        return "netflora"

    def name(self):
        return "Netflora"

    def longName(self):
        return "Netflora (Flight Planner & Detection)"

    def icon(self):
        png = _icon_path_png()
        if png:
            QgsMessageLog.logMessage(f"[Netflora] provider icon PNG: {png}", "Netflora", Qgis.Info)
            return QIcon(png)
        QgsMessageLog.logMessage("[Netflora] provider icon PNG not found, using theme fallback",
                                 "Netflora", Qgis.Warning)
        return QgsApplication.getThemeIcon("/processingAlgorithm.svg")

    # Alguns builds do QGIS leem este método; se não houver SVG, retornamos string vazia:
    def svgIconPath(self):
        svg = _icon_path_svg()
        if svg:
            QgsMessageLog.logMessage(f"[Netflora] provider icon SVG: {svg}", "Netflora", Qgis.Info)
            return svg
        return ""

    def loadAlgorithms(self):
        # Flight Planner
        self.addAlgorithm(NetfloraFlightPlanner())

        # Amazonia
        self.addAlgorithm(DET_Amazonia_Madeireiros())
        self.addAlgorithm(DET_Amazonia_NaoMadeireiros())
        self.addAlgorithm(DET_Amazonia_Palmeiras())
        self.addAlgorithm(DET_Amazonia_Ecologico())
        self.addAlgorithm(DET_Amazonia_Acai_Touceira())
        self.addAlgorithm(DET_Amazonia_Acai_Solteiro())
        self.addAlgorithm(DET_Amazonia_Castanheira())
        self.addAlgorithm(DET_Amazonia_Invasora())
        self.addAlgorithm(DET_Amazonia_Geral())

        # Cerrado
        self.addAlgorithm(DET_Cerrado_Carvao())
        self.addAlgorithm(DET_Cerrado_NaoMadeireiros())
        self.addAlgorithm(DET_Cerrado_Palmeiras())

        # Mata Atlântica
        self.addAlgorithm(DET_MA_Madeireiro())
        self.addAlgorithm(DET_MA_NaoMadeireiro())
        self.addAlgorithm(DET_MA_Palmeiras())
        self.addAlgorithm(DET_MA_Araucaria())
        
        # Caatinga
        self.addAlgorithm(DET_Caatinga_Palmeiras())

        # Pantanal
        self.addAlgorithm(DET_Pantanal_Palmeiras())

        # Pampa
        self.addAlgorithm(DET_Pampa_Palmeiras())

        #Custom
                # CUSTOM (import local + proteção)
        try:
            from .detection.custom import DET_Custom
            self.addAlgorithm(DET_Custom())
        except Exception as e:
            QgsMessageLog.logMessage(
                f"[Netflora] Falha ao carregar DET_Custom: {e}",
                "Netflora", Qgis.Critical
            )
