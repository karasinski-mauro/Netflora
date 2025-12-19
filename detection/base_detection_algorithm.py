# -*- coding: utf-8 -*-
import os
import re
import unicodedata

from qgis.core import (
    QgsProcessingAlgorithm, QgsProcessingParameterRasterLayer,
    QgsProcessingParameterFeatureSink, QgsProcessingParameterNumber, QgsProcessingParameterBoolean,
    QgsProcessingParameterFileDestination,
    QgsProcessingContext, QgsProcessingException, QgsFeature, QgsFields, QgsField,
    QgsWkbTypes, QgsFeatureSink, QgsProcessing, QgsCoordinateReferenceSystem,
    QgsProcessingOutputVectorLayer, QgsProject, QgsRasterLayer, QgsProcessingUtils,
    QgsSymbol, QgsRendererCategory, QgsCategorizedSymbolRenderer,
    QgsSimpleFillSymbolLayer, QgsVectorLayerSimpleLabeling,
    QgsPalLayerSettings, QgsTextFormat, QgsTextBufferSettings, QgsFillSymbol
)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor

from ..common.preprocessing import run_preprocessing
from ..common.inference import run_detection


def _norm_group_id(text: str) -> str:
    s = unicodedata.normalize('NFKD', text)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r'[^a-z0-9]+', '_', s).strip('_')
    return s


# -------------------------- estilo de saída (boxes) -------------------------- #

def _apply_detection_style(vlayer, prefer_field: str = "common_name"):
    """
    Categorização por 'common_name' (fallback 'class_id'), polígonos SEM fill
    (contorno colorido) e rótulos com halo branco.
    Sem expressões: usa um único campo como texto do rótulo (compatível com QGIS 3.x).
    """
    if vlayer is None or not vlayer.isValid():
        return

    field_names = vlayer.fields().names()
    cat_field = prefer_field if prefer_field in field_names else "class_id"

    # ---- categorias (uma cor por valor distinto) ----
    seen = {}
    for f in vlayer.getFeatures():
        v = f[cat_field]
        key = "" if v is None else str(v)
        if key not in seen:
            seen[key] = v
    values = list(seen.values()) or [""]

    cats = []
    n = max(1, len(values))
    for i, val in enumerate(values):
        # cor por matiz
        qc = QColor()
        qc.setHsv(int((i * 360.0 / n) % 360), 160, 220)
        r, g, b = qc.red(), qc.green(), qc.blue()

        sym = QgsFillSymbol.createSimple({
            "color": "255,255,255,0",               # fill transparente
            "outline_color": f"{r},{g},{b},255",    # contorno colorido
            "outline_width": "0.6",
            "outline_width_unit": "MM",
            "joinstyle": "miter"
        })
        cats.append(QgsRendererCategory(val, sym, str(val)))

    vlayer.setRenderer(QgsCategorizedSymbolRenderer(cat_field, cats))

    # ---- rótulos com halo branco (SEM expressão) ----
    label_field = prefer_field if prefer_field in field_names else "class_id"

    fmt = QgsTextFormat()
    fmt.setColor(QColor(0, 0, 0))
    fmt.setSize(9)  # pt
    buf = QgsTextBufferSettings()
    buf.setEnabled(True)
    buf.setSize(1.0)  # pt
    buf.setColor(QColor(255, 255, 255))
    fmt.setBuffer(buf)

    pal = QgsPalLayerSettings()
    pal.enabled = True
    pal.fieldName = label_field        # usa um campo direto, sem expressão
    pal.setFormat(fmt)
    try:
        pal.placement = QgsPalLayerSettings.PolygonInterior
    except Exception:
        try:
            pal.placement = QgsPalLayerSettings.OverPoint
        except Exception:
            pass

    vlayer.setLabeling(QgsVectorLayerSimpleLabeling(pal))
    vlayer.setLabelsEnabled(True)
    vlayer.triggerRepaint()


# ---------------------------- algoritmo base ---------------------------- #

class BaseDetectionAlgorithm(QgsProcessingAlgorithm):
    P_RASTER = "INPUT_RASTER"
    P_CONF   = "CONF_THRESHOLD"
    P_ADD    = "ADD_INPUT_TO_PROJECT"
    O_SINK   = "OUTPUT"
    P_REPORT = "GENERATE_REPORT"
    P_REPORT_PATH = "REPORT_PATH"

    BIOME = "Biome"
    CATEGORY = "Category"
    ALG_ID = "netflora:base"

    def name(self):
        return self.ALG_ID.split(":")[1]

    def displayName(self):
        return self.CATEGORY

    def group(self):
        return f"Detection • {self.BIOME}"

    def groupId(self):
        return f"netflora_detection_{_norm_group_id(self.BIOME)}"

    def shortHelpString(self):
        return ("Runs category-specific detection over a raster using shared pre-processing.\n"
                "Inputs: Raster; Params: Confidence threshold.\n"
                "Outputs: Polygon layer with detection boxes. Optional PDF report.")

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(self.P_RASTER, "Raster (input)"))
        self.addParameter(QgsProcessingParameterNumber(
            self.P_CONF, "Confidence threshold",
            type=QgsProcessingParameterNumber.Double,
            minValue=0.0, maxValue=1.0, defaultValue=0.05))
        self.addParameter(QgsProcessingParameterBoolean(
            self.P_ADD, "Add input raster to project", defaultValue=True))
        self.addParameter(QgsProcessingParameterFeatureSink(
            self.O_SINK, "Detections (boxes)", type=QgsProcessing.TypeVectorPolygon))

        # ---- Relatório (opcional) ----
        self.addParameter(QgsProcessingParameterBoolean(
            self.P_REPORT, "Generate PDF report", defaultValue=False))
        self.addParameter(QgsProcessingParameterFileDestination(
            self.P_REPORT_PATH, "Save report to", fileFilter="PDF files (*.pdf)", optional=True))

    # <<< IMPORTANTE: método protegido para resolver o caminho do modelo >>>
    def _resolve_model_path(self, params, context, plugin_root, feedback):
        """
        Padrão: procurar <alg_key>.onnx/.pt em common/weights.
        Classes filhas (ex.: DET_Custom) podem sobrescrever.
        """
        alg_key = self.ALG_ID.split(":")[1]
        weight_dir = os.path.join(plugin_root, "common/weights")
        candidate_onnx = os.path.join(weight_dir, f"{alg_key}.onnx")
        candidate_pt   = os.path.join(weight_dir, f"{alg_key}.pt")
        if os.path.exists(candidate_onnx):
            return candidate_onnx
        if os.path.exists(candidate_pt):
            return candidate_pt

        try:
            listing = ", ".join(sorted(os.listdir(weight_dir)))
        except Exception:
            listing = "(pasta não encontrada)"
        raise QgsProcessingException(
            f"Modelo não encontrado: {candidate_onnx} ou {candidate_pt}\n"
            f"Coloque o arquivo em: {weight_dir}\n"
            f"Nome esperado: {alg_key}.onnx (ou .pt)\n"
            f"Arquivos visíveis: {listing}"
        )

    def processAlgorithm(self, params, context: QgsProcessingContext, feedback):
        from qgis.core import QgsGeometry, QgsRectangle, QgsFeature

        add_to_project = self.parameterAsBool(params, self.P_ADD, context)

        raster = self.parameterAsRasterLayer(params, self.P_RASTER, context)
        if raster is None:
            src = self.parameterAsString(params, self.P_RASTER, context)
            if not src:
                raise QgsProcessingException("Raster input is required.")
            name = os.path.splitext(os.path.basename(src))[0]
            raster = QgsRasterLayer(src, name)
            if not raster.isValid():
                raise QgsProcessingException(f"Failed to open raster: {src}")
            if add_to_project:
                QgsProject.instance().addMapLayer(raster)
        else:
            if add_to_project and raster.id() not in QgsProject.instance().mapLayers():
                QgsProject.instance().addMapLayer(raster)

        conf_thr = self.parameterAsDouble(params, self.P_CONF, context)
        feedback.pushInfo(f"[Netflora] Detection: {self.BIOME} / {self.CATEGORY}")

        # pré-processamento (reprojeção, tiles, etc)
        raster_pp = run_preprocessing(raster, feedback)

        # resolve pesos do modelo (usa o método protegido)
        plugin_root = os.path.dirname(os.path.dirname(__file__))
        model_path = self._resolve_model_path(params, context, plugin_root, feedback)
        feedback.pushInfo(f"[Netflora] Using model weight: {model_path}")

        # inferência
        boxes = run_detection(raster_pp, model_path, conf_thr, feedback)

        # esquema da camada de saída
        fields = QgsFields()
        fields.append(QgsField("biome", QVariant.String))
        fields.append(QgsField("category", QVariant.String))
        fields.append(QgsField("conf", QVariant.Double))
        fields.append(QgsField("class_id", QVariant.Int))
        fields.append(QgsField("width", QVariant.Double))
        fields.append(QgsField("height", QVariant.Double))

        add_names = hasattr(self, "CLASS_INFO")
        if add_names:
            fields.append(QgsField("common_name", QVariant.String))
            fields.append(QgsField("sci_name", QVariant.String))

        (sink, dest_id) = self.parameterAsSink(
            params, self.O_SINK, context,
            fields, QgsWkbTypes.Polygon, raster_pp.crs()
        )

        # escreve features
        for (xmin, ymin, xmax, ymax, class_id, conf) in boxes:
            w = round(float(xmax - xmin), 2)
            h = round(float(ymax - ymin), 2)

            attrs = [self.BIOME, self.CATEGORY, float(conf), int(class_id), w, h]
            if add_names:
                mapped = getattr(self, "CLASS_MAP", {}).get(int(class_id), int(class_id))
                info = getattr(self, "CLASS_INFO", {}).get(mapped, {"common_name": "", "sci_name": ""})
                attrs.extend([info.get("common_name", ""), info.get("sci_name", "")])

            f = QgsFeature(fields)
            f.setAttributes(attrs)
            f.setGeometry(QgsGeometry.fromRect(QgsRectangle(xmin, ymin, xmax, ymax)))
            sink.addFeature(f)

        feedback.pushInfo("[Netflora] Detection pipeline complete (polygons).")

        # aplica estilo na camada resultante (categorização + labels com halo)
        try:
            out_layer_now = QgsProcessingUtils.mapLayerFromString(dest_id, context)
            if out_layer_now is not None and out_layer_now.isValid():
                _apply_detection_style(out_layer_now, prefer_field="common_name")
        except Exception as _e:
            feedback.reportError(f"[Netflora] Styling skipped: {_e}", fatalError=False)

        # ---- Relatório (opcional) ----
        if self.parameterAsBool(params, self.P_REPORT, context):
            report_path = self.parameterAsFileOutput(params, self.P_REPORT_PATH, context)
            if not report_path:
                raise QgsProcessingException("Report generation selected but no file path given.")

            # Reabrir a camada de saída a partir do dest_id (funciona para memory:, gpkg, shp, etc.)
            try:
                out_layer = QgsProcessingUtils.mapLayerFromString(dest_id, context)
            except Exception:
                out_layer = None
            if out_layer is None or not out_layer.isValid():
                raise QgsProcessingException("Could not reopen output layer for report generation.")

            # (re)aplica estilo caso ainda não esteja aplicado
            try:
                _apply_detection_style(out_layer, prefer_field="common_name")
            except Exception as _e:
                feedback.reportError(f"[Netflora] Styling (late) skipped: {_e}", fatalError=False)

            try:
                from ..common.report import generate_report
                generate_report(out_layer, raster, self.BIOME, self.CATEGORY, report_path)
                feedback.pushInfo(f"[Netflora] Report saved to: {report_path}")
            except Exception as e:
                feedback.reportError(f"[Netflora] Report generation failed: {e}", fatalError=False)

        return {self.O_SINK: dest_id}

    def createInstance(self):
        return self.__class__()
