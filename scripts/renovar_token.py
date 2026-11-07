"""Renova o token do Instagram (vale 60 dias) e imprime o novo para o workflow gravar no Secret.

O token de longa duração do login do Instagram pode ser renovado depois de 24 horas de vida,
enquanto ainda for válido. O workflow roda nos dias 1 e 15 de cada mês, com folga de sobra.
Nunca imprime o token no log: escreve num arquivo temporário que o workflow lê e apaga.
"""
import json
import os
import sys

import requests

API = os.environ.get("IG_API_BASE", "https://graph.instagram.com")
r = requests.get(f"{API}/refresh_access_token",
                 params={"grant_type": "ig_refresh_token", "access_token": os.environ["IG_TOKEN"]}, timeout=60).json()
if "access_token" not in r:
    print(f"Falhou ao renovar: {json.dumps(r.get('error', r), ensure_ascii=False)}", file=sys.stderr)
    sys.exit(1)
with open(os.environ.get("SAIDA", "novo_token.txt"), "w", encoding="utf-8") as f:
    f.write(r["access_token"])
dias = int(r.get("expires_in", 0)) // 86400
print(f"Token renovado; vale por mais {dias} dias.")
