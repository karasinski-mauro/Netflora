# -*- coding: utf-8 -*-
import os
from qgis.core import (
    QgsProcessingParameterFile, QgsProcessingException, QgsProcessingContext
)

# base_algorithm está um nível acima de "custom"
from ..base_detection_algorithm import BaseDetectionAlgorithm


class DET_Custom(BaseDetectionAlgorithm):
    """
    Algoritmo extra (não substitui biomas) que permite escolher pesos .onnx/.pt.
    Aparece no grupo "Detection • Custom".
    """
    ALG_ID   = "netflora:custom"
    BIOME    = "Custom"
    CATEGORY = "Generic (Custom Weights)"

    P_MODEL = "MODEL_PATH"

    def initAlgorithm(self, config=None):
        # mantém todos os parâmetros do base (raster, conf, add_to_project, sink, report)
        super().initAlgorithm(config)

        # adiciona o seletor de peso
        self.addParameter(QgsProcessingParameterFile(
            self.P_MODEL,
            "Custom model weight (.onnx ou .pt)",
            behavior=QgsProcessingParameterFile.File,
            fileFilter="ONNX/PT (*.onnx *.pt)"
        ))

    # única diferença: como resolver o caminho do modelo
    def _resolve_model_path(self, params, context: QgsProcessingContext, plugin_root, feedback):
        model_path = self.parameterAsFile(params, self.P_MODEL, context)
        if not model_path or not os.path.exists(model_path):
            raise QgsProcessingException(f"Invalid model path: {model_path}")
        return model_path

    def createInstance(self):
        return DET_Custom()
