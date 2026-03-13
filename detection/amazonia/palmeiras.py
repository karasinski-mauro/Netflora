# -*- coding: utf-8 -*-
from ..base_detection_algorithm import BaseDetectionAlgorithm

class DET_Amazonia_Palmeiras(BaseDetectionAlgorithm):
    BIOME = "Amazonia"
    CATEGORY = "Palmeiras"
    ALG_ID = "netflora:amazonia_palmeiras"

    CLASS_INFO = {
        0:  {"common_name": "tucumã",        "sci_name": "Astrocaryum aculeatum G.Mey."},
        1:  {"common_name": "jaci",          "sci_name": "Attalea butyracea (Mutis ex Lf) Wess.Boer"},
        2:  {"common_name": "jauari",        "sci_name": "Astrocaryum jauari Mart."},
        3:  {"common_name": "inajá",         "sci_name": "Attalea maripa (Aubl.) Mart."},
        4:  {"common_name": "uricuri",       "sci_name": "Attalea phalerata Mart. ex Spreng."},
        5:  {"common_name": "babaçu",        "sci_name": "Attalea speciosa Mart. ex Spreng."},
        6:  {"common_name": "cocão",         "sci_name": "Attalea tessmannii Burret"},
        7:  {"common_name": "murumuru",      "sci_name": "Astrocaryum ulei Burret"},
        8:  {"common_name": "açaí solteiro", "sci_name": "Euterpe precatoria Mart."},
        9:  {"common_name": "açaí solteiro produtivo", "sci_name": "Euterpe precatoria Mart."},
        10: {"common_name": "buritirana",    "sci_name": "Mauritiella armata (Kunth) Burret"},
        11: {"common_name": "buriti",        "sci_name": "Mauritia flexuosa L.f."},
        12: {"common_name": "patauá",        "sci_name": "Oenocarpus bataua Mart."},
        13: {"common_name": "bacaba",        "sci_name": "Oenocapus bacaba Mart."},
        14: {"common_name": "paxiuba",      "sci_name": "Socratea exorrhiza (Mart.) H. Wendl."}
    }

    # Opcional: mantenha apenas se precisar remapear IDs do seu modelo.
    CLASS_MAP = {i: i for i in range(15)}



