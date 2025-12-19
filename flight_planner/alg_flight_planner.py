

# -*- coding: utf-8 -*-
import os
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsProcessingAlgorithm, QgsApplication

def _plugin_root():
    here = os.path.dirname(os.path.abspath(__file__))  # .../flight_planner
    cur = here
    for _ in range(5):
        if os.path.isdir(os.path.join(cur, "common")):
            return cur
        cur = os.path.dirname(cur)
    return here

def _flight_icon_png():
    p = os.path.join(_plugin_root(), "common", "icons", "flight.png")
    return p if os.path.exists(p) else None





"""
QGIS Processing Algorithm - Netflora Flight Planner
"""

import os
import math
import csv
import random

from qgis.PyQt.QtCore import QVariant, Qt
from qgis.PyQt.QtGui import QColor

from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterNumber,
    QgsProcessingParameterPoint,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterFeatureSink,
    QgsProcessingException,
    QgsFeatureRequest,
    QgsFeature,
    QgsFields,
    QgsField,
    QgsGeometry,
    QgsPointXY,
    QgsWkbTypes,
    QgsProject,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProcessingLayerPostProcessorInterface,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFolderDestination,
    QgsProcessingParameterString,
    QgsVectorLayer,
    QgsVectorFileWriter,
    QgsSingleSymbolRenderer,
    QgsProcessingParameterDefinition,
    QgsCategorizedSymbolRenderer, QgsRendererCategory, QgsSymbol
)

class NetfloraFlightPlanner(QgsProcessingAlgorithm):
    
    def icon(self):
        p = _flight_icon_png()
        return QIcon(p) if p else QgsApplication.getThemeIcon("/mActionGps.svg")
    
    
    INPUT_POLYGON      = "INPUT_POLYGON"
    ORIENT_LINE        = "ORIENT_LINE"
    ORIENT_PERP        = "ORIENT_PERP"
    PONTO_LANCAMENTO   = "PONTO_LANCAMENTO"

    ORIENT_MODE        = "ORIENT_MODE"
    ORIENT_MODE_CHOICES = ["Usar camada de linha", "Desenhar por 2 pontos"]
    ORIENT_START       = "ORIENT_START"
    ORIENT_END         = "ORIENT_END"

    ALTURA_VOO         = "ALTURA_VOO"
    VELOCIDADE         = "VELOCIDADE"
    OVERLAP_LAT        = "OVERLAP_LAT"
    OVERLAP_LONG       = "OVERLAP_LONG"
    TEMPO_MAX          = "TEMPO_MAX"
    TURN_CHAMFER       = "TURN_CHAMFER"
    INCLUDE_HOME_CSV   = "INCLUDE_HOME_CSV"
    MARGEM_BORDA       = "MARGEM_BORDA"

    OUTPUT_CSV         = "OUTPUT_CSV"
    OUTPUT_PATHS       = "OUTPUT_PATHS"
    OUTPUT_WAYPOINTS   = "OUTPUT_WAYPOINTS"
    OUTPUT_ORIENT      = "OUTPUT_ORIENT"

    SAVE_BASE_DIR  = "SAVE_BASE_DIR"
    AREA_NAME      = "AREA_NAME"

    DRONE_MODEL       = "DRONE_MODEL"
    DRONE_PRESETS = {
        # Mavic 3E (wide):
        # 4/3" ativo ~17.3×13.0 mm, focal ~12 mm (≈24 mm eq), 20 MP → 5280×3956
        "DJI Mavic 3E (4/3\" 20MP)": {
            "sensor_w_mm": 17.3,
            "sensor_h_mm": 13.0,
            "focal_mm":    12.0,
            "res_w_px":    5280,
            "res_h_px":    3956,
        },
        # Mavic 3T (wide):
        # 1/2" ativo ~6.4×4.8 mm, focal ~4.5 mm (≈24 mm eq), 48 MP → 8000×6000
        "DJI Mavic 3T (1/2\" 48MP)": {
            "sensor_w_mm": 6.4,
            "sensor_h_mm": 4.8,
            "focal_mm":    4.5,
            "res_w_px":    8000,
            "res_h_px":    6000,
        },
    }

    DRONE_CHOICES = list(DRONE_PRESETS.keys())

    ENLACE_DIST_METERS = 1000.0

    def name(self): return "netflora_flight_planner"
    def displayName(self): return "Flight Planner - Litchi"
    def group(self): return "Netflora Flight Planner"
    def groupId(self): return "netflora_flight_planner"
    def createInstance(self): return NetfloraFlightPlanner()


    # Presets (ajuste aqui se quiser refinar)
    # Valores aproximados, suficientes para planejamento.


    def shortHelpString(self):
        return ("Lawn-mower orientado por linha (∥/⟂), recorte por AOI, viradas ortogonais (chanfrado), "
                f"WPs ~{int(self.ENLACE_DIST_METERS)} m; CSV Litchi + camadas Linhas/Pontos.")

    @staticmethod
    def _rot_to_local(x, y, cx, cy, cos_t, sin_t):
        dx, dy = x - cx, y - cy
        return (cos_t * dx + sin_t * dy, -sin_t * dx + cos_t * dy)

    @staticmethod
    def _rot_to_world(xp, yp, cx, cy, cos_t, sin_t):
        return (cx + cos_t * xp - sin_t * yp, cy + sin_t * xp + cos_t * yp)

    @staticmethod
    def _dist(a, b): return math.hypot(a[0] - b[0], a[1] - b[1])

    def initAlgorithm(self, config=None):
               
        # ===================== INPUTS / ORIENTATION =====================
        self.addParameter(QgsProcessingParameterVectorLayer(
            self.INPUT_POLYGON, "Mapping area (polygon)",
            [QgsProcessing.TypeVectorPolygon]
        ))
        self.addParameter(QgsProcessingParameterEnum(
            self.ORIENT_MODE, "Orientation method",
            self.ORIENT_MODE_CHOICES, defaultValue=0  # 0=Use line layer, 1=Draw by 2 points
        ))
        self.addParameter(QgsProcessingParameterVectorLayer(
            self.ORIENT_LINE, "Orientation line (1 feature; lane heading)",
            [QgsProcessing.TypeVectorLine], optional=True
        ))
        self.addParameter(QgsProcessingParameterPoint(
            self.ORIENT_START, "Start point (click on map)", optional=True
        ))
        self.addParameter(QgsProcessingParameterPoint(
            self.ORIENT_END, "End point (click on map)", optional=True
        ))
        self.addParameter(QgsProcessingParameterBoolean(
            self.ORIENT_PERP, "Lanes perpendicular to the line", defaultValue=False
        ))
        self.addParameter(QgsProcessingParameterPoint(
            self.PONTO_LANCAMENTO, "Home point (same CRS as AOI)"
        ))

        # ===================== FLIGHT PARAMETERS =====================
        self.addParameter(QgsProcessingParameterNumber(
            self.ALTURA_VOO, "Flight altitude (m)",
            type=QgsProcessingParameterNumber.Double, defaultValue=150.0
        ))
        self.addParameter(QgsProcessingParameterNumber(
            self.VELOCIDADE, "Drone speed (m/s)",
            type=QgsProcessingParameterNumber.Double, defaultValue=15.0
        ))
        self.addParameter(QgsProcessingParameterNumber(
            self.OVERLAP_LAT, "Lateral overlap (%)",
            type=QgsProcessingParameterNumber.Double, defaultValue=80.0
        ))
        self.addParameter(QgsProcessingParameterNumber(
            self.OVERLAP_LONG, "Longitudinal overlap (%)",
            type=QgsProcessingParameterNumber.Double, defaultValue=80.0
        ))
        self.addParameter(QgsProcessingParameterNumber(
            self.TEMPO_MAX, "Max mission time (min)",
            type=QgsProcessingParameterNumber.Double, defaultValue=12.0
        ))
        self.addParameter(QgsProcessingParameterNumber(
            self.TURN_CHAMFER, "Corner chamfer (m)",
            type=QgsProcessingParameterNumber.Double, defaultValue=10.0
        ))
        self.addParameter(QgsProcessingParameterNumber(
            self.MARGEM_BORDA, "Outer margin outside AOI (m)",
            type=QgsProcessingParameterNumber.Double, defaultValue=50.0
        ))
        self.addParameter(QgsProcessingParameterBoolean(
            self.INCLUDE_HOME_CSV, "Show Home in map (not in CSV)",
            defaultValue=True
        ))

        # ===================== CAMERA / DRONE (BEFORE PROJECT) =====================
        self.addParameter(QgsProcessingParameterEnum(
            self.DRONE_MODEL, "Drone / Camera", self.DRONE_CHOICES,
            defaultValue=0  # 0=Mavic 3E, 1=Mavic 3T
        ))

        # ===================== PROJECT (NAME & BASE FOLDER) =====================
        self.addParameter(QgsProcessingParameterString(
            self.AREA_NAME, "Project name", defaultValue="", optional=False
        ))
        self.addParameter(QgsProcessingParameterFolderDestination(
            self.SAVE_BASE_DIR, "Base folder for outputs", optional=False
        ))

        # ===================== HIDDEN OUTPUTS (CSV + SINKS) =====================
        param_csv = QgsProcessingParameterFileDestination(
            self.OUTPUT_CSV,
            "CSV base (missions get _001, _002, …)",
            "CSV files (*.csv)",
            optional=True,
        )
        param_csv.setFlags(param_csv.flags() | QgsProcessingParameterDefinition.FlagHidden)
        self.addParameter(param_csv)

        p_paths = QgsProcessingParameterFeatureSink(
            self.OUTPUT_PATHS, "Paths (per-mission lines)",
            QgsProcessing.TypeVectorLine, optional=True, createByDefault=True
        )
        p_paths.setDefaultValue('TEMPORARY_OUTPUT')
        p_paths.setFlags(p_paths.flags() | QgsProcessingParameterDefinition.FlagHidden)
        self.addParameter(p_paths)

        p_pts = QgsProcessingParameterFeatureSink(
            self.OUTPUT_WAYPOINTS, "Waypoints (points)",
            QgsProcessing.TypeVectorPoint, optional=True, createByDefault=True
        )
        p_pts.setDefaultValue('TEMPORARY_OUTPUT')
        p_pts.setFlags(p_pts.flags() | QgsProcessingParameterDefinition.FlagHidden)
        self.addParameter(p_pts)

        p_orient = QgsProcessingParameterFeatureSink(
            self.OUTPUT_ORIENT, "Orientation line (preview)",
            QgsProcessing.TypeVectorLine, optional=True, createByDefault=True
        )
        p_orient.setDefaultValue('TEMPORARY_OUTPUT')
        p_orient.setFlags(p_orient.flags() | QgsProcessingParameterDefinition.FlagHidden)
        self.addParameter(p_orient)



    def _rings_local(self, geom, cx, cy, cos_t, sin_t):
        rings = []
        if geom.isMultipart():
            mp = geom.asMultiPolygon()
            for poly in mp:
                for ring in poly:
                    rings.append([self._rot_to_local(p.x(), p.y(), cx, cy, cos_t, sin_t) for p in ring])
        else:
            sp = geom.asPolygon()
            for ring in sp:
                rings.append([self._rot_to_local(p.x(), p.y(), cx, cy, cos_t, sin_t) for p in ring])
        return rings

    def _scan_intervals_y(self, rings_local, y):
        xs = []
        for ring in rings_local:
            for i in range(len(ring)-1):
                x1, y1 = ring[i]
                x2, y2 = ring[i+1]
                if (y1 <= y < y2) or (y2 <= y < y1):
                    t = (y - y1) / (y2 - y1)
                    xs.append(x1 + t * (x2 - x1))
        xs.sort()
        intervals = []
        for i in range(0, len(xs)-1, 2):
            x0 = xs[i]; x1 = xs[i+1]
            if x1 > x0 + 1e-9:
                intervals.append((x0, x1))
        return intervals

    def processAlgorithm(self, parameters, context, feedback):
        layer = self.parameterAsVectorLayer(parameters, self.INPUT_POLYGON, context)
        if not layer:
            raise QgsProcessingException("Camada de polígonos inválida.")

        if layer.crs().isGeographic():
            feedback.reportError("CRS geográfico: 'Margem externa' será em graus. Reprojete para CRS métrico.", True)

        # ---- parâmetros básicos ----
        home_pt    = self.parameterAsPoint(parameters, self.PONTO_LANCAMENTO, context)
        alt        = self.parameterAsDouble(parameters, self.ALTURA_VOO, context)
        speed      = max(0.1, self.parameterAsDouble(parameters, self.VELOCIDADE, context))
        ov_lat     = self.parameterAsDouble(parameters, self.OVERLAP_LAT, context) / 100.0
        ov_long    = self.parameterAsDouble(parameters, self.OVERLAP_LONG, context) / 100.0
        tmax_sec   = self.parameterAsDouble(parameters, self.TEMPO_MAX, context) * 60.0
        chamfer    = max(0.0, self.parameterAsDouble(parameters, self.TURN_CHAMFER, context))
        margem_ext = max(0.0, self.parameterAsDouble(parameters, self.MARGEM_BORDA, context))
        out_csv    = self.parameterAsFileOutput(parameters, self.OUTPUT_CSV, context)
        include_home = self.parameterAsBool(parameters, self.INCLUDE_HOME_CSV, context)
        
        # ====== Diretórios de saída por área (modo inteligente) ======
        base_dir  = self.parameterAsFile(parameters, self.SAVE_BASE_DIR, context)
        area_name_param = self.parameterAsString(parameters, self.AREA_NAME, context).strip()

        csv_dir = None
        shp_dir = None
        base_for_csv = None
        area_key = None  # prefixo padrão para nomes

        if base_dir:
            base_dir = os.path.normpath(base_dir)

            if area_name_param:
                # Caso 1: usuário quer criar uma nova pasta com esse nome dentro do diretório-base
                area_dir = os.path.join(base_dir, area_name_param)
                area_key = area_name_param

                # >>> NÃO sobrescrever: se já existe, interrompe com mensagem
                if os.path.isdir(area_dir):
                    raise QgsProcessingException(
                        f"O projeto '{area_name_param}' já existe em '{base_dir}'. "
                        f"Escolha outro nome de projeto ou remova/renomeie a pasta existente."
                    )
            else:
                # Caso 2: usuário apontou diretamente para a pasta da área
                area_dir = base_dir
                area_key = os.path.basename(area_dir)
                # Se você também quiser bloquear quando o usuário apontar para uma pasta já existente,
                # descomente o bloco abaixo:
                #
                # if os.path.isdir(area_dir):
                #     raise QgsProcessingException(
                #         f"A pasta de projeto '{area_dir}' já existe. "
                #         f"Informe um 'Project name' (AREA_NAME) novo ou selecione outro diretório-base."
                #     )

            # Se chegou aqui, a pasta não existe → pode criar
            csv_dir  = os.path.join(area_dir, f"VOOS_{area_key}")
            shp_dir  = os.path.join(area_dir, "SHP")
            os.makedirs(csv_dir, exist_ok=True)
            os.makedirs(shp_dir, exist_ok=True)

            # CSVs terão prefixo = area_key
            base_for_csv = os.path.join(csv_dir, area_key)
            feedback.pushInfo(
                f"Saídas configuradas: CSV → '{csv_dir}', SHP → '{shp_dir}', padrão CSV: '{area_key}_{1:03d}.csv'"
            )



        # ---- feição da AOI ----
        feats = list(layer.getFeatures(QgsFeatureRequest().setLimit(1)))
        if not feats:
            raise QgsProcessingException("A camada não possui feições.")
        geom = feats[0].geometry()
        if not geom or geom.isEmpty():
            raise QgsProcessingException("Geometria vazia.")

        # ---- aplica margem antes de QUALQUER uso de geom_scan ----
        geom_scan = geom.buffer(margem_ext, 8) if margem_ext > 0.0 else geom
        if geom_scan is None or geom_scan.isEmpty():
            # fallback para evitar NameError caso o buffer retorne vazio
            geom_scan = geom
        if margem_ext > 0.0:
            feedback.pushInfo(f"Margem externa: {margem_ext:.2f} m")

        # ---- centróide base para o sistema local ----
        centroid = geom_scan.centroid().asPoint()
        cx, cy = centroid.x(), centroid.y()

        # ---- orientação: camada ou 2 pontos (como já implementado) ----
        orient_perp = self.parameterAsBool(parameters, self.ORIENT_PERP, context)
        orient_mode = self.parameterAsEnum(parameters, self.ORIENT_MODE, context)
        orient_line_layer = self.parameterAsVectorLayer(parameters, self.ORIENT_LINE, context)
        p_start = self.parameterAsPoint(parameters, self.ORIENT_START, context)
        p_end   = self.parameterAsPoint(parameters, self.ORIENT_END, context)

        # (opcional) sink de visualização da linha:
        fields_orient = QgsFields(); fields_orient.append(QgsField("source", QVariant.String))
        sink_orient, id_orient = self.parameterAsSink(
            parameters, self.OUTPUT_ORIENT, context,
            fields_orient, QgsWkbTypes.LineString, layer.crs()
        )

        theta = 0.0
        orient_line_geom_for_viz = None

        if orient_mode == 0:
            if not orient_line_layer:
                raise QgsProcessingException("Modo 'Usar camada de linha': selecione uma camada de linha.")
            lfeats = list(orient_line_layer.getFeatures(QgsFeatureRequest().setLimit(1)))
            if not lfeats: raise QgsProcessingException("Linha de orientação vazia.")
            g = lfeats[0].geometry()
            if not g or g.isEmpty(): raise QgsProcessingException("Geometria de linha vazia.")
            verts = [p for p in g.vertices()]
            if len(verts) < 2: raise QgsProcessingException("Linha de orientação precisa de ≥ 2 vértices.")
            x0, y0 = verts[0].x(), verts[0].y(); x1, y1 = verts[-1].x(), verts[-1].y()
            dx, dy = x1 - x0, y1 - y0
            if abs(dx) < 1e-12 and abs(dy) < 1e-12:
                raise QgsProcessingException("Linha de orientação degenerada.")
            theta = math.atan2(dy, dx)
            if orient_perp: theta += math.pi / 2.0
            orient_line_geom_for_viz = g
            feedback.pushInfo(f"Orientação por CAMADA: θ={math.degrees(theta):.2f}° {'(⊥)' if orient_perp else '(∥)'}")
        else:
            if p_start.isEmpty() or p_end.isEmpty():
                raise QgsProcessingException("Modo 'Desenhar por 2 pontos': informe Ponto Inicial e Ponto Final.")
            x0, y0 = p_start.x(), p_start.y()
            x1, y1 = p_end.x(),   p_end.y()
            dx, dy = x1 - x0, y1 - y0
            if abs(dx) < 1e-12 and abs(dy) < 1e-12:
                raise QgsProcessingException("Os 2 pontos são coincidentes; não é possível definir a orientação.")
            theta = math.atan2(dy, dx)
            if orient_perp: theta += math.pi / 2.0
            orient_line_geom_for_viz = QgsGeometry.fromPolylineXY([QgsPointXY(x0, y0), QgsPointXY(x1, y1)])
            feedback.pushInfo(f"Orientação por 2 PONTOS: θ={math.degrees(theta):.2f}° {'(⊥)' if orient_perp else '(∥)'}")

        if sink_orient and orient_line_geom_for_viz:
            f_or = QgsFeature(fields_orient)
            f_or.setGeometry(orient_line_geom_for_viz)
            f_or.setAttributes(["layer" if orient_mode == 0 else "2points"])
            sink_orient.addFeature(f_or)
            feature_orient_export = f_or

        # ---- só agora calcule cos/sin e siga o fluxo normal ----
        cos_t, sin_t = math.cos(theta), math.sin(theta)



        # --- Drone optics → footprint no solo e espaçamentos a partir de presets ---
        model_idx = self.parameterAsEnum(parameters, self.DRONE_MODEL, context)
        model_key = self.DRONE_CHOICES[model_idx]
        preset = self.DRONE_PRESETS[model_key]

        sensor_w_mm = preset["sensor_w_mm"]
        sensor_h_mm = preset["sensor_h_mm"]
        focal_mm    = preset["focal_mm"]
        res_w_px    = preset["res_w_px"]
        res_h_px    = preset["res_h_px"]

        footprint_w_m = alt * (sensor_w_mm / focal_mm)
        footprint_h_m = alt * (sensor_h_mm / focal_mm)

        line_spacing = max(0.5, footprint_w_m * (1.0 - ov_lat))
        along_step   = max(0.5, footprint_h_m * (1.0 - ov_long))

        feedback.pushInfo(
            f"[{model_key}] Footprint: {footprint_w_m:.1f} × {footprint_h_m:.1f} m "
            f"| line_spacing={line_spacing:.2f} m | photo_step={along_step:.2f} m"
        )

        minx = miny = float("inf")
        maxx = maxy = float("-inf")
        rings_local = []
        if geom_scan.isMultipart():
            mp = geom_scan.asMultiPolygon()
            for poly in mp:
                for ring in poly:
                    loc = [self._rot_to_local(p.x(), p.y(), cx, cy, cos_t, sin_t) for p in ring]
                    rings_local.append(loc)
                    for xp, yp in loc:
                        minx = min(minx, xp); maxx = max(maxx, xp)
                        miny = min(miny, yp); maxy = max(maxy, yp)
        else:
            sp = geom_scan.asPolygon()
            for ring in sp:
                loc = [self._rot_to_local(p.x(), p.y(), cx, cy, cos_t, sin_t) for p in ring]
                rings_local.append(loc)
                for xp, yp in loc:
                    minx = min(minx, xp); maxx = max(maxx, xp)
                    miny = min(miny, yp); maxy = max(maxy, yp)

        def _snap_x_to_intervals(x_candidate, intervals):
            if not intervals: return None
            best = None; best_d = float("inf")
            for x0, x1 in intervals:
                if x0 <= x_candidate <= x1: return x_candidate
                if abs(x_candidate - x0) < best_d: best_d = abs(x_candidate - x0); best = x0
                if abs(x_candidate - x1) < best_d: best_d = abs(x_candidate - x1); best = x1
            return best

        key_loc = []
        direction = 1
        ycur = miny
        next_start_x = None
        seg_kind = []  # 'ALONG' or 'ORTHO'

        while ycur <= maxy + 1e-9:
            intervals_cur = self._scan_intervals_y(rings_local, ycur)
            if not intervals_cur:
                ycur += line_spacing; direction *= -1; next_start_x = None; continue

            if direction == 1:
                default_start_x = intervals_cur[0][0]
                default_end_x   = intervals_cur[-1][1]
            else:
                default_start_x = intervals_cur[-1][1]
                default_end_x   = intervals_cur[0][0]

            start_x = _snap_x_to_intervals(next_start_x, intervals_cur) if next_start_x is not None else default_start_x
            if start_x is None:
                ycur += line_spacing; direction *= -1; next_start_x = None; continue

            end_x = None
            for (x0, x1) in intervals_cur:
                if x0 - 1e-9 <= start_x <= x1 + 1e-9:
                    end_x = (x1 if direction == 1 else x0); break
            if end_x is None: end_x = default_end_x

            stripe_len = abs(end_x - start_x)
            if stripe_len < 1e-9:
                ycur += line_spacing; direction *= -1; next_start_x = None; continue

            use_ch = min(chamfer, stripe_len * 0.45)
            dx_sign = 1 if direction == 1 else -1
            end_mod_x = end_x - dx_sign * use_ch

            if not key_loc or key_loc[-1] != (start_x, ycur):
                key_loc.append((start_x, ycur))
            key_loc.append((end_mod_x, ycur))
            seg_kind.append("ALONG")

            y_next = ycur + line_spacing
            if y_next <= maxy + 1e-9:
                key_loc.append((end_mod_x, y_next))
                seg_kind.append("ORTHO")
                intervals_next = self._scan_intervals_y(rings_local, y_next)
                next_start_x = _snap_x_to_intervals(end_mod_x, intervals_next) if intervals_next else None
            else:
                next_start_x = None

            ycur = y_next
            direction *= -1

        if len(key_loc) < 2:
            raise QgsProcessingException("Não foi possível construir o caminho de voo dentro da área.")

        key_pts = [self._rot_to_world(xp, yp, cx, cy, cos_t, sin_t) for (xp, yp) in key_loc]

        expected = max(0, len(key_pts) - 1)
        if len(seg_kind) < expected:
            seg_kind.extend(["ALONG"] * (expected - len(seg_kind)))
        elif len(seg_kind) > expected:
            seg_kind = seg_kind[:expected]

        missions = []
        wps_cur = []
        elapsed = 0.0              # segundos já consumidos na missão corrente (apenas entre WPs)
        dist_since_wp = 0.0        # metros desde o último WP para espaçar ENLACE

        def capacity_m():
            """Quanto ainda posso voar nesta missão em metros (sem contar RTH)."""
            return max(0.0, (tmax_sec - elapsed) * speed)

        def start_new_mission(seed_xy=None):
            """Fecha a missão atual e inicia outra, opcionalmente já sem 'tempo de deslocamento' até seed."""
            nonlocal missions, wps_cur, elapsed, dist_since_wp
            if wps_cur:
                missions.append(wps_cur)
            wps_cur = []
            elapsed = 0.0
            dist_since_wp = 0.0
            if seed_xy is not None:
                # Litchi não conta voo até o 1º WP por padrão → não incrementa tempo aqui
                wps_cur.append((seed_xy[0], seed_xy[1], alt))

        def push_segment(a, b):
            """
            Empurra o segmento a->b consumindo o orçamento.
            Pode cortar o segmento várias vezes, criando WPs nos cortes e nos ENLACE.
            """
            nonlocal wps_cur, elapsed, dist_since_wp

            ax, ay = a
            bx, by = b
            seg_len = self._dist(a, b)
            if seg_len <= 1e-9:
                return

            ux = (bx - ax) / seg_len
            uy = (by - ay) / seg_len

            # posição local ao longo do segmento (0 .. seg_len)
            pos = 0.0

            while pos < seg_len - 1e-9:
                cap = capacity_m()
                if cap <= 1e-6:
                    # fecha missão exatamente aqui e reabre começando no ponto atual
                    cut_xy = (ax + ux * pos, ay + uy * pos)
                    start_new_mission(seed_xy=cut_xy)
                    continue

                # quanto ainda consigo percorrer neste passe
                take = min(seg_len - pos, cap)

                # 1) colocar WPs de enlace dentro do subtrecho [pos, pos+take]
                walked = 0.0
                # “dist_since_wp” vem do histórico fora do subtrecho; respeitar ENLACE
                while dist_since_wp + (take - walked) >= self.ENLACE_DIST_METERS - 1e-9:
                    need = self.ENLACE_DIST_METERS - dist_since_wp
                    if walked + need > take + 1e-9:
                        break
                    walked += need
                    cand_len = pos + walked
                    cand_xy = (ax + ux * cand_len, ay + uy * cand_len)
                    wps_cur.append((cand_xy[0], cand_xy[1], alt))
                    elapsed += need / speed          # só soma o que voou dentro deste subtrecho
                    dist_since_wp = 0.0

                # 2) fechar o subtrecho no fim (corte ou fim de segmento)
                sub_rem = take - walked
                if sub_rem > 1e-9:
                    end_len = pos + take
                    end_xy = (ax + ux * end_len, ay + uy * end_len)
                    wps_cur.append((end_xy[0], end_xy[1], alt))
                    elapsed += sub_rem / speed
                    dist_since_wp += sub_rem

                pos += take

                if pos < seg_len - 1e-9:
                    # houve corte por falta de orçamento → próxima iteração inicia nova missão
                    cut_xy = (ax + ux * pos, ay + uy * pos)
                    start_new_mission(seed_xy=cut_xy)

        # === inicializa 1º ponto ===
        if not key_pts:
            raise QgsProcessingException("Sem pontos de caminho para montar as missões.")
        # Começa no primeiro ponto do caminho (sem custo de tempo até ele)
        wps_cur = [(key_pts[0][0], key_pts[0][1], alt)]

        # Varre todos os segmentos, cortando onde necessário
        for i in range(len(key_pts) - 1):
            a = key_pts[i]
            b = key_pts[i + 1]
            push_segment(a, b)

        # Fecha a última missão
        if wps_cur:
            missions.append(wps_cur)

        # Insere o Home como 1º WP apenas na primeira missão (opcional)
      #  if include_home and missions:
      #      missions[0] = [(home_pt.x(), home_pt.y(), alt)] + missions[0]
        layer_crs = layer.crs()
        wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
        xform = QgsCoordinateTransform(layer_crs, wgs84, context.transformContext())
        home84 = xform.transform(home_pt)

        base = base_for_csv if base_for_csv else os.path.splitext(out_csv)[0]
        for i, wps in enumerate(missions, start=1):
            out_path = f"{base}_{i:03d}.csv"
            self._export_litchi_csv(out_path, wps, xform, (home84 if include_home else None), speed, chamfer,photo_dist_m=along_step)
            feedback.pushInfo(f"Arquivo gerado: {out_path}")

        features_lines_export = []
        features_pts_export   = []
        feature_orient_export = None

        # ---------- Layers ----------
        fields_lines = QgsFields(); fields_lines.append(QgsField("mission", QVariant.Int)); fields_lines.append(QgsField("wp_count", QVariant.Int))
        fields_pts   = QgsFields(); fields_pts.append(QgsField("mission", QVariant.Int));   fields_pts.append(QgsField("idx", QVariant.Int)); fields_pts.append(QgsField("alt", QVariant.Double))

        sink_lines, id_lines = self.parameterAsSink(parameters, self.OUTPUT_PATHS, context, fields_lines, QgsWkbTypes.LineString, layer.crs())
        sink_pts,   id_pts   = self.parameterAsSink(parameters, self.OUTPUT_WAYPOINTS, context, fields_pts,   QgsWkbTypes.Point,      layer.crs())

        for mi, wps in enumerate(missions, start=1):
            if len(wps) >= 2:
                poly = [QgsPointXY(x, y) for (x, y, _z) in wps]
                f = QgsFeature(fields_lines)
                f.setGeometry(QgsGeometry.fromPolylineXY(poly))
                f.setAttributes([mi, len(wps)])
                sink_lines.addFeature(f)
                features_lines_export.append(f)
            for idx, (x, y, z) in enumerate(wps, start=1):
                fp = QgsFeature(fields_pts)
                fp.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(x, y)))
                fp.setAttributes([mi, idx, float(z)])
                sink_pts.addFeature(fp)
                features_pts_export.append(fp)


        # ====== Exportar SHPs em <AREA>/SHP ======
        if shp_dir:
            crs_authid = layer.crs().authid()
            name_prefix = area_key if area_key else "export"  # usa nome da pasta; fallback "export"

            # paths.shp
            if features_lines_export:
                vl_lines = QgsVectorLayer(f"LineString?crs={crs_authid}", "paths", "memory")
                pr_lines = vl_lines.dataProvider()
                pr_lines.addAttributes(list(fields_lines))
                vl_lines.updateFields()
                pr_lines.addFeatures(features_lines_export)
                opt = QgsVectorFileWriter.SaveVectorOptions()
                opt.driverName = "ESRI Shapefile"
                opt.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
                lines_path = os.path.join(shp_dir, f"{name_prefix}_paths.shp")
                QgsVectorFileWriter.writeAsVectorFormatV3(vl_lines, lines_path, context.transformContext(), opt)
                feedback.pushInfo(f"Salvo: {lines_path}")

            # waypoints.shp
            if features_pts_export:
                vl_pts = QgsVectorLayer(f"Point?crs={crs_authid}", "waypoints", "memory")
                pr_pts = vl_pts.dataProvider()
                pr_pts.addAttributes(list(fields_pts))
                vl_pts.updateFields()
                pr_pts.addFeatures(features_pts_export)
                opt = QgsVectorFileWriter.SaveVectorOptions()
                opt.driverName = "ESRI Shapefile"
                opt.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
                pts_path = os.path.join(shp_dir, f"{name_prefix}_waypoints.shp")
                QgsVectorFileWriter.writeAsVectorFormatV3(vl_pts, pts_path, context.transformContext(), opt)
                feedback.pushInfo(f"Salvo: {pts_path}")

            # orient_line.shp
            if feature_orient_export:
                vl_or = QgsVectorLayer(f"LineString?crs={crs_authid}", "orient_line", "memory")
                pr_or = vl_or.dataProvider()
                pr_or.addAttributes(list(fields_orient))
                vl_or.updateFields()
                pr_or.addFeature(feature_orient_export)
                opt = QgsVectorFileWriter.SaveVectorOptions()
                opt.driverName = "ESRI Shapefile"
                opt.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
                or_path = os.path.join(shp_dir, f"{name_prefix}_orient_line.shp")
                QgsVectorFileWriter.writeAsVectorFormatV3(vl_or, or_path, context.transformContext(), opt)
                feedback.pushInfo(f"Salvo: {or_path}")

            # ====== Carregar SHPs no projeto já com estilo ======
            def _style_lines_by_mission(layer, field_name="mission"):
                try:
                    if not layer or not layer.isValid():
                        return
                    idx = layer.fields().indexFromName(field_name)
                    if idx < 0:
                        feedback.reportError(f"Campo '{field_name}' não encontrado para estilizar linhas.", True)
                        return
                    values = sorted(layer.uniqueValues(idx))
                    cats = []
                    for v in values:
                        sym = QgsSymbol.defaultSymbol(layer.geometryType())
                        # cor pseudo-aleatória estável por valor
                        try:
                            seed = int(v)
                        except Exception:
                            seed = hash(v)
                        rnd = random.Random(seed * 98731)
                        sym.setColor(QColor(rnd.randint(30, 220), rnd.randint(30, 220), rnd.randint(30, 220)))
                        try:
                            sl = sym.symbolLayer(0)
                            if hasattr(sl, "setWidth"): sl.setWidth(0.9)
                        except Exception:
                            pass
                        cats.append(QgsRendererCategory(v, sym, f"Mission {v}"))
                    layer.setRenderer(QgsCategorizedSymbolRenderer(field_name, cats))
                    layer.triggerRepaint()
                except Exception as e:
                    feedback.reportError(f"Falha ao estilizar linhas por '{field_name}': {e}", True)

            def _style_points_by_mission(layer, field_name="mission"):
                try:
                    if not layer or not layer.isValid():
                        return
                    idx = layer.fields().indexFromName(field_name)
                    if idx < 0:
                        feedback.reportError(f"Campo '{field_name}' não encontrado para estilizar pontos.", True)
                        return
                    values = sorted(layer.uniqueValues(idx))
                    cats = []
                    for v in values:
                        sym = QgsSymbol.defaultSymbol(layer.geometryType())
                        try:
                            sl = sym.symbolLayer(0)
                            if hasattr(sl, "setSize"): sl.setSize(3.0)  # marcadores maiores
                        except Exception:
                            pass
                        # cor estável
                        try:
                            seed = int(v)
                        except Exception:
                            seed = hash(v)
                        rnd = random.Random(seed * 7919)
                        sym.setColor(QColor(rnd.randint(40, 230), rnd.randint(40, 230), rnd.randint(40, 230)))
                        cats.append(QgsRendererCategory(v, sym, f"Mission {v}"))
                    layer.setRenderer(QgsCategorizedSymbolRenderer(field_name, cats))
                    layer.triggerRepaint()
                except Exception as e:
                    feedback.reportError(f"Falha ao estilizar pontos por '{field_name}': {e}", True)

            def _style_orient_line(layer):
                try:
                    if not layer or not layer.isValid():
                        return
                    sym = QgsSymbol.defaultSymbol(layer.geometryType())
                    sym.setColor(QColor(120, 120, 120))
                    try:
                        sl = sym.symbolLayer(0)
                        if hasattr(sl, "setWidth"): sl.setWidth(0.8)
                        if hasattr(sl, "setPenStyle"): sl.setPenStyle(Qt.DashLine)
                    except Exception:
                        pass
                    from qgis.core import QgsSingleSymbolRenderer
                    layer.setRenderer(QgsSingleSymbolRenderer(sym))
                    layer.triggerRepaint()
                except Exception as e:
                    feedback.reportError(f"Falha ao estilizar linha de orientação: {e}", True)

            try:
                if features_lines_export:
                    lyr_paths = QgsVectorLayer(lines_path, f"{name_prefix}_paths (styled)", "ogr")
                    if lyr_paths and lyr_paths.isValid():
                        _style_lines_by_mission(lyr_paths, "mission")
                        QgsProject.instance().addMapLayer(lyr_paths)
                if features_pts_export:
                    lyr_pts = QgsVectorLayer(pts_path, f"{name_prefix}_waypoints (styled)", "ogr")
                    if lyr_pts and lyr_pts.isValid():
                        _style_points_by_mission(lyr_pts, "mission")
                        QgsProject.instance().addMapLayer(lyr_pts)
                if feature_orient_export:
                    lyr_or = QgsVectorLayer(or_path, f"{name_prefix}_orient_line (styled)", "ogr")
                    if lyr_or and lyr_or.isValid():
                        _style_orient_line(lyr_or)
                        QgsProject.instance().addMapLayer(lyr_or)
            except Exception as e:
                feedback.reportError(f"Falha ao carregar/estilizar SHPs: {e}", True)

        return {self.OUTPUT_CSV: f"{base}_*.csv", self.OUTPUT_PATHS: id_lines, self.OUTPUT_WAYPOINTS: id_pts, self.OUTPUT_ORIENT: id_orient}



    def _export_litchi_csv(self, path, waypoints_xyz, xform, home84_or_none, speed_mps, chamfer_m, photo_dist_m=0.0):
        header = [
            "latitude","longitude","altitude(m)","heading(deg)",
            "curvesize(m)","rotationdir","gimbalmode","gimbalpitchangle",
            "actiontype1","actionparam1","actiontype2","actionparam2",
            "actiontype3","actionparam3","actiontype4","actionparam4",
            "actiontype5","actionparam5","actiontype6","actionparam6",
            "actiontype7","actionparam7","actiontype8","actionparam8",
            "actiontype9","actionparam9","actiontype10","actionparam10",
            "actiontype11","actionparam11","actiontype12","actionparam12",
            "actiontype13","actionparam13","actiontype14","actionparam14",
            "actiontype15","actionparam15",
            "altitudemode","speed(m/s)","poi_latitude","poi_longitude",
            "poi_altitude(m)","poi_altitudemode","photo_timeinterval","photo_distinterval"
        ]
        from math import radians, degrees, sin, cos, atan2, hypot

        def _bearing_deg(lat1, lon1, lat2, lon2):
            phi1 = radians(lat1); phi2 = radians(lat2)
            dlam = radians(lon2 - lon1)
            y = sin(dlam) * cos(phi2)
            x = cos(phi1)*sin(phi2) - sin(phi1)*cos(phi2)*cos(dlam)
            return (degrees(atan2(y, x)) + 360.0) % 360.0

        n = len(waypoints_xyz)
        if n < 1: raise QgsProcessingException("Sem waypoints para exportar.")

        ll = []
        for x, y, _z in waypoints_xyz:
            p84 = xform.transform(QgsPointXY(x, y))
            ll.append((p84.y(), p84.x()))

        headings = []
        for i in range(n):
            if i < n - 1:
                lat1, lon1 = ll[i];   lat2, lon2 = ll[i+1]
            else:
                lat1, lon1 = ll[i-1]; lat2, lon2 = ll[i]
            headings.append(round(_bearing_deg(lat1, lon1, lat2, lon2), 2))

        chamfer_m = float(max(0.0, chamfer_m))
        curves = [0.0] * n

        def seglen(i, j):
            xi, yi, _ = waypoints_xyz[i]
            xj, yj, _ = waypoints_xyz[j]
            return hypot(xj - xi, yj - yi)

        for i in range(1, n-1):
            prev_len = seglen(i-1, i)
            next_len = seglen(i, i+1)
            if prev_len < 1e-6 or next_len < 1e-6:
                curves[i] = 0.0
                continue
            max_by_geom = 0.45 * min(prev_len, next_len)
            curves[i] = round(max(0.0, min(chamfer_m, max_by_geom)), 3)

        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(header)
            for i, (x, y, z) in enumerate(waypoints_xyz):
                p84 = xform.transform(QgsPointXY(x, y))
                w.writerow([
                    p84.y(), p84.x(), z,
                    headings[i],
                    curves[i],
                    0,
                    2, -90,
                    -1,0, -1,0, -1,0, -1,0, -1,0,
                    -1,0, -1,0, -1,0, -1,0, -1,0,
                    -1,0, -1,0, -1,0, -1,0, -1,0,
                    0,
                    float(speed_mps),
                    "", "", "", "", "", "",
                    round(float(photo_dist_m), 2)
                ])
