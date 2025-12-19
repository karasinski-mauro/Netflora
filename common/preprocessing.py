# -*- coding: utf-8 -*-
"""
Shared pre-processing for all Detection algorithms.
This module is imported by biome/category algorithms.
"""
from qgis.core import QgsRasterLayer, QgsCoordinateTransformContext

def run_preprocessing(raster_layer: "QgsRasterLayer", feedback):
    # Placeholder: here you can mask, resample, normalize, tile, etc.
    feedback.pushInfo(f"[Netflora] Pre-processing raster: {raster_layer.name()}")
    # Return the same layer (no-op) for now
    return raster_layer
