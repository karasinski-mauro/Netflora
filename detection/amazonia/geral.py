# -*- coding: utf-8 -*-
from ..base_detection_algorithm import BaseDetectionAlgorithm

class DET_Amazonia_Geral(BaseDetectionAlgorithm):
    BIOME = "Amazonia"
    CATEGORY = "Geral"
    ALG_ID = "netflora:amazonia_geral"

    CLASS_INFO = {
        0: {'common_name': 'Tucumã', 'sci_name': 'Astrocaryum aculeatum G.Mey.'},
        1: {'common_name': 'Jací', 'sci_name': 'Attalea butyracea (Mutis ex Lf) Wess.Boer'},
        2: {'common_name': 'Jauari', 'sci_name': 'Astrocaryum jauari Mart.'},
        3: {'common_name': 'Garapeira', 'sci_name': 'Apuleia leiocarpa (Vogel) JFMacbr.'},
        4: {'common_name': 'Árvore morta', 'sci_name': 'AV'},
        5: {'common_name': 'Inajá', 'sci_name': 'Attalea maripa (Aubl.) Mart.'},
        6: {'common_name': 'Ouricuri', 'sci_name': 'Attalea phalerata Mart. ex Spreng.'},
        7: {'common_name': 'Espinheiro preto', 'sci_name': 'Acacia polyphylla DC.'},
        8: {'common_name': 'Babaçu', 'sci_name': 'Attalea speciosa Mart. ex Spreng'},
        9: {'common_name': 'Murumuru', 'sci_name': 'Astrocaryum ulei Burret'},
        10: {'common_name': 'Manite', 'sci_name': 'Brosimum alicastrum Sw.'},
        11: {'common_name': 'Castanheira', 'sci_name': 'Bertholletia excelsa Bonpl.'},
        12: {'common_name': 'Castanha florada', 'sci_name': 'Bertholletia\xa0excelsa\xa0Bonpl.'},
        13: {'common_name': 'Bajão', 'sci_name': 'Parkia paraensis Ducke'},
        14: {'common_name': 'Clareira', 'sci_name': 'CL'},
        15: {'common_name': 'Copaíba', 'sci_name': 'Copaifera multijuga Hayne'},
        16: {'common_name': 'Tauari', 'sci_name': 'Couratari macrosperma A.C.Sm.'},
        17: {'common_name': 'Jequitiba carvão', 'sci_name': 'Cariniana micrantha'},
        18: {'common_name': 'Cedro', 'sci_name': 'Cedrela odorata L.'},
        19: {'common_name': 'Samaúma', 'sci_name': 'Ceiba pentandra (L.) Gaertn.'},
        20: {'common_name': 'Cecrópia', 'sci_name': 'Cecropia'},
        21: {'common_name': 'Samauma preta', 'sci_name': 'Ceiba samauma (Mart. & Zucc.) K.Schum.'},
        22: {'common_name': 'Samaúma barriguda', 'sci_name': 'Ceiba speciosa (A.St.-Hil.) Ravenna'},
        23: {'common_name': 'Cecrópia02', 'sci_name': 'Cecropia02'},
        24: {'common_name': 'Caucho', 'sci_name': 'Castilla Ulei Warb.'},
        25: {'common_name': 'Caucho RO', 'sci_name': 'CAUCHO'},
        26: {'common_name': 'Faveira-ferro RO', 'sci_name': 'Dinizia excelsa Ducke'},
        27: {'common_name': 'Cumaru ferro', 'sci_name': 'Dipteryx odorata (Aubl.) Willd.'},
        28: {'common_name': 'Acao Jamari', 'sci_name': 'Desconhecida'},
        29: {'common_name': 'Açaí solteiro', 'sci_name': 'Euterpe precatoria Mart.'},
        30: {'common_name': 'Açaí solteiro produtivo', 'sci_name': 'Euterpe precatoria Mart.'},
        31: {'common_name': 'Orelha de macaco', 'sci_name': 'Enterolobium schomburqki'},
        32: {'common_name': 'Louro abacate', 'sci_name': 'Endlicheria verticillata'},
        33: {'common_name': 'Caxinguba', 'sci_name': 'Ficus maxima Mill.'},
        34: {'common_name': 'Folhosa desconhecida', 'sci_name': 'Desconhecida'},
        35: {'common_name': 'Ficus', 'sci_name': 'Ficus maxima Mill.'},
        36: {'common_name': 'Seringueira', 'sci_name': 'Hevea brasiliensis'},
        37: {'common_name': 'Jutai', 'sci_name': 'Hymenaea oblongifolia'},
        38: {'common_name': 'Angelim', 'sci_name': 'ANG'},
        39: {'common_name': 'Pau jacaré', 'sci_name': 'Laetia procera (Poepp.) Eichler'},
        40: {'common_name': 'Buritirana', 'sci_name': 'Mauritiella armata (Mart.) Burret'},
        41: {'common_name': 'Burití', 'sci_name': 'Mauritia flexuosa L.f.'},
        42: {'common_name': 'Maçaranduba', 'sci_name': 'Manilkara huberi (Ducke) Standl.'},
        43: {'common_name': 'Banana', 'sci_name': 'Musa sp.'},
        44: {'common_name': 'Abiu rosa', 'sci_name': 'Micropholis venulosa (Mart. & Eichler ex Miq.) Pierre'},
        45: {'common_name': 'Patauá', 'sci_name': 'Oenocarpus bataua Mart.'},
        46: {'common_name': 'Bacaba Touceira', 'sci_name': 'Oenocarpus minor Mart.'},
        47: {'common_name': 'Algoodoeiro', 'sci_name': 'ALG'},
        48: {'common_name': 'Bacaba Solteira', 'sci_name': 'Oenocarpus bacaba Mart.'},
        49: {'common_name': 'Roxinho', 'sci_name': 'Peltogyne\xa0lecointei\xa0Ducke'},
        50: {'common_name': 'Fava arara', 'sci_name': 'Parkia multijuga'},
        51: {'common_name': 'Pinho cuiabano', 'sci_name': 'Schizolobium amazonicum Ducke'},
        52: {'common_name': 'Pinho florado', 'sci_name': 'Schizolobium amazonicum Ducke'},
        53: {'common_name': 'Paxiúba', 'sci_name': 'Socratea exorrhiza (Mart.) H. Wendl.'},
        54: {'common_name': 'Taxi-vermelho AC', 'sci_name': 'TAXI'},
        55: {'common_name': 'Taxi preto', 'sci_name': 'Tachigali myrmecophila'},
        56: {'common_name': 'Taxi Verm RO', 'sci_name': 'Tachigali\xa0paniculata\xa0Aubl.'},
        57: {'common_name': 'Toras', 'sci_name': 'Toras'},
        58: {'common_name': 'Quaruba', 'sci_name': 'Vochysia ferruginea Mart.'}
    }

    # Opcional: mantenha apenas se precisar remapear IDs do seu modelo.
    CLASS_MAP = {i: i for i in range(59)}



