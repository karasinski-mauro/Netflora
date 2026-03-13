# Netflora – QGIS Plugin for Automatic Tree Detection

<img src="https://github.com/NetFlora/Netflora/blob/main/inference/images/detection.gif" alt="Netflora Detection Demo" width="1000"/>

**Read this in other languages**: [Português](README.pt.md), [Español](README.es.md)

<a href="https://colab.research.google.com/drive/16nydPteUlpXo1tcIC0DWrQr05Z3m-npU?usp=sharing">
<img src="https://colab.research.google.com/assets/colab-badge.svg">
</a>

---

# Netflora Project

The **Netflora Project** involves the application of geotechnologies, remote sensing and artificial intelligence to support forest automation and carbon stock mapping in native forest areas of the Western Amazon.

This initiative is developed by **Embrapa Acre** with sponsorship from the **JBS Fund for the Amazon**.

Within the project, drones and artificial intelligence are used to automate stages of the forest inventory, enabling the identification of strategic species and improving the efficiency of environmental monitoring.

More than **50,000 hectares of forest areas** have already been mapped with the objective of building a dataset to support the development of automated forest inventory methods.

---

<div align="center">

<img src="https://github.com/NetFlora/NetFlora/blob/main/logo/Netflora.png?raw=true" width="200">

<img src="https://github.com/NetFlora/NetFlora/blob/main/logo/Embrapa-Acre.png?raw=true" width="200">

<img src="https://github.com/NetFlora/NetFlora/blob/main/logo/Fundo-JBS.png?raw=true" width="200">

</div>

---

# Netflora QGIS Plugin

The **Netflora QGIS Plugin** allows users to detect trees and vegetation features automatically from georeferenced orthomosaics using deep learning models based on the **YOLO architecture**.

The plugin integrates AI-based detection directly into the **QGIS Processing Framework**, allowing users to perform automated detection workflows within a GIS environment.

---

# Main Features

• Automatic tree detection using YOLO deep learning models  
• Processing of large orthomosaics using **sliding window inference**  
• Support for **ONNX and PyTorch models**  
• Execution using **CPU or GPU**  
• Removal of duplicate detections using **Non-Maximum Suppression (NMS)**  
• Export of **bounding boxes and centroids as georeferenced vector layers**  
• Automatic **HTML report generation** with detection statistics  
• Integration with **QGIS Processing tools**

---

# How the Detection Works

The detection workflow follows these steps:

1. The orthomosaic is divided into image **tiles**.
2. Each tile is analyzed using a YOLO detection model.
3. Predictions from all tiles are merged.
4. Duplicate detections between overlapping tiles are removed using **Non-Maximum Suppression (NMS)**.
5. Final detections are converted into **georeferenced vector layers**.

This approach allows the processing of very large orthomosaics without loading the entire raster into memory.

---

# Inputs

Netflora accepts georeferenced raster imagery such as:

• UAV orthomosaics  
• Aerial imagery  
• High-resolution satellite imagery  

Supported formats include:

.tif  
.tiff  

---

# Outputs

After processing, the plugin generates:

• Bounding box vector layer  
• Centroid vector layer  
• Attribute table with predicted class and confidence  
• CSV summary files  
• HTML report with detection statistics

Supported formats include:

• Shapefile (.shp)  
• GeoPackage (.gpkg)  
• CSV  
• HTML report  

---

# Examples of Detection

<div align="center">

<img src="https://github.com/NetFlora/NetFlora/blob/main/inference/images/Acai.jpg?raw=true" width="230">

<img src="https://github.com/NetFlora/NetFlora/blob/main/inference/images/Palmeiras.jpg?raw=true" width="250">

<img src="https://github.com/NetFlora/NetFlora/blob/main/inference/images/PFMNs.jpg?raw=true" width="230">

</div>

---

# Installation

## Install via ZIP (recommended)

1. Download the Netflora plugin `.zip`
2. Open QGIS
3. Navigate to:

Plugins → Manage and Install Plugins

4. Click **Install from ZIP**
5. Select the Netflora ZIP file
6. Restart QGIS if required

---

# Python Dependencies

Depending on the inference mode, the following libraries may be required:

numpy  
onnxruntime  
torch  
ultralytics  

### Installing Dependencies (Windows)

Open **OSGeo4W Shell** and run:

python -m pip install --upgrade pip  
python -m pip install numpy onnxruntime  

For GPU acceleration:

python -m pip install onnxruntime-gpu  

---

# Running Detection via Python

Example command:

python detect.py --device 0 --weights model_weights.pt --img 1536

---

# Visualizing Detection Results

python results.py --graphics --conf 0.25

---

# Website

https://www.embrapa.br/acre/netflora

---

# Useful Links

Orthophoto example download  
https://drive.google.com/drive/folders/1OcRel7fJHALwm9ZAdU3rSlFwV_4iaZnp?usp=sharing

EAD Course  
https://ava.sede.embrapa.br/enrol/index.php?id=470

FAQ  
https://www.embrapa.br/web/portal/acre/tecnologias/netflora/perguntas-e-respostas

Embrapa Acre  
https://www.embrapa.br/acre/

JBS Fund for the Amazon  
https://fundojbsamazonia.org/

---

# License

Distributed under the **GNU General Public License v3.0 (GPL-3.0)**.

See LICENSE for more information.

---

# Citation

If you use Netflora in academic research, please cite:

Karasinski, M. A.  
Netflora – Deep Learning for Automated Forest Inventory using UAV Imagery.

---

# Acknowledgements

We acknowledge the contributions of the open-source computer vision community.

https://github.com/AlexeyAB/darknet  
https://github.com/WongKinYiu/yolov7  

---

We appreciate your interest in the Netflora project!
