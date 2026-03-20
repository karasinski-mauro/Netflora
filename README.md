# Netflora - QGIS Plugin for Forest Inventory with Drones

<img src="https://github.com/NetFlora/Netflora/blob/main/inference/images/detection.gif" alt="Netflora Detection Demo" width="1000"/>

---

# Netflora Project

The **Netflora Project** involves the application of geotechnologies, remote sensing and artificial intelligence to support forest automation and carbon stock mapping in native forest areas of the Western Amazon.

This initiative is developed by **Embrapa Acre** with sponsorship from the **JBS Fund for the Amazon**.

Within the project, drones and artificial intelligence are used to automate stages of forest inventory, enabling the identification of strategic species and improving the efficiency of environmental monitoring.

More than **50,000 hectares** of forest areas have already been mapped with the objective of building the Netflora dataset and supporting automated forest inventory methods.

---

<div align="center">

<img src="https://github.com/NetFlora/NetFlora/blob/main/logo/Netflora.png?raw=true" width="260">

<img src="https://github.com/NetFlora/NetFlora/blob/main/logo/Embrapa-Acre.png?raw=true" width="220">

<img src="https://github.com/NetFlora/NetFlora/blob/main/logo/Fundo-JBS.png?raw=true" width="220">

</div>

---

# Netflora QGIS Plugin

The **Netflora QGIS Plugin** integrates detection and flight-planning tools directly into the **QGIS Processing Framework**.

It was designed to support forest inventory workflows using drone imagery, georeferenced orthomosaics and AI-based models for strategic species and vegetation-feature detection.

The plugin currently combines:

- biome-specific detection algorithms
- flight planning for drone missions
- optional PDF reporting
- on-demand model download from GitHub release assets

---

# Main Features

- Automatic detection of forest species and vegetation targets using AI models
- Processing of large orthomosaics using tiled inference
- Support for ONNX-based inference with CPU or GPU runtimes
- Duplicate-removal and filtering of detections
- Export of georeferenced polygon layers with confidence and class attributes
- Optional PDF report generation
- Flight planner for Litchi-compatible drone missions
- Integration with QGIS Processing tools

---

# How the Detection Works

The detection workflow follows these general steps:

1. The orthomosaic is divided into image tiles.
2. Each tile is processed by a category-specific model.
3. Predictions are merged across the full raster.
4. Duplicate detections are filtered.
5. Final detections are exported as georeferenced vector layers.

This approach allows the processing of large rasters without loading the entire image into memory at once.

---

# Available Tools

## Detection Algorithms

Netflora includes tools for multiple biomes and categories, such as:

- **Amazonia**: acai solteiro, acai touceira, castanheira, ecologico, geral, invasora, madeireiros, nao madeireiros and palmeiras
- **Cerrado**: carvao, nao madeireiros and palmeiras
- **Mata Atlantica**: araucaria, madeireiro, nao madeireiro and palmeiras
- **Caatinga**: palmeiras
- **Pantanal**: palmeiras
- **Pampa**: palmeiras
- **Custom**: execution with user-provided model weights

Each algorithm now includes a short in-tool description inside QGIS, together with the Netflora logo and a link to the complete documentation repository.

## Flight Planner

The plugin also includes a flight planner for drone mission preparation, with:

- AOI-based route generation
- orientation by line layer or two user-defined points
- overlap, altitude and speed settings
- CSV export for Litchi
- waypoint and path layers for visualization in QGIS

---

# Inputs

Netflora works with georeferenced raster imagery such as:

- UAV orthomosaics
- aerial imagery
- high-resolution raster imagery

The flight planner also uses polygon layers to define the mapping area.

---

# Outputs

Depending on the selected tool, the plugin can generate:

- polygon detection layers
- class and confidence attributes
- mission paths and waypoint layers
- CSV mission files
- optional PDF reports

---

# Installation

## Install via ZIP in QGIS

1. Download the Netflora plugin ZIP package.
2. Open QGIS.
3. Go to:

`Plugins > Manage and Install Plugins`

4. Click **Install from ZIP**.
5. Select the Netflora ZIP file.
6. Restart QGIS if required.

## Python Dependencies

Depending on the environment, the plugin may require external Python packages in the QGIS Python installation.

Minimum setup:

```bash
python -m pip install --upgrade pip
python -m pip install numpy onnxruntime matplotlib pandas
```

Optional GPU runtimes:

```bash
python -m pip install onnxruntime-gpu
python -m pip install onnxruntime-directml
python -m pip install onnxruntime-openvino
```

On Windows, these commands are usually run from the **OSGeo4W Shell**.

---

# Model Weights

Model weights are **not bundled** inside the plugin ZIP.

When a detection algorithm is executed for the first time, the plugin can automatically download the required `.onnx` model from the configured GitHub release assets:

https://github.com/karasinski-mauro/Netflora/releases/tag/v1.0

If the asset for a given algorithm has not been published yet, the plugin informs the user that the algorithm is still under construction.

Optional `sha256` validation can also be configured for each asset.

---

# Examples of Detection

<div align="center">

<img src="https://github.com/NetFlora/NetFlora/blob/main/inference/images/Acai.jpg?raw=true" width="230">

<img src="https://github.com/NetFlora/NetFlora/blob/main/inference/images/Palmeiras.jpg?raw=true" width="250">

<img src="https://github.com/NetFlora/NetFlora/blob/main/inference/images/PFMNs.jpg?raw=true" width="230">

</div>

---

# Documentation and Links

## Official Project Page

https://www.embrapa.br/acre/netflora

## Repository and Full Documentation

https://github.com/karasinski-mauro/Netflora

## Example Data

https://drive.google.com/drive/folders/1OcRel7fJHALwm9ZAdU3rSlFwV_4iaZnp?usp=sharing

## Course

https://ava.sede.embrapa.br/enrol/index.php?id=470

## FAQ

https://www.embrapa.br/web/portal/acre/tecnologias/netflora/perguntas-e-respostas

## Embrapa Acre

https://www.embrapa.br/acre/

## JBS Fund for the Amazon

https://fundojbsamazonia.org/

---

# Author and Institution

**Authors:** Mauro Alessandro Karasinski <br>
**Project Coordinator:** Evandro Orfanó Figueiredo <br>
**Institution:** Embrapa Acre <br>
**Project page:** https://www.embrapa.br/acre/netflora <br>
**Support:** https://fundojbsamazonia.org/

---

# License

Distributed under the **GNU General Public License v3.0 (GPL-3.0)**.

See `LICENSE` for more information.

---

# Acknowledgements

We acknowledge the support of the open-source geospatial and computer vision communities, including the broader ecosystems around QGIS, ONNX Runtime and YOLO-based workflows.
