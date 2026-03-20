# -*- coding: utf-8 -*-
import base64
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

from ..common.model_manager import ensure_model_path
from ..common.preprocessing import run_preprocessing
from ..common.inference import run_detection

DOCS_URL = "https://github.com/karasinski-mauro/Netflora"


def _logo_data_uri(filename: str) -> str:
    path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "common",
        "icons",
        filename,
    )
    try:
        with open(path, "rb") as handle:
            encoded = base64.b64encode(handle.read()).decode("ascii")
        return f"data:image/png;base64,{encoded}"
    except Exception:
        return ""


def _norm_group_id(text: str) -> str:
    s = unicodedata.normalize('NFKD', text)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r'[^a-z0-9]+', '_', s).strip('_')
    return s


def _apply_detection_style(vlayer, prefer_field: str = "common_name"):
    """
    Categorization by common_name (fallback class_id), polygons without fill
    and labels with white halo for better readability in QGIS 3.x.
    """
    if vlayer is None or not vlayer.isValid():
        return

    field_names = vlayer.fields().names()
    cat_field = prefer_field if prefer_field in field_names else "class_id"

    seen = {}
    for feature in vlayer.getFeatures():
        value = feature[cat_field]
        key = "" if value is None else str(value)
        if key not in seen:
            seen[key] = value
    values = list(seen.values()) or [""]

    categories = []
    total_values = max(1, len(values))
    for index, value in enumerate(values):
        color = QColor()
        color.setHsv(int((index * 360.0 / total_values) % 360), 160, 220)
        r, g, b = color.red(), color.green(), color.blue()

        symbol = QgsFillSymbol.createSimple(
            {
                "color": "255,255,255,0",
                "outline_color": f"{r},{g},{b},255",
                "outline_width": "0.6",
                "outline_width_unit": "MM",
                "joinstyle": "miter",
            }
        )
        categories.append(QgsRendererCategory(value, symbol, str(value)))

    vlayer.setRenderer(QgsCategorizedSymbolRenderer(cat_field, categories))

    label_field = prefer_field if prefer_field in field_names else "class_id"

    text_format = QgsTextFormat()
    text_format.setColor(QColor(0, 0, 0))
    text_format.setSize(9)
    buffer_settings = QgsTextBufferSettings()
    buffer_settings.setEnabled(True)
    buffer_settings.setSize(1.0)
    buffer_settings.setColor(QColor(255, 255, 255))
    text_format.setBuffer(buffer_settings)

    label_settings = QgsPalLayerSettings()
    label_settings.enabled = True
    label_settings.fieldName = label_field
    label_settings.setFormat(text_format)
    try:
        label_settings.placement = QgsPalLayerSettings.PolygonInterior
    except Exception:
        try:
            label_settings.placement = QgsPalLayerSettings.OverPoint
        except Exception:
            pass

    vlayer.setLabeling(QgsVectorLayerSimpleLabeling(label_settings))
    vlayer.setLabelsEnabled(True)
    vlayer.triggerRepaint()


def _detection_help_html(biome: str, category: str, docs_url: str = DOCS_URL) -> str:
    summary = (
        f"Netflora detection tool for <b>{category}</b> in the <b>{biome}</b> biome. "
        "Use this algorithm to analyze drone imagery with AI-assisted inference and generate "
        "polygon detections with confidence values and optional PDF reporting."
    )
    return (
        f'<div style="font-family:Segoe UI, Arial, sans-serif; line-height:1.45;">'
        f'<div style="text-align:center; margin-bottom:10px;">'
        f'<img src="{_logo_data_uri("Netflora.png")}" width="180" style="margin:0 8px 12px 8px;">'
        f'<img src="{_logo_data_uri("Embrapa-Acre.png")}" width="160" style="margin:0 8px 12px 8px;">'
        f'<img src="{_logo_data_uri("Fundo-JBS.png")}" width="160" style="margin:0 8px 12px 8px;"></div>'
        f"<h3>Netflora Detection</h3>"
        f"<p>{summary}</p>"
        f"<p><b>Inputs:</b> raster image, confidence threshold and optional report destination.<br>"
        f"<b>Outputs:</b> polygon layer with detections, class attributes and optional PDF summary.</p>"
        f'<p><a href="{docs_url}">Complete documentation / Documentacao completa</a></p>'
        f"</div>"
    )


class BaseDetectionAlgorithm(QgsProcessingAlgorithm):
    P_RASTER = "INPUT_RASTER"
    P_CONF = "CONF_THRESHOLD"
    P_ADD = "ADD_INPUT_TO_PROJECT"
    O_SINK = "OUTPUT"
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
        return f"Detection - {self.BIOME}"

    def groupId(self):
        return f"netflora_detection_{_norm_group_id(self.BIOME)}"

    def shortHelpString(self):
        return _detection_help_html(self.BIOME, self.CATEGORY)

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(self.P_RASTER, "Raster (input)"))
        self.addParameter(
            QgsProcessingParameterNumber(
                self.P_CONF,
                "Confidence threshold",
                type=QgsProcessingParameterNumber.Double,
                minValue=0.0,
                maxValue=1.0,
                defaultValue=0.05,
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.P_ADD, "Add input raster to project", defaultValue=True
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.O_SINK, "Detections (boxes)", type=QgsProcessing.TypeVectorPolygon
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.P_REPORT, "Generate PDF report", defaultValue=False
            )
        )
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.P_REPORT_PATH, "Save report to", fileFilter="PDF files (*.pdf)", optional=True
            )
        )

    def _resolve_model_path(self, params, context, plugin_root, feedback):
        alg_key = self.ALG_ID.split(":")[1]
        try:
            return ensure_model_path(alg_key, plugin_root, feedback)
        except Exception as exc:
            raise QgsProcessingException(str(exc))

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

        plugin_root = os.path.dirname(os.path.dirname(__file__))
        model_path = self._resolve_model_path(params, context, plugin_root, feedback)
        feedback.pushInfo(f"[Netflora] Using model weight: {model_path}")

        raster_pp = run_preprocessing(raster, feedback)

        boxes = run_detection(raster_pp, model_path, conf_thr, feedback)

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

        sink, dest_id = self.parameterAsSink(
            params, self.O_SINK, context, fields, QgsWkbTypes.Polygon, raster_pp.crs()
        )

        for xmin, ymin, xmax, ymax, class_id, conf in boxes:
            width = round(float(xmax - xmin), 2)
            height = round(float(ymax - ymin), 2)

            attrs = [self.BIOME, self.CATEGORY, float(conf), int(class_id), width, height]
            if add_names:
                mapped = getattr(self, "CLASS_MAP", {}).get(int(class_id), int(class_id))
                info = getattr(self, "CLASS_INFO", {}).get(
                    mapped, {"common_name": "", "sci_name": ""}
                )
                attrs.extend([info.get("common_name", ""), info.get("sci_name", "")])

            feature = QgsFeature(fields)
            feature.setAttributes(attrs)
            feature.setGeometry(QgsGeometry.fromRect(QgsRectangle(xmin, ymin, xmax, ymax)))
            sink.addFeature(feature)

        feedback.pushInfo("[Netflora] Detection pipeline complete (polygons).")

        try:
            out_layer_now = QgsProcessingUtils.mapLayerFromString(dest_id, context)
            if out_layer_now is not None and out_layer_now.isValid():
                _apply_detection_style(out_layer_now, prefer_field="common_name")
        except Exception as exc:
            feedback.reportError(f"[Netflora] Styling skipped: {exc}", fatalError=False)

        if self.parameterAsBool(params, self.P_REPORT, context):
            report_path = self.parameterAsFileOutput(params, self.P_REPORT_PATH, context)
            if not report_path:
                raise QgsProcessingException("Report generation selected but no file path given.")

            try:
                out_layer = QgsProcessingUtils.mapLayerFromString(dest_id, context)
            except Exception:
                out_layer = None
            if out_layer is None or not out_layer.isValid():
                raise QgsProcessingException("Could not reopen output layer for report generation.")

            try:
                _apply_detection_style(out_layer, prefer_field="common_name")
            except Exception as exc:
                feedback.reportError(f"[Netflora] Styling (late) skipped: {exc}", fatalError=False)

            try:
                from ..common.report import generate_report

                generate_report(out_layer, raster, self.BIOME, self.CATEGORY, report_path)
                feedback.pushInfo(f"[Netflora] Report saved to: {report_path}")
            except Exception as exc:
                feedback.reportError(
                    f"[Netflora] Report generation failed: {exc}", fatalError=False
                )

        return {self.O_SINK: dest_id}

    def createInstance(self):
        return self.__class__()
