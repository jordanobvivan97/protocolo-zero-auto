"""Publica no Instagram os posts da fila cujo horário já chegou (roda no GitHub Actions).

- API do Instagram com login do Instagram (graph.instagram.com): não exige Página do Facebook.
- O Instagram baixa as imagens pelo jsDelivr, a partir do commit exato que está sendo
  publicado (repositório público, como no Promessa); se o jsDelivr falhar, tenta o
  raw.githubusercontent.com. Segredos ficam só nos Secrets do GitHub.
- Antes de publicar, roda o validador de novo: post com erro não sai.
- Reel só sai quando houver video.mp4 na pasta (você grava, o agente publica).
- Posts de dias anteriores não publicados são ignorados, salvo "recuperar": true.

Uso:
  python scripts/publicar.py            publica (no máximo 1 por execução)
  python scripts/publicar.py --checar   só diz se há algo no horário (sem dependências; sai 0 se houver, 3 se não)
  python scripts/publicar.py --simular  monta tudo e mostra o que faria, sem chamar a API

Variáveis: IG_USER_ID, IG_TOKEN, GITHUB_REPOSITORY e PUB_SHA (ou GITHUB_SHA).
"""
import json
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

RAIZ = Path(__file__).resolve().parent.parent
TZ = ZoneInfo("America/Sao_Paulo")
API = os.environ.get("IG_API_BASE", "https://graph.instagram.com")
MAX_POR_EXECUCAO = 1


def ler(pj):
    return json.loads(pj.read_text(encoding="utf-8"))


def pendentes(agora):
    hoje = agora.date().isoformat()
    lista = []
    for pj in sorted((RAIZ / "fila").glob("*/*/post.json")):
        pasta, post = pj.parent, ler(pj)
        dia = pasta.parent.name
        if dia > hoje or (dia < hoje and not post.get("recuperar")):
            continue
        h, m = map(int, post["horario"].split(":"))
        if dia == hoje and (agora.hour, agora.minute) < (h, m):
            continue
        if post["tipo"] == "reel":
            if not (pasta / "video.mp4").exists():
                print(f"{pasta.relative_to(RAIZ)}: reel aguardando video.mp4", file=sys.stderr)
                continue
        elif not list(pasta.glob("slide-*.jpg")):
            print(f"{pasta.relative_to(RAIZ)}: sem imagens renderizadas, pulando", file=sys.stderr)
            continue
        lista.append(pasta)
    return lista


# ---------- links das mídias (jsDelivr) ----------

class Links:
    def __init__(self, provedor="jsdelivr", simular=False):
        self.provedor = provedor
        self.repo = os.environ.get("GITHUB_REPOSITORY", "jordanobvivan97/protocolo-zero-auto")
        self.sha = os.environ.get("PUB_SHA") or os.environ.get("GITHUB_SHA") or "SIMULADO"
        self.simular = simular

    def link(self, arquivo):
        rel = Path(arquivo).resolve().relative_to(RAIZ).as_posix()
        if self.provedor == "jsdelivr":
            return f"https://cdn.jsdelivr.net/gh/{self.repo}@{self.sha}/{rel}"
        return f"https://raw.githubusercontent.com/{self.repo}/{self.sha}/{rel}"


# ---------- Instagram ----------

class Instagram:
    def __init__(self, simular=False):
        self.simular = simular
        self.ig = os.environ.get("IG_USER_ID", "SIMULADO")
        self.token = os.environ.get("IG_TOKEN", "")
        self.n = 0

    def chamar(self, metodo, caminho, **params):
        if self.simular:
            self.n += 1
            print(f"  [simulado] {metodo} {caminho} {sorted(k for k in params)}")
            if caminho.endswith("media_publish"):
                return {"id": "MIDIA_SIMULADA"}
            if metodo == "GET":
                return {"status_code": "FINISHED", "id": caminho, "permalink": "https://instagram.com/p/SIMULADO"}
            return {"id": f"CONTAINER_{self.n}"}
        import requests
        params["access_token"] = self.token
        r = requests.request(metodo, f"{API}/{caminho}", data=params if metodo == "POST" else None,
                             params=params if metodo == "GET" else None, timeout=90)
        dados = r.json()
        if "error" in dados:
            e = dados["error"]
            raise RuntimeError(f"{caminho}: {e.get('message')} (código {e.get('code')}/{e.get('error_subcode')})")
        return dados

    def esperar(self, cid, limite=600):
        inicio = time.time()
        while time.time() - inicio < limite:
            st = self.chamar("GET", cid, fields="status_code,status")
            if st.get("status_code") == "FINISHED":
                return
            if st.get("status_code") in ("ERROR", "EXPIRED"):
                raise RuntimeError(f"container {cid} falhou: {st}")
            time.sleep(6)
        raise TimeoutError(f"container {cid} não ficou pronto em {limite}s")


def criar_containers(ig, links, pasta, post):
    if post["tipo"] == "reel":
        params = {"media_type": "REELS", "video_url": links.link(pasta / "video.mp4"),
                  "caption": post["legenda"], "share_to_feed": "true"}
        if (pasta / "capa.jpg").exists():
            params["cover_url"] = links.link(pasta / "capa.jpg")
        c = ig.chamar("POST", f"{ig.ig}/media", **params)
        ig.esperar(c["id"], limite=900)
        return c["id"]
    imagens = sorted(pasta.glob("slide-*.jpg"))
    if post["tipo"] == "estatico":
        c = ig.chamar("POST", f"{ig.ig}/media", image_url=links.link(imagens[0]), caption=post["legenda"])
        ig.esperar(c["id"])
        return c["id"]
    filhos = [ig.chamar("POST", f"{ig.ig}/media", image_url=links.link(img), is_carousel_item="true")["id"]
              for img in imagens]
    for f in filhos:
        ig.esperar(f)
    c = ig.chamar("POST", f"{ig.ig}/media", media_type="CAROUSEL", children=",".join(filhos), caption=post["legenda"])
    ig.esperar(c["id"])
    return c["id"]


def publicar(pasta, simular=False):
    sys.path.insert(0, str(RAIZ / "scripts"))
    from validar import validar_post
    erros, _, post = validar_post(pasta)
    if erros:
        raise RuntimeError("validador barrou o post: " + "; ".join(erros))
    ig = Instagram(simular)
    try:
        cid = criar_containers(ig, Links("jsdelivr", simular), pasta, post)
    except RuntimeError as e:
        print(f"jsDelivr falhou ({e}); tentando raw.githubusercontent", file=sys.stderr)
        cid = criar_containers(ig, Links("raw", simular), pasta, post)
    pub = ig.chamar("POST", f"{ig.ig}/media_publish", creation_id=cid)
    info = ig.chamar("GET", pub["id"], fields="id,permalink,timestamp,media_type")
    info["publicado_em_brt"] = datetime.now(TZ).isoformat(timespec="minutes")
    if simular:
        print(f"[simulado] publicaria {post['id']} ({post['tipo']}, {post['formato']}, PROTOCOLO {post['protocolo']})")
        return info
    destino = RAIZ / "publicados" / pasta.parent.name / pasta.name
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(pasta), destino)
    (destino / "publicado.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Publicado {post['id']}: {info.get('permalink')}")
    return info


def main():
    args = set(sys.argv[1:])
    agora = datetime.now(TZ)
    if (RAIZ / "PAUSADO").exists():
        print("Arquivo PAUSADO presente: nada será publicado.")
        sys.exit(3 if "--checar" in args else 0)
    fila = pendentes(agora)
    print(f"{agora:%Y-%m-%d %H:%M} BRT, {len(fila)} post(s) no horário")
    if "--checar" in args:
        sys.exit(0 if fila else 3)
    if "--simular" not in args and not (os.environ.get("IG_TOKEN") and os.environ.get("IG_USER_ID")):
        print("IG_TOKEN ou IG_USER_ID ainda não configurados nos Secrets: nada publicado (ver README).")
        sys.exit(0)
    erros = 0
    for pasta in fila[:MAX_POR_EXECUCAO]:
        try:
            publicar(pasta, simular="--simular" in args)
        except Exception as e:  # noqa: BLE001
            erros += 1
            print(f"ERRO ao publicar {pasta.relative_to(RAIZ)}: {e}", file=sys.stderr)
    sys.exit(1 if erros else 0)


if __name__ == "__main__":
    main()
