# Netflora
Plugin QGIS para detecção de árvores e palmeiras em ortomosaicos usando YOLO (PyTorch/ONNX), gerando camadas vetoriais e relatório HTML.

---

## Visão geral
O **Netflora** automatiza a etapa de inventário florestal a partir de ortomosaicos (GeoTIFF) e modelos YOLO. O plugin:
- executa detecção por janelas (tiles) com sobreposição configurável;
- aplica supressão de duplicidades (NMS) para remover detecções repetidas entre tiles;
- exporta camadas vetoriais (polígonos/centroides) e tabelas de atributos;
- gera **relatório HTML** com métricas e gráficos.

> **Entrada:** ortomosaico georreferenciado (ex.: `.tif/.tiff`)  
> **Saída:** camadas vetoriais (Shapefile/GeoPackage), CSVs e relatório HTML

---

## Requisitos
- **QGIS 3.x** (recomendado: 3.28+)
- Windows / Linux / macOS  
- Modelos YOLO em **ONNX** (`.onnx`) ou pesos PyTorch (`.pt`) (dependendo do modo habilitado no plugin)

> Dica: para reprodutibilidade, mantenha os modelos em `common/weights/` (ou no diretório indicado nas configurações do plugin).

---

## Instalação

### Opção A — Instalar via ZIP (recomendado)
1. Baixe o repositório como `.zip` (ou baixe o `Netflora.zip` da aba *Releases*).
2. No QGIS, vá em **Complementos → Gerenciar e Instalar Complementos…**
3. Clique em **Instalar a partir de ZIP**
4. Selecione o arquivo `.zip` do Netflora e confirme.
5. Reinicie o QGIS, se solicitado.

### Opção B — Instalar como plugin local (desenvolvimento)
1. Clone o repositório:
   ```bash
   git clone https://github.com/karasinski-mauro/Netflora.git
