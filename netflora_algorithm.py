from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterFileDestination,
    QgsRaster,
    QgsProcessingOutputVectorLayer
)

class NetfloraAlgorithm(QgsProcessingAlgorithm):
    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterRasterLayer(self.INPUT, 'Imagem de entrada')
        )
        self.addParameter(
            QgsProcessingParameterFileDestination(self.OUTPUT, 'Shapefile de saída', 'ESRI Shapefile (*.shp)')
        )

    def processAlgorithm(self, parameters, context, feedback):
        raster_layer = self.parameterAsRasterLayer(parameters, self.INPUT, context)
        output_path = self.parameterAsFileOutput(parameters, self.OUTPUT, context)

        # Aqui seria chamada a lógica de detecção real
        feedback.pushInfo(f"Raster recebido: {raster_layer.name()}")
        feedback.pushInfo(f"Saída esperada: {output_path}")

        # Simula saída (não cria shapefile real ainda)
        return {self.OUTPUT: output_path}

    def name(self):
        return "detectar_arvores"

    def displayName(self):
        return "Netflora – Detecção de Árvores"

    def group(self):
        return "Netflora"

    def groupId(self):
        return "netflora"

    def createInstance(self):
        return NetfloraAlgorithm()