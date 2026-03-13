# -*- coding: utf-8 -*-
import hashlib
import json
import os
import shutil
from typing import Optional

from qgis.PyQt.QtCore import QEventLoop, QFileInfo, QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest
from qgis.PyQt.QtWidgets import QApplication, QFileDialog, QMessageBox
from qgis.core import QgsApplication, QgsNetworkAccessManager


REGISTRY_FILE = "model_registry.json"


def _log(feedback, message: str):
    try:
        feedback.pushInfo(message)
    except Exception:
        pass


def _plugin_models_dir(plugin_root: str) -> str:
    return os.path.join(plugin_root, "common", "weights")


def _user_models_dir() -> str:
    base = os.path.join(QgsApplication.qgisSettingsDirPath(), "netflora", "models")
    os.makedirs(base, exist_ok=True)
    return base


def _registry_path(plugin_root: str) -> str:
    return os.path.join(plugin_root, "common", REGISTRY_FILE)


def _load_registry(plugin_root: str) -> dict:
    path = _registry_path(plugin_root)
    if not os.path.exists(path):
        return {}

    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _candidate_paths(plugin_root: str, model_filename: str, alg_key: str):
    user_dir = _user_models_dir()
    plugin_dir = _plugin_models_dir(plugin_root)
    base_name, ext = os.path.splitext(model_filename)
    ext = ext.lower()

    candidates = [
        os.path.join(user_dir, model_filename),
        os.path.join(user_dir, f"{alg_key}.onnx"),
        os.path.join(user_dir, f"{alg_key}.pt"),
        os.path.join(plugin_dir, model_filename),
        os.path.join(plugin_dir, f"{alg_key}.onnx"),
        os.path.join(plugin_dir, f"{alg_key}.pt"),
    ]

    if ext not in (".onnx", ".pt"):
        candidates.extend(
            [
                os.path.join(user_dir, f"{base_name}.onnx"),
                os.path.join(user_dir, f"{base_name}.pt"),
                os.path.join(plugin_dir, f"{base_name}.onnx"),
                os.path.join(plugin_dir, f"{base_name}.pt"),
            ]
        )

    seen = set()
    ordered = []
    for path in candidates:
        norm = os.path.normcase(os.path.normpath(path))
        if norm in seen:
            continue
        seen.add(norm)
        ordered.append(path)
    return ordered


def _first_existing_path(paths):
    for path in paths:
        if os.path.exists(path):
            return path
    return None


def _http_get(url: str, headers: Optional[dict] = None):
    request = QNetworkRequest(QUrl(url))
    request.setAttribute(QNetworkRequest.FollowRedirectsAttribute, True)
    request.setRawHeader(b"User-Agent", b"Netflora-QGIS-Plugin")
    if headers:
        for key, value in headers.items():
            request.setRawHeader(key.encode("utf-8"), value.encode("utf-8"))

    manager = QgsNetworkAccessManager.instance()
    reply = manager.get(request)
    loop = QEventLoop()
    reply.finished.connect(loop.quit)
    loop.exec()

    status_code = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
    error = reply.error()
    payload = bytes(reply.readAll())
    error_message = reply.errorString()
    reply.deleteLater()
    if error:
        if status_code:
            raise RuntimeError(f"HTTP {int(status_code)}: {error_message}")
        raise RuntimeError(error_message)
    return payload


def _show_under_construction_message(alg_key: str, asset_name: str):
    if QApplication.instance() is None:
        return

    parent = QApplication.activeWindow()
    QMessageBox.information(
        parent,
        "Netflora - Algorithm under construction / Algoritmo em construcao",
        (
            f"The model for '{alg_key}' is not available yet.\n"
            f"Expected release asset: {asset_name}\n\n"
            "This algorithm is still under construction. "
            "Please try again after the model is published.\n\n"
            f"O modelo para '{alg_key}' ainda nao esta disponivel.\n"
            f"Asset esperado no release: {asset_name}\n\n"
            "Este algoritmo ainda esta em construcao. "
            "Tente novamente depois que o modelo for publicado."
        ),
    )


def _resolve_github_release_url(repo: str, release_tag: str, asset_name: str) -> str:
    if not repo:
        raise RuntimeError("GitHub repository is not configured for this model.")

    if not asset_name:
        raise RuntimeError("Asset name is not configured for this model.")

    if not release_tag or release_tag == "latest":
        api_url = f"https://api.github.com/repos/{repo}/releases/latest"
    else:
        api_url = f"https://api.github.com/repos/{repo}/releases/tags/{release_tag}"

    payload = _http_get(
        api_url,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    data = json.loads(payload.decode("utf-8"))
    for asset in data.get("assets", []):
        if asset.get("name") == asset_name:
            url = asset.get("browser_download_url")
            if url:
                return url

    release_name = data.get("tag_name") or release_tag or "latest"
    raise RuntimeError(
        f"Asset '{asset_name}' was not found in GitHub release '{release_name}'."
    )


def _verify_sha256(file_path: str, expected_hash: str):
    if not expected_hash:
        return

    digest = hashlib.sha256()
    with open(file_path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    actual_hash = digest.hexdigest().lower()
    if actual_hash != expected_hash.lower():
        raise RuntimeError(
            f"SHA256 mismatch for '{os.path.basename(file_path)}'. "
            f"Expected {expected_hash.lower()}, got {actual_hash}."
        )


def _prompt_for_missing_model(asset_name: str, target_dir: str):
    if QApplication.instance() is None:
        raise RuntimeError(
            f"Model '{asset_name}' is missing and no GUI is available to ask for download confirmation."
        )

    parent = QApplication.activeWindow()
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Warning)
    box.setWindowTitle("Netflora - Model weight required")
    box.setText(f"The model '{asset_name}' is not installed.")
    box.setInformativeText(
        "Netflora can download it from the configured release assets "
        f"and store it in:\n{target_dir}"
    )
    download_button = box.addButton("Download", QMessageBox.AcceptRole)
    local_button = box.addButton("Use local file", QMessageBox.ActionRole)
    cancel_button = box.addButton(QMessageBox.Cancel)
    box.setDefaultButton(download_button)
    box.exec()

    clicked = box.clickedButton()
    if clicked == download_button:
        return "download"
    if clicked == local_button:
        return "local"
    if clicked == cancel_button:
        return "cancel"
    return "cancel"


def _copy_local_model(asset_name: str, target_dir: str):
    parent = QApplication.activeWindow()
    selected, _ = QFileDialog.getOpenFileName(
        parent,
        "Select model weight",
        "",
        "Model weights (*.onnx *.pt)",
    )
    if not selected:
        return None

    suffix = QFileInfo(selected).suffix() or QFileInfo(asset_name).suffix() or "onnx"
    cached_path = os.path.join(target_dir, f"{os.path.splitext(asset_name)[0]}.{suffix}")
    shutil.copy2(selected, cached_path)
    return cached_path


def _download_model(entry: dict, asset_name: str, target_path: str, feedback):
    download_url = entry.get("url")
    if not download_url:
        download_url = _resolve_github_release_url(
            repo=entry.get("github_repo"),
            release_tag=entry.get("release_tag", "latest"),
            asset_name=asset_name,
        )

    _log(feedback, f"[Netflora] Downloading model: {download_url}")
    try:
        payload = _http_get(download_url)
    except Exception as exc:
        message = str(exc)
        if "HTTP 404" in message:
            raise FileNotFoundError(message)
        raise

    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    temp_path = f"{target_path}.part"
    with open(temp_path, "wb") as handle:
        handle.write(payload)

    try:
        _verify_sha256(temp_path, entry.get("sha256", ""))
        os.replace(temp_path, target_path)
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise

    return target_path


def ensure_model_path(alg_key: str, plugin_root: str, feedback=None) -> str:
    registry = _load_registry(plugin_root)
    defaults = registry.get("defaults", {})
    models = registry.get("models", {})
    entry = dict(defaults)
    entry.update(models.get(alg_key, {}))

    asset_name = entry.get("asset_name") or f"{alg_key}.onnx"
    target_dir = _user_models_dir()
    target_path = os.path.join(target_dir, asset_name)

    existing_path = _first_existing_path(_candidate_paths(plugin_root, asset_name, alg_key))
    if existing_path:
        return existing_path

    action = _prompt_for_missing_model(asset_name, target_dir)
    if action == "local":
        local_path = _copy_local_model(asset_name, target_dir)
        if local_path:
            _verify_sha256(local_path, entry.get("sha256", ""))
            return local_path
        raise RuntimeError("Model selection cancelled by the user.")

    if action != "download":
        raise RuntimeError("Model download cancelled by the user.")

    if not entry.get("url") and not entry.get("github_repo"):
        raise RuntimeError(
            f"No remote source is configured for '{alg_key}'. "
            f"Update '{_registry_path(plugin_root)}' or choose a local file."
        )

    try:
        return _download_model(entry, asset_name, target_path, feedback)
    except FileNotFoundError:
        _show_under_construction_message(alg_key, asset_name)
        raise RuntimeError(
            f"The algorithm '{alg_key}' is still under construction because the asset "
            f"'{asset_name}' has not been published in the release yet. "
            f"O algoritmo '{alg_key}' ainda esta em construcao porque o asset "
            f"'{asset_name}' ainda nao foi publicado no release."
        )
