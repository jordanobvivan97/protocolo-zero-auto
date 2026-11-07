"""Teste só de leitura: confere token, conta, permissões, limite de publicação e se o jsDelivr serve os arquivos do repositório.

Não publica nada. Grava o resultado (sem segredos) em metricas/teste-conexao.json.
"""
import json
import os
from datetime import datetime
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
API = os.environ.get("IG_API_BASE", "https://graph.facebook.com/v24.0")
TOKEN = os.environ.get("IG_TOKEN", "")
IG = os.environ.get("IG_USER_ID", "").strip()


def get(caminho, **params):
    params["access_token"] = TOKEN
    try:
        r = requests.get(f"{API}/{caminho}", params=params, timeout=60).json()
    except Exception as e:  # noqa: BLE001
        return {"erro": str(e)}
    if "error" in r:
        e = r["error"]
        return {"erro": e.get("message"), "codigo": e.get("code"), "subcodigo": e.get("error_subcode")}
    return r


res = {"em": datetime.now().isoformat(timespec="seconds")}
res["eu"] = get("me", fields="id,name")
res["permissoes"] = get("me/permissions")
if IG:
    res["conta"] = get(IG, fields="username,followers_count,media_count")
    res["limite_publicacao"] = get(f"{IG}/content_publishing_limit", fields="config,quota_usage")
else:
    res["conta"] = {"erro": "IG_USER_ID vazio"}

PAGE = os.environ.get("FB_PAGE_ID", "").strip()
if PAGE:
    res["pagina"] = get(PAGE, fields="id,name,instagram_business_account")
    if "erro" not in res["pagina"]:
        res["pagina_token_ok"] = "access_token" in get(PAGE, fields="access_token")
        iba = (res["pagina"].get("instagram_business_account") or {}).get("id")
        res["instagram_ligado_a_pagina_confere"] = (iba == IG) if iba else "Página sem Instagram ligado"
else:
    res["pagina"] = {"erro": "FB_PAGE_ID vazio"}

repo = os.environ.get("GITHUB_REPOSITORY", "")
sha = os.environ.get("GITHUB_SHA", "")
if repo and sha:
    url = f"https://cdn.jsdelivr.net/gh/{repo}@{sha}/marca.json"
    try:
        res["jsdelivr_responde"] = requests.get(url, timeout=60).status_code == 200
    except Exception as e:  # noqa: BLE001
        res["jsdelivr_responde"] = f"erro: {e}"

(RAIZ / "metricas").mkdir(exist_ok=True)
(RAIZ / "metricas" / "teste-conexao.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(res, ensure_ascii=False, indent=2))
