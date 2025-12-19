# -*- coding: utf-8 -*-
import os, glob

def _norm(s: str) -> str:
    return s.replace(' ', '_')

def get_model_path(biome: str, category: str, plugin_root: str) -> str:
    """
    Procura o modelo em <plugin_root>/common/weigths/ seguindo esta ordem:
      1) Nome exato: <Biome>_<Categoria>.(onnx|pt)
      2) Qualquer arquivo cujo nome contenha os dois tokens (biome e categoria)
      3) Qualquer .onnx ou .pt encontrado
      4) Se nada existir, retorna o caminho canônico esperado (ajuda o usuário a saber onde salvar)
    """
    base = os.path.join(plugin_root, 'common', 'weigths')
    os.makedirs(base, exist_ok=True)

    # 1) nome exato
    for ext in ('onnx', 'pt'):
        p = os.path.join(base, f"{_norm(biome)}_{_norm(category)}.{ext}")
        if os.path.exists(p):
            return p

    # 2) contém os dois tokens (case-insensitive)
    toks = [_norm(biome).lower(), _norm(category).lower()]
    for ext in ('onnx', 'pt'):
        for p in glob.glob(os.path.join(base, f"*.{ext}")):
            name = os.path.splitext(os.path.basename(p))[0].lower()
            if all(t in name for t in toks):
                return p

    # 3) qualquer modelo
    for ext in ('onnx', 'pt'):
        anyp = glob.glob(os.path.join(base, f"*.{ext}"))
        if anyp:
            return anyp[0]

    # 4) caminho canônico (ainda não existe)
    return os.path.join(base, f"{_norm(biome)}_{_norm(category)}.onnx")
 