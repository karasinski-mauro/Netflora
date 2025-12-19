# -*- coding: utf-8 -*-
from ..base_detection_algorithm import BaseDetectionAlgorithm

class DET_Amazonia_Acai_Solteiro(BaseDetectionAlgorithm):
    BIOME = "Amazonia"
    CATEGORY = "Açaí-solteiro"
    ALG_ID = "netflora:amazonia_acai_solteiro"
    
    CLASS_INFO = {
        0:  {"common_name": "açaí solteiro", "sci_name": "Euterpe precatoria Mart."},
        1:  {"common_name": "açaí solteiro produtivo", "sci_name": "Euterpe precatoria Mart."},
    }

    # Opcional: mantenha apenas se precisar remapear IDs do seu modelo.
    CLASS_MAP = {i: i for i in range(2)}