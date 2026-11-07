"""Teste só de leitura: confere token, conta, permissões, limite de publicação e se o jsDelivr serve os arquivos do repositório.

Não publica nada. Grava o resultado (sem segredos) em metricas/teste-conexao.json.
"""
import json
import os
from datetime import datetime
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
API = os.environ.get("IG_API_BASE", "https://graph.instagram.com")
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
res["eu"] = get("me", fields="user_id,username,account_type")
if IG:
    res["conta"] = get(IG, fields="username,followers_count,media_count")
    res["limite_publicacao"] = get(f"{IG}/content_publishing_limit", fields="config,quota_usage")
    if "user_id" in res["eu"]:
        res["ig_user_id_confere"] = str(res["eu"]["user_id"]) == IG
else:
    res["conta"] = {"erro": "IG_USER_ID vazio"}

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
