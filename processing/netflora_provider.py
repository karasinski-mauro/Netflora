# -*- coding: utf-8 -*-
import os
from qgis.core import QgsProcessingProvider, QgsApplication
from qgis.PyQt.QtGui import QIcon

def _icon_path():
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "common", "icons", "icon.png"),
        os.path.join(os.path.dirname(here), "common", "icons", "icon.png"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None

from .netflora_algorithm import NetfloraDetector

class NetfloraProvider(QgsProcessingProvider):

    def loadAlgorithms(self):
        self.addAlgorithm(NetfloraDetector())

    def id(self):
        return 'netflora'

    def name(self):
        return 'NetFlora'

    def longName(self):
        return 'Plugin NetFlora para Detecção de Palmeiras'

    def icon(self):
        p = _icon_path()
        if p:
            return QIcon(p)

        try:
            return QgsApplication.getThemeIcon("/processingAlgorithm.svg")
        except Exception:
            return QIcon()
