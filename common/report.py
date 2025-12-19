# -*- coding: utf-8 -*-
import os
import io
import tempfile
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

try:
    import seaborn as sns
    _HAS_SNS = True
except Exception:
    _HAS_SNS = False

from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.pagesizes import A4

from qgis.core import QgsVectorLayer

# ========================== CONFIG ==========================
HEADER_ICON_FILENAMES   = [ "Embrapa-Acre.png","Netflora.png", "Fundo-JBS.png"]
HEADER_ICON_HEIGHT_CM   = 2.0         # ↑ logos maiores

HEADER_ICON_HEIGHTS_CM = {
    "Netflora.png": 2.6,   # ← um pouco maior só a primeira (ajuste à vontade)
    # "Embrapa-Acre.png": 2.0,
    # "Fundo-JBS.png": 2.0,
}


HEADER_LINE_COLOR       = colors.HexColor("#1B5E20")  # verde escuro
HEADER_LINE_WIDTH_PT    = 4.0         # linha verde espessa
HEADER_LINE_GAP_CM      = 0.18        # distância da base dos logos até a linha

FOOTER_LINE_Y_CM        = 1.2         # altura da linha horizontal (a partir da base)
FOOTER_TEXT_Y_CM        = 0.8         # altura do texto (uma linha)
FOOTER_FONT_NAME        = "Helvetica"
FOOTER_FONT_SIZE        = 7           # ↓ fonte menor
FOOTER_SEP              = " | "       # separador vertical

FOOTER_SITE_URL         = "https://www.embrapa.br/en/acre/netflora"
FOOTER_ADDRESS          = "Endereço: Rodovia BR-364, Km 14, Rio Branco - AC, 69900-970"
FOOTER_EMAIL            = "netfloraembrapa@gmail.com"

# margens base
BASE_LEFT_CM  = 1.5
BASE_RIGHT_CM = 1.5
BASE_TOP_CM   = 1.5
BASE_BOT_CM   = 1.5

# ---------------------------- plotting helpers ---------------------------- #

def _matplotlib_defaults():
    plt.rcParams.update({
        "font.size": 8,
        "axes.titlesize": 10,
        "axes.labelsize": 8,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "legend.fontsize": 7,
        "figure.dpi": 120,
        "savefig.dpi": 200,
    })

def _nice_axis(ax, title, xlabel, ylabel):
    ax.set_title(title, fontweight="bold")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, axis="y", alpha=0.25)

def _adaptive_xtick_fontsize(n_labels: int) -> int:
    if n_labels <= 8:   return 9
    if n_labels <= 12:  return 8
    if n_labels <= 18:  return 7
    if n_labels <= 26:  return 6
    if n_labels <= 40:  return 5
    return 4

def _apply_xtick_styling(ax, n_labels: int):
    fs = _adaptive_xtick_fontsize(n_labels)
    for lab in ax.get_xticklabels():
        lab.set_fontsize(fs)
    rot = 25 if n_labels <= 20 else 40
    ax.tick_params(axis="x", rotation=rot)
    ax.margins(x=0.02)

def _auto_fig_width(n_labels: int, base=6.4, per_10=0.8, min_w=6.0, max_w=10.0):
    if n_labels <= 10:
        return base
    extra_blocks = max(0, (n_labels - 10)) / 10.0
    w = base + extra_blocks * per_10
    return max(min_w, min(max_w, w))

def _palette_for(labels):
    cmaps = [plt.cm.get_cmap("tab20"),
             plt.cm.get_cmap("tab20b"),
             plt.cm.get_cmap("tab20c")]
    out = {}
    for i, lab in enumerate(labels):
        cmap = cmaps[(i // 20) % len(cmaps)]
        out[lab] = cmap((i % 20) / 19.0)
    return out

def _save_fig_to_tmp(fig, name):
    path = os.path.join(tempfile.gettempdir(), name)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path

# -------------------------- content helpers -------------------------- #

def _safe_get(f, name, default=None):
    return f[name] if name in f.fields().names() else default

def _fmt_int(x):
    try:
        return f"{int(x):,}".replace(",", ".")
    except Exception:
        return str(x)

def _try_fetch_image(src_path_or_url, desired_width_cm=12):
    try:
        if isinstance(src_path_or_url, (list, tuple)):
            src_path_or_url = src_path_or_url[0]
        if str(src_path_or_url).lower().startswith(("http://", "https://")):
            import urllib.request
            tmpf = os.path.join(
                tempfile.gettempdir(),
                os.path.basename(str(src_path_or_url)).split("?")[0] or "netflora_img.jpg"
            )
            urllib.request.urlretrieve(src_path_or_url, tmpf)
            img_path = tmpf
        else:
            img_path = src_path_or_url
        return Image(img_path, width=desired_width_cm*cm, height=desired_width_cm*0.66*cm)
    except Exception:
        return None

# ------------------------- KDE + hist helpers ------------------------- #

def _freedman_diaconis_bins(x, max_bins=60):
    x = np.asarray(x); x = x[np.isfinite(x)]
    n = x.size
    if n < 2: return 10
    q75, q25 = np.percentile(x, [75 ,25]); iqr = q75 - q25
    if iqr <= 0: return min(max_bins, max(5, int(np.sqrt(n))))
    h = 2.0 * iqr * n ** (-1/3)
    if h <= 0:  return min(max_bins, max(5, int(np.sqrt(n))))
    bins = int(np.ceil((x.max() - x.min()) / h))
    return max(10, min(max_bins, bins))

def _silverman_bandwidth(x):
    x = np.asarray(x); x = x[np.isfinite(x)]
    n = x.size
    if n < 2: return np.std(x) if n == 1 else 1.0
    sigma = np.std(x, ddof=1)
    if sigma <= 0: sigma = 1e-6
    return 1.06 * sigma * n ** (-1/5)

def _kde_gaussian(x_grid, samples, bw=None):
    x = np.asarray(samples); x = x[np.isfinite(x)]
    if x.size == 0: return np.zeros_like(x_grid, dtype=float)
    if not bw or bw <= 0: bw = _silverman_bandwidth(x)
    u = (x_grid[:, None] - x[None, :]) / bw
    dens = np.exp(-0.5 * u * u).sum(axis=1) / (x.size * bw * np.sqrt(2.0 * np.pi))
    return dens

def _plot_hist_with_density(ax, data, xlabel="Diameter (m)"):
    x = np.asarray(data); x = x[np.isfinite(x)]
    if x.size == 0:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes); return
    bins = _freedman_diaconis_bins(x, max_bins=60)
    ax.hist(x, bins=bins, density=True)
    ax.set_xlabel(xlabel); ax.set_ylabel("Density"); ax.grid(True, axis="y", alpha=0.25)
    x_min, x_max = float(np.min(x)), float(np.max(x))
    pad = 0.05 * (x_max - x_min) if x_max > x_min else 0.5
    grid = np.linspace(x_min - pad, x_max + pad, 400)
    dens = _kde_gaussian(grid, x, bw=_silverman_bandwidth(x))
    ax.plot(grid, dens, linewidth=2)

# ----------------------- header/footer (logos & texto) ----------------------- #

def _resolve_icon_paths():
    """
    Resolve caminhos absolutos para os 3 ícones em common/icons ao lado deste arquivo.
    """
    here = os.path.dirname(__file__)            # .../common
    icons_dir = os.path.join(here, "icons")     # .../common/icons
    paths = []
    for fn in HEADER_ICON_FILENAMES:
        p = os.path.join(icons_dir, fn)
        if os.path.isfile(p):
            paths.append(p)
    return paths

def _build_onpage_drawer(header_icon_paths, left_cm, right_cm):
    """
    Desenha:
      - Cabeçalho: 3 logos alinhados e, abaixo, uma linha verde espessa.
      - Rodapé: linha horizontal e, abaixo, uma única linha centralizada:
                site | endereço | e-mail (com links no site e no e-mail).
    """
    def _drawer(canvas, doc):
        from reportlab.lib.utils import ImageReader
        page_w, page_h = doc.pagesize
        x0 = left_cm * cm
        x1 = page_w - right_cm * cm
        usable_w = max(1, x1 - x0)

        # ----- Header icons -----
        y_top_line = None
        if header_icon_paths:
            # alturas alvo por arquivo (cm)
            heights_cm = [
                HEADER_ICON_HEIGHTS_CM.get(os.path.basename(p), HEADER_ICON_HEIGHT_CM)
                for p in header_icon_paths
            ]
            max_h_cm = max(heights_cm) if heights_cm else HEADER_ICON_HEIGHT_CM
            y_base = page_h - (max_h_cm * cm) - 0.35*cm  # alinhar pela base

            n = len(header_icon_paths)
            cell_w = usable_w / n
            for i, p in enumerate(header_icon_paths):
                try:
                    ir = ImageReader(p)
                    iw, ih = ir.getSize()
                    target_h = heights_cm[i] * cm
                    scale = target_h / float(ih)
                    w = iw * scale
                    h = ih * scale
                    if w > cell_w:
                        scale = cell_w / float(iw)
                        w = iw * scale
                        h = ih * scale
                    cx = x0 + i*cell_w + (cell_w - w)/2.0
                    canvas.drawImage(ir, cx, y_base, width=w, height=h,
                                    preserveAspectRatio=True, mask="auto")
                except Exception:
                    continue

            # linha verde sob os logos
            y_top_line = y_base - HEADER_LINE_GAP_CM*cm
        else:
            y_top_line = page_h - (BASE_TOP_CM*cm) - 0.3*cm

        canvas.setStrokeColor(HEADER_LINE_COLOR)
        canvas.setLineWidth(HEADER_LINE_WIDTH_PT)
        canvas.line(x0, y_top_line, x1, y_top_line)

        # ----- Footer line + single centered text -----
        canvas.setStrokeColor(colors.black)
        canvas.setLineWidth(0.6)
        y_line = FOOTER_LINE_Y_CM * cm
        canvas.line(x0, y_line, x1, y_line)

        canvas.setFont(FOOTER_FONT_NAME, FOOTER_FONT_SIZE)

        site_text = FOOTER_SITE_URL
        addr_text = FOOTER_ADDRESS
        mail_text = FOOTER_EMAIL
        sep = FOOTER_SEP

        # medir cada trecho
        tw_site = canvas.stringWidth(site_text, FOOTER_FONT_NAME, FOOTER_FONT_SIZE)
        tw_sep  = canvas.stringWidth(sep, FOOTER_FONT_NAME, FOOTER_FONT_SIZE)
        tw_addr = canvas.stringWidth(addr_text, FOOTER_FONT_NAME, FOOTER_FONT_SIZE)
        tw_mail = canvas.stringWidth(mail_text, FOOTER_FONT_NAME, FOOTER_FONT_SIZE)

        tw_total = tw_site + tw_sep + tw_addr + tw_sep + tw_mail
        x_start = (page_w - tw_total) / 2.0
        y_text = FOOTER_TEXT_Y_CM * cm

        # desenha mantendo posições para links
        x = x_start
        canvas.drawString(x, y_text, site_text)
        canvas.linkURL(site_text, (x, y_text - 1, x + tw_site, y_text + FOOTER_FONT_SIZE + 1), relative=0)
        x += tw_site
        canvas.drawString(x, y_text, sep)
        x += tw_sep
        canvas.drawString(x, y_text, addr_text)
        x += tw_addr
        canvas.drawString(x, y_text, sep)
        x += tw_sep
        canvas.drawString(x, y_text, mail_text)
        canvas.linkURL(f"mailto:{mail_text}", (x, y_text - 1, x + tw_mail, y_text + FOOTER_FONT_SIZE + 1), relative=0)

    return _drawer

# ------------------------------- main -------------------------------- #

def generate_report(
        vector_layer: QgsVectorLayer,
        raster_layer,  # compat apenas
        biome,
        category,
        output_pdf,
        *,
        min_conf=None,
        extra_images=None,
        show_hist=True
    ):
    """
    Relatório com:
      • Cabeçalho: Netflora.png, Embrapa-Acre.png, Fundo-JBS.png (de common/icons) + linha verde
      • Rodapé: linha + (site | endereço | e-mail) centralizado, com links
      • Cores por espécie, eixos adaptativos, histograma + KDE
    """
    _matplotlib_defaults()
    styles = getSampleStyleSheet()
    normal = styles["Normal"]; title = styles["Title"]
    h2 = styles["Heading2"]; h3 = styles["Heading3"]
    body = ParagraphStyle("body", parent=normal, leading=12)
    warn = ParagraphStyle("warn", parent=normal, textColor=colors.red, leading=12)

    # Header icons
    header_icon_paths = _resolve_icon_paths()

    # margens: aumenta topo para caber logos e linha; base para caber linha + 1 linha de texto
    left_cm  = BASE_LEFT_CM
    right_cm = BASE_RIGHT_CM
    top_cm   = BASE_TOP_CM + (HEADER_ICON_HEIGHT_CM + 0.7 if header_icon_paths else 0.4)
    bottom_reserve_cm = max(1.6, FOOTER_LINE_Y_CM + 0.3)  # linha + 1 linha de texto
    bot_cm   = BASE_BOT_CM + bottom_reserve_cm

    doc = SimpleDocTemplate(
        output_pdf, pagesize=A4,
        leftMargin=left_cm*cm, rightMargin=right_cm*cm,
        topMargin=top_cm*cm, bottomMargin=bot_cm*cm
    )

    story = []
    story.append(Paragraph("🌿 Netflora — Detection Report", title))
    story.append(Paragraph(f"<b>Biome:</b> {biome} &nbsp;&nbsp; <b>Category:</b> {category}", body))
    if min_conf is not None:
        story.append(Paragraph(f"<b>Confidence filter:</b> ≥ {min_conf:.2f}", body))
    story.append(Spacer(1, 0.35*cm))

    # ---- Extract attributes safely ----
    records = []
    if vector_layer is None or not isinstance(vector_layer, QgsVectorLayer):
        story.append(Paragraph("⚠ No layer or invalid vector layer provided.", warn))
        onpage = _build_onpage_drawer(header_icon_paths, left_cm, right_cm)
        doc.build(story, onFirstPage=onpage, onLaterPages=onpage)
        return output_pdf

    field_names = vector_layer.fields().names()
    has_common = "common_name" in field_names
    has_sci    = "sci_name" in field_names

    for f in vector_layer.getFeatures():
        cid = _safe_get(f, "class_id")
        if cid is None:
            cid = _safe_get(f, "label", _safe_get(f, "class", None))
        conf = _safe_get(f, "conf")
        w    = _safe_get(f, "width")
        h    = _safe_get(f, "height")
        if w is None or h is None:
            bbox = f.geometry().boundingBox() if f and f.geometry() else None
            if bbox is not None:
                w = float(bbox.width())  if w is None else float(w)
                h = float(bbox.height()) if h is None else float(h)
        rec = {
            "class_id": cid,
            "conf": float(conf) if conf is not None else None,
            "width": float(w) if w is not None else None,
            "height": float(h) if h is not None else None,
        }
        if has_common: rec["common_name"] = _safe_get(f, "common_name")
        if has_sci:    rec["sci_name"]    = _safe_get(f, "sci_name")
        records.append(rec)

    if not records:
        story.append(Paragraph("⚠ No detections found.", warn))
        onpage = _build_onpage_drawer(header_icon_paths, left_cm, right_cm)
        doc.build(story, onFirstPage=onpage, onLaterPages=onpage)
        return output_pdf

    df = pd.DataFrame(records)

    if min_conf is not None and "conf" in df.columns:
        df = df[df["conf"].fillna(0) >= min_conf].copy()

    if df.empty:
        story.append(Paragraph("⚠ All detections filtered out by confidence threshold.", warn))
        onpage = _build_onpage_drawer(header_icon_paths, left_cm, right_cm)
        doc.build(story, onFirstPage=onpage, onLaterPages=onpage)
        return output_pdf

    df["diameter"] = (df["width"].fillna(0) + df["height"].fillna(0)) / 2.0

    if has_common and df["common_name"].notna().any():
        df["label"] = df["common_name"].fillna(df["class_id"].astype(str))
    elif has_sci and df["sci_name"].notna().any():
        df["label"] = df["sci_name"].fillna(df["class_id"].astype(str))
    else:
        df["label"] = df["class_id"].astype(str)

    total = len(df)
    num_labels = df["label"].nunique()

    agg = (
        df.groupby("label", as_index=False)
          .agg(count=("label", "size"),
               mean_diameter=("diameter", "mean"),
               max_diameter=("diameter", "max"),
               min_diameter=("diameter", "min"))
          .sort_values("count", ascending=False)
          .reset_index(drop=True)
    )
    agg["percent"] = 100.0 * agg["count"] / total

    story.append(Paragraph(
        f"<b>Total detections:</b> {_fmt_int(total)} individuals across {num_labels} classes/species.",
        body
    ))
    story.append(Spacer(1, 0.2*cm))

    top_by_count = agg.iloc[0]
    bottom_by_count = agg.iloc[-1]
    top_by_mean_diam  = agg.sort_values("mean_diameter", ascending=False).iloc[0]
    bottom_by_mean_diam = agg.sort_values("mean_diameter", ascending=True).iloc[0]

    overall_mean_d = df["diameter"].mean()
    overall_med_d  = df["diameter"].median()
    overall_max_d  = df["diameter"].max()
    overall_min_d  = df["diameter"].min()

    insights = f"""
    • Most frequent: <b>{top_by_count['label']}</b> with {_fmt_int(top_by_count['count'])} ({top_by_count['percent']:.1f}%).
    • Least frequent: <b>{bottom_by_count['label']}</b> with {_fmt_int(bottom_by_count['count'])} ({bottom_by_count['percent']:.1f}%).
    • Largest mean diameter: <b>{top_by_mean_diam['label']}</b> ({top_by_mean_diam['mean_diameter']:.2f} m).
    • Smallest mean diameter: <b>{bottom_by_mean_diam['label']}</b> ({bottom_by_mean_diam['mean_diameter']:.2f} m).
    • Overall diameter: mean = {overall_mean_d:.2f} m, median = {overall_med_d:.2f} m, min = {overall_min_d:.2f} m, max = {overall_max_d:.2f} m.
    """
    story.append(Paragraph("📝 Observations", h2))
    story.append(Paragraph(insights.replace("\n", "<br/>"), body))
    story.append(Spacer(1, 0.35*cm))

    # Tabela
    table_data = [["Species / Class", "Individuals", "Share (%)", "Mean Ø (m)", "Min Ø (m)", "Max Ø (m)"]]
    for _, r in agg.iterrows():
        table_data.append([
            Paragraph(str(r["label"]), body),
            _fmt_int(r["count"]),
            f"{r['percent']:.1f}",
            f"{r['mean_diameter']:.2f}",
            f"{r['min_diameter']:.2f}",
            f"{r['max_diameter']:.2f}",
        ])
    story.append(Paragraph("📊 Summary by class/species", h2))
    tbl = Table(table_data, hAlign="LEFT",
                colWidths=[6*cm, 2.3*cm, 2.2*cm, 2.2*cm, 2.0*cm, 2.0*cm])
    tbl.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.25, colors.lightgrey),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#F0F3F7")),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("ALIGN", (1,1), (-1,-1), "RIGHT"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 0.4*cm))

    # Gráficos
    _matplotlib_defaults()
    pal  = _palette_for(list(agg["label"]))
    cols = [pal[l] for l in agg["label"]]
    if _HAS_SNS: sns.set_theme(style="whitegrid")

    n = len(agg); fig_w = _auto_fig_width(n)

    fig1, ax1 = plt.subplots(figsize=(fig_w, 3.8))
    ax1.bar(agg["label"], agg["count"], color=cols, edgecolor="black", linewidth=0.3)
    _nice_axis(ax1, "Number of individuals per species", "Species", "Count")
    _apply_xtick_styling(ax1, n)
    count_img = _save_fig_to_tmp(fig1, "netflora_count.png")
    story.append(Image(count_img, width=15*cm, height=8.5*cm))
    story.append(Spacer(1, 0.25*cm))

    fig2, ax2 = plt.subplots(figsize=(fig_w, 3.8))
    ax2.bar(agg["label"], agg["mean_diameter"], color=cols, edgecolor="black", linewidth=0.3)
    _nice_axis(ax2, "Mean crown diameter per species", "Species", "Diameter (m)")
    _apply_xtick_styling(ax2, n)
    diam_img = _save_fig_to_tmp(fig2, "netflora_diameter.png")
    story.append(Image(diam_img, width=15*cm, height=8.5*cm))
    story.append(Spacer(1, 0.25*cm))

    if show_hist and df["diameter"].notna().any():
        fig3, ax3 = plt.subplots(figsize=(6.0, 3.6))
        _plot_hist_with_density(ax3, df["diameter"].dropna().values, xlabel="Diameter (m)")
        ax3.set_title("Distribution of crown diameters", fontweight="bold")
        hist_img = _save_fig_to_tmp(fig3, "netflora_diameter_hist.png")
        story.append(Image(hist_img, width=15*cm, height=7.5*cm))
        story.append(Spacer(1, 0.25*cm))

    # Galeria opcional
    if extra_images:
        story.append(PageBreak())
        story.append(Paragraph("Examples of Detection by Algorithms", h2))
        story.append(Spacer(1, 0.2*cm))
        row = []
        for i, item in enumerate(extra_images, 1):
            src = item.get("src"); cap = item.get("caption", ""); wcm = float(item.get("width_cm", 6))
            im = _try_fetch_image(src, desired_width_cm=wcm)
            if im:
                row.append([im, Paragraph(cap, body)])
            if i % 3 == 0 or i == len(extra_images):
                cols_n = len(row)
                img_row = [c[0] for c in row]; cap_row = [c[1] for c in row]
                grid = Table([img_row, cap_row], colWidths=[(17.0/cols_n)*cm]*cols_n)
                grid.setStyle(TableStyle([
                    ("ALIGN", (0,0), (-1,-1), "CENTER"),
                    ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
                    ("BOTTOMPADDING", (0,1), (-1,1), 8),
                ]))
                story.append(grid); story.append(Spacer(1, 0.2*cm))
                row = []

    # Nota final
    story.append(Spacer(1, 0.35*cm))
    story.append(Paragraph(
        "⚠ <b>Important note:</b> Netflora provides automated tree detection using YOLO ONNX models. "
        "However, supervised analysis, visual inspection of the data, and in-field validation "
        "are essential steps for reliable forest monitoring.",
        ParagraphStyle("warn", parent=normal, textColor=colors.red, leading=12)
    ))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        "Developed by <b>Embrapa Acre</b> • Supported by <b>JBS Fund for the Amazon</b>",
        body
    ))

    onpage = _build_onpage_drawer(header_icon_paths, left_cm, right_cm)
    doc.build(story, onFirstPage=onpage, onLaterPages=onpage)
    return output_pdf
