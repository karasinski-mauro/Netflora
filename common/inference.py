# -*- coding: utf-8 -*-
import os
import numpy as np
from osgeo import gdal
import subprocess
import shutil

def _resize_bilinear(img_hwc: np.ndarray, out_w: int, out_h: int) -> np.ndarray:
    """
    Redimensiona HxWxC para (out_h, out_w, C) via bilinear puro NumPy.
    """
    in_h, in_w, C = img_hwc.shape
    if in_h == out_h and in_w == out_w:
        return img_hwc.copy()

    # coordenadas alvo
    y = np.linspace(0, in_h - 1, out_h)
    x = np.linspace(0, in_w - 1, out_w)
    xg, yg = np.meshgrid(x, y)

    x0 = np.floor(xg).astype(np.int32)
    y0 = np.floor(yg).astype(np.int32)
    x1 = np.clip(x0 + 1, 0, in_w - 1)
    y1 = np.clip(y0 + 1, 0, in_h - 1)

    # pesos
    wa = (x1 - xg) * (y1 - yg)
    wb = (xg - x0) * (y1 - yg)
    wc = (x1 - xg) * (yg - y0)
    wd = (xg - x0) * (yg - y0)

    out = np.empty((out_h, out_w, C), dtype=img_hwc.dtype)
    for c in range(C):
        Ia = img_hwc[y0, x0, c]
        Ib = img_hwc[y0, x1, c]
        Ic = img_hwc[y1, x0, c]
        Id = img_hwc[y1, x1, c]
        out[..., c] = Ia * wa + Ib * wb + Ic * wc + Id * wd

    return out



def _probe_nvidia_vram_mb():
    # 1) NVML (se disponível)
    try:
        import pynvml
        pynvml.nvmlInit()
        h = pynvml.nvmlDeviceGetHandleByIndex(0)
        mem = pynvml.nvmlDeviceGetMemoryInfo(h)
        total_mb = int(mem.total / (1024*1024))
        free_mb  = int(mem.free  / (1024*1024))
        pynvml.nvmlShutdown()
        return total_mb, free_mb
    except Exception:
        pass

    # 2) nvidia-smi (se existir no PATH)
    try:
        if shutil.which("nvidia-smi"):
            out = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=memory.total,memory.free", "--format=csv,noheader,nounits"],
                universal_newlines=True, stderr=subprocess.STDOUT
            ).strip()
            # pega a 1ª GPU: "total, free"
            first = out.splitlines()[0].split(',')
            total_mb = int(first[0].strip())
            free_mb  = int(first[1].strip())
            return total_mb, free_mb
    except Exception:
        pass

    return None, None  
#--------------------------------------------------------------------------------------------

def _choose_tile_from_vram(provider, total_mb, free_mb):
    return 1024, 512
#---------------------------------------------
# 
# 
# 
# 
# -----------------------------------------------

def _load_ort_session(model_path, feedback):
    def _log(msg):
        try: feedback.pushInfo(msg)
        except Exception: pass

    try:
        import onnxruntime as ort
    except Exception as e:
        _log(f"[Netflora] onnxruntime ausente: {e}")
        return None, None

    try:
        avail = ort.get_available_providers()
    except Exception:
        avail = []
    _log(f"[Netflora] ORT providers: {avail}")

    so = ort.SessionOptions()
    so.log_severity_level = 1
    if hasattr(ort, "GraphOptimizationLevel"):
        so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

    # 1) TensorRT 
    if "TensorrtExecutionProvider" in avail:
        for ws_gb in (4, 2, 1):  # tente 4GB → 2GB → 1GB
            trt_opts = {
                "device_id": 0,
                "trt_engine_cache_enable": True,
                "trt_fp16_enable": True,
                "trt_max_workspace_size": ws_gb * 1024 * 1024 * 1024,
            }
            try:
                sess = ort.InferenceSession(
                    model_path, sess_options=so,
                    providers=[("TensorrtExecutionProvider", trt_opts)]
                )
                _log(f"[Netflora] Using TensorrtExecutionProvider (workspace={ws_gb}GB, fp16=True)")
                return sess, "TensorrtExecutionProvider"
            except Exception as e:
                _log(f"[Netflora] TensorRT falhou (workspace={ws_gb}GB): {e}")

    # 2) CUDA
    if "CUDAExecutionProvider" in avail:
        cuda_opts = {
            "device_id": 0,
            "arena_extend_strategy": "kNextPowerOfTwo",
            "cudnn_conv_use_max_workspace": "1",
        }
        try:
            sess = ort.InferenceSession(
                model_path, sess_options=so,
                providers=[("CUDAExecutionProvider", cuda_opts)]
            )
            _log("[Netflora] Using CUDAExecutionProvider")
            return sess, "CUDAExecutionProvider"
        except Exception as e:
            _log(f"[Netflora] CUDA falhou: {e}")

        # Tente CUDA
        try:
            sess = ort.InferenceSession(
                model_path, sess_options=so,
                providers=[("CUDAExecutionProvider", {"device_id": 0}), "CPUExecutionProvider"]
            )
            used = sess.get_providers()[0]
            _log(f"[Netflora] Using {used} (CUDA+CPU fallback)")
            return sess, used
        except Exception as e:
            _log(f"[Netflora] CUDA+CPU falhou: {e}")

    # 3) DirectML (AMD/Intel)
    if "DmlExecutionProvider" in avail:
        try:
            sess = ort.InferenceSession(
                model_path, sess_options=so,
                providers=["DmlExecutionProvider", "CPUExecutionProvider"]
            )
            used = sess.get_providers()[0]
            _log(f"[Netflora] Using {used} (DirectML)")
            return sess, used
        except Exception as e:
            _log(f"[Netflora] DirectML falhou: {e}")

    # 4) CPU
    try:
        sess = ort.InferenceSession(model_path, sess_options=so, providers=["CPUExecutionProvider"])
        _log("[Netflora] Using CPUExecutionProvider (fallback)")
        return sess, "CPUExecutionProvider"
    except Exception as e:
        _log(f"[Netflora] CPU falhou: {e}")
        return None, None


def _log(feedback, msg):
    try:
        feedback.pushInfo(msg)
    except Exception:
        pass

def _read_tile_gdal(ds, xoff, yoff, xsize, ysize, bands=(1,2,3)):
    arrays = []
    for b in bands:
        band = ds.GetRasterBand(b)
        arr = band.ReadAsArray(xoff, yoff, xsize, ysize)
        if arr is None:
            return None
        arrays.append(arr)
    img = np.stack(arrays, axis=-1)
    return img

def _preprocess(img_hwc: np.ndarray) -> np.ndarray:
    img = img_hwc.astype(np.float32) / 255.0
    img = _resize_bilinear(img, 640, 640)
    img = np.transpose(img, (2, 0, 1))
    return img[None, ...].astype(np.float32)


def import_ort_and_create_cuda_session(model_path, sess_options, cuda_opts, fallback_cpu=True):
    import onnxruntime as ort
    providers = [("CUDAExecutionProvider", cuda_opts)]
    if fallback_cpu:
        providers.append("CPUExecutionProvider")
    return ort.InferenceSession(model_path, sess_options=sess_options, providers=providers)

def _parse_output(outputs):
    if isinstance(outputs, (list, tuple)) and len(outputs) == 1:
        out = outputs[0]
    else:
        out = outputs
    out = np.squeeze(out)
    if out.ndim == 1:
        out = out[None, :]
    dets = []
    for row in out:
        if row.shape[-1] >= 6:
            x1, y1, x2, y2, conf, cls = row[:6]
            dets.append((float(x1), float(y1), float(x2), float(y2), float(conf), int(cls)))
    return dets

def center_inside(a, b):
    cx = (a[0] + a[2]) / 2.0
    cy = (a[1] + a[3]) / 2.0
    return b[0] <= cx <= b[2] and b[1] <= cy <= b[3]

def iou(a, b):
    xA = max(a[0], b[0]); yA = max(a[1], b[1])
    xB = min(a[2], b[2]); yB = min(a[3], b[3])
    inter = max(0, xB - xA) * max(0, yB - yA)
    if inter <= 0:
        return 0.0
    areaA = (a[2] - a[0]) * (a[3] - a[1])
    areaB = (b[2] - b[0]) * (b[3] - b[1])
    return inter / float(areaA + areaB - inter)

def apply_iou_nms_with_center_overlap(dets, iou_threshold=0.64):
    if not dets:
        return []
    dets = sorted(dets, key=lambda x: x[5], reverse=True)
    keep = []
    while dets:
        best = dets.pop(0)
        keep.append(best)
        dets = [d for d in dets if not (iou(d, best) >= iou_threshold or center_inside(d, best))]
    return keep

def run_detection(raster_layer, model_path: str, confidence_threshold: float, feedback):
    if not os.path.exists(model_path):
        _log(feedback, f"[Netflora] Modelo não encontrado: {model_path}")
        return []

    sess, provider = _load_ort_session(model_path, feedback)
    if sess is None:
        return []
    _log(feedback, f"[Netflora] onnxruntime provider: {provider}")

    image_path = raster_layer.source()
    ds = gdal.Open(image_path, gdal.GA_ReadOnly)
    if ds is None:
        _log(feedback, f"[Netflora] ERRO ao abrir raster: {image_path}")
        return []

    width = ds.RasterXSize
    height = ds.RasterYSize
    gt = ds.GetGeoTransform()
    x0, pxW, _, y0, _, neg_pxH = gt
    res_x = pxW
    res_y = abs(neg_pxH) if neg_pxH != 0 else pxW
    top_left_x = x0
    top_left_y = y0

    # --- tiling adaptativo por VRAM
    total_mb, free_mb = _probe_nvidia_vram_mb()
    window_size, step_size = _choose_tile_from_vram(provider, total_mb, free_mb)
    _log(feedback, f"[Netflora] Tiling inicial: window={window_size}, step={step_size} (VRAM total/free = {total_mb}/{free_mb} MB)")

    input_name = sess.get_inputs()[0].name
    raw = []

    def _try_forward(pre):
        # executa uma inferência e permite capturar erros de OOM para backoff
        try:
            out = sess.run(None, {input_name: pre})
            return out
        except Exception as e:
            msg = str(e)
            # sinais comuns de OOM: CUBLAS/CUDNN/allocator/RESOURCE_EXHAUSTED
            if any(k in msg.upper() for k in ("RESOURCE_EXHAUSTED", "CUBLAS", "CUDNN", "OUT OF MEMORY", "CUDA ERROR")):
                return "OOM"
            return e

    # loop com backoff se OOM
    backoff_chain = [1.0, 0.8, 0.67, 0.5]  # reduz tile gradualmente
    for scale in backoff_chain:
        ws = int(max(512, window_size * scale))
        ss = max(256, int(step_size * scale))
        total = ((height - 1) // ss + 1) * ((width - 1) // ss + 1)
        _log(feedback, f"[Netflora] Tiling em uso: window={ws}, step={ss} (total janelas ~ {total})")

        ok = True
        count = 0

        for y in range(0, height, ss):
            for x in range(0, width, ss):
                if getattr(feedback, 'isCanceled', lambda: False)():
                    _log(feedback, "[Netflora] Cancelado.")
                    return []

                ww = min(ws, width - x)
                hh = min(ws, height - y)
                if ww <= 0 or hh <= 0:
                    continue

                img = _read_tile_gdal(ds, x, y, ww, hh, bands=(1,2,3))
                if img is None or img.size == 0 or np.all(img == 0):
                    count += 1
                    continue

                # --- Garantir padding nas bordas ---
                if img.shape[0] != ws or img.shape[1] != ws:
                    pad_h = ws - img.shape[0]
                    pad_w = ws - img.shape[1]
                    img = np.pad(
                        img,
                        ((0, pad_h), (0, pad_w), (0, 0)),  # (H, W, C)
                        mode="constant"
                    )

                pre = _preprocess(img)
                out = _try_forward(pre)
                if out == "OOM":
                    _log(feedback, f"[Netflora] OOM com window={ws}, step={ss} na janela ({x},{y}). Tentando reduzir tile...")
                    ok = False
                    break  # sai do loop para diminuir o tile
                elif isinstance(out, Exception):
                    _log(feedback, f"[Netflora] Falha no forward: {out}")
                    return []

                dets = _parse_output(out)
                sx = ww / 640.0
                sy = hh / 640.0
                for x1, y1, x2, y2, conf, cls in dets:
                    if conf < confidence_threshold:
                        continue
                    x_min = x1 * sx
                    x_max = x2 * sx
                    y_min = y1 * sy
                    y_max = y2 * sy
                    bw = (x_max - x_min) * res_x
                    bh = (y_max - y_min) * res_y
                    if bw <= 0 or bh <= 0:
                        continue
                    if bw < 1 or bh < 1 or bw > 20 or bh > 150:
                        continue
                    ar = bw / bh if bh > 0 else 0
                    if ar < 0.3 or ar > 3.0:
                        continue
                    gxmin = float(top_left_x + (x + x_min) * res_x)
                    gxmax = float(top_left_x + (x + x_max) * res_x)
                    gymin_pix = (y + y_max)
                    gymax_pix = (y + y_min)
                    gymin = float(top_left_y + gymin_pix * neg_pxH)
                    gymax = float(top_left_y + gymax_pix * neg_pxH)
                    if gymin > gymax:
                        gymin, gymax = gymax, gymin
                    raw.append((gxmin, gymin, gxmax, gymax, int(cls), float(conf)))

                count += 1
                if count % 20 == 0:
                    _log(feedback, f"[Netflora] Janelas: {count}/{total}")

            if not ok:
                break

        if ok:
            break  # tiling atual funcionou; sai do backoff

    kept = apply_iou_nms_with_center_overlap(raw, iou_threshold=0.85)
    return kept
