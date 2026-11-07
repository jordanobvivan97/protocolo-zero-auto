"""Coleta métricas dos posts publicados e da conta (roda no GitHub Actions, uma vez por dia).

Grava:
- metricas/posts.csv: uma linha por post (alcance, visualizações, salvamentos, envios, curtidas,
  comentários, e a taxa (salvamentos + envios) / alcance, que é a métrica de salvamento da Fundação)
- metricas/conta.csv: seguidores e número de posts por dia (para seguidores por post)
- metricas/resumo.json: mediana por formato, com o tamanho da amostra

Não mexe em volume: a cadência vem do calendário da Fundação. O veredito por formato só vale
com cerca de 15 posts do formato (regra da Fundação); abaixo disso o resumo marca "amostra pequena".
Retenção de Reels aos 3s não sai pela API: essa leitura continua nos prints, no diagnóstico.
"""
import csv
import json
import os
import statistics
from datetime import date, datetime
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
API = os.environ.get("IG_API_BASE", "https://graph.facebook.com/v24.0")
TOKEN = os.environ["IG_TOKEN"]
METRICAS = ["reach", "views", "saved", "shares", "likes", "comments"]


def get(caminho, **params):
    params["access_token"] = TOKEN
    return requests.get(f"{API}/{caminho}", params=params, timeout=60).json()


def insights(media_id):
    r = get(f"{media_id}/insights", metric=",".join(METRICAS))
    if "error" in r:  # alguma métrica não disponível para o tipo de mídia: tenta sem views
        r = get(f"{media_id}/insights", metric=",".join(m for m in METRICAS if m != "views"))
    if "error" in r:
        return {"erro": r["error"].get("message", "")}
    return {i["name"]: i["values"][0]["value"] for i in r.get("data", [])}


def coletar_posts():
    linhas = []
    for pj in sorted((RAIZ / "publicados").glob("*/*/publicado.json")):
        pub = json.loads(pj.read_text(encoding="utf-8"))
        post = json.loads((pj.parent / "post.json").read_text(encoding="utf-8"))
        d = insights(pub["id"])
        alcance = d.get("reach") or 0
        taxa = round((d.get("saved", 0) + d.get("shares", 0)) / alcance, 4) if alcance else ""
        linhas.append({"data": pj.parent.parent.name, "id": post["id"], "pauta_id": post["pauta_id"],
                       "formato": post["formato"], "tipo": post["tipo"], "gancho_tipo": post["gancho_tipo"],
                       "protocolo": post["protocolo"], "horario": post["horario"],
                       "permalink": pub.get("permalink", ""), **{m: d.get(m, "") for m in METRICAS},
                       "salv_env_por_alcance": taxa, "erro": d.get("erro", "")})
    with open(RAIZ / "metricas" / "posts.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()) if linhas else ["data"])
        w.writeheader()
        w.writerows(linhas)
    return linhas


def coletar_conta():
    ig = os.environ.get("IG_USER_ID", "me")
    r = get(ig, fields="followers_count,media_count")
    arq = RAIZ / "metricas" / "conta.csv"
    novo = not arq.exists()
    with open(arq, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if novo:
            w.writerow(["data", "seguidores", "posts", "erro"])
        w.writerow([date.today().isoformat(), r.get("followers_count", ""), r.get("media_count", ""),
                    r.get("error", {}).get("message", "") if "error" in r else ""])


def resumir(linhas):
    por_formato = {}
    for l in linhas:
        por_formato.setdefault(l["formato"], []).append(l)
    resumo = {"atualizado_em": datetime.now().isoformat(timespec="minutes"), "formatos": {}}
    for fmt, ls in por_formato.items():
        alc = [int(l["reach"]) for l in ls if str(l["reach"]).isdigit()]
        tx = [float(l["salv_env_por_alcance"]) for l in ls if l["salv_env_por_alcance"] != ""]
        resumo["formatos"][fmt] = {
            "posts": len(ls),
            "mediana_alcance": statistics.median(alc) if alc else None,
            "mediana_salv_env_por_alcance": round(statistics.median(tx), 4) if tx else None,
            "amostra": "suficiente" if len(ls) >= 15 else f"pequena ({len(ls)} de 15)",
        }
    (RAIZ / "metricas" / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(resumo, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    (RAIZ / "metricas").mkdir(exist_ok=True)
    coletar_conta()
    resumir(coletar_posts())
