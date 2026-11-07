"""Renderiza os slides de um post (identidade de dossiê do Protocolo Zero).

Uso: python scripts/render.py fila/2026-11-09/01 [fila/2026-11-09/02 ...]

Gera slide-01.jpg, slide-02.jpg ... (1080x1350) dentro da pasta do post.
Texto entre **asteriscos duplos** sai em laranja de sinalização (só em títulos e textos).
O carimbo "PROTOCOLO 00X", o rodapé, a numeração das lâminas, o rótulo de cenário
hipotético, o fecho fixo e a frase da Defesa Civil são colocados aqui, não no post.json,
para nunca faltarem.
"""
import json
import math
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

RAIZ = Path(__file__).resolve().parent.parent
FONTES = RAIZ / "assets" / "fonts"
W, H = 1080, 1350
M = 72  # margem externa

GRAFITE = (22, 24, 26)
GRAFITE_2 = (36, 39, 42)
LINHA = (58, 62, 66)
LARANJA = (255, 106, 19)
LARANJA_PAPEL = (196, 70, 0)  # no papel claro o laranja escurece para manter contraste de leitura
PAPEL = (237, 231, 218)
PAPEL_SOMBRA = (205, 197, 180)
TINTA = (28, 29, 31)
TINTA_SUAVE = (92, 90, 84)
OFF = (232, 228, 219)
CINZA = (150, 152, 150)

MARCA = json.loads((RAIZ / "marca.json").read_text(encoding="utf-8"))


def fonte(nome, tam):
    return ImageFont.truetype(str(FONTES / nome), tam)


TITULO = "Oswald-Bold.ttf"
TITULO_2 = "Oswald-SemiBold.ttf"
CORPO = "PlexSans-Regular.ttf"
CORPO_B = "PlexSans-SemiBold.ttf"
MONO = "PlexMono-Regular.ttf"
MONO_B = "PlexMono-SemiBold.ttf"
MAQUINA = "SpecialElite.ttf"


# ---------- texto ----------

def tokens(texto):
    """Divide em palavras guardando o destaque **...** e as quebras de linha."""
    out, laranja = [], False
    for par_i, par in enumerate(texto.split("\n")):
        if par_i:
            out.append(("\n", False))
        for bruto in par.split(" "):
            if not bruto:
                continue
            palavra, inicio, fim = bruto, False, False
            if palavra.startswith("**"):
                palavra, inicio = palavra[2:], True
            if palavra.endswith("**") or palavra.rstrip(".,:;!?)").endswith("**"):
                palavra, fim = palavra.replace("**", ""), True
            palavra = palavra.replace("**", "")
            if inicio:
                laranja = True
            out.append((palavra, laranja))
            if fim:
                laranja = False
    return out


def quebrar(draw, texto, f, largura):
    linhas, atual = [], []
    for palavra, cor in tokens(texto):
        if palavra == "\n":
            linhas.append(atual)
            atual = []
            continue
        teste = " ".join(p for p, _ in atual + [(palavra, cor)])
        if atual and draw.textlength(teste, font=f) > largura:
            linhas.append(atual)
            atual = [(palavra, cor)]
        else:
            atual.append((palavra, cor))
    linhas.append(atual)
    return linhas


def caber(draw, texto, nome_fonte, largura, altura, tam_max, tam_min, entrelinha=1.18):
    tam = tam_max
    while tam >= tam_min:
        f = fonte(nome_fonte, tam)
        linhas = quebrar(draw, texto, f, largura)
        alt = len(linhas) * tam * entrelinha
        if alt <= altura and all(draw.textlength(" ".join(p for p, _ in l), font=f) <= largura for l in linhas):
            return f, linhas, tam
        tam -= 2
    raise ValueError(f"texto não cabe nem em {tam_min}px: {texto[:60]}...")


def escrever(draw, xy, linhas, f, tam, cor, entrelinha=1.18, cor_destaque=LARANJA):
    x, y = xy
    for linha in linhas:
        cx = x
        for i, (palavra, laranja) in enumerate(linha):
            txt = palavra + (" " if i < len(linha) - 1 else "")
            draw.text((cx, y), txt, font=f, fill=cor_destaque if laranja else cor)
            cx += draw.textlength(txt, font=f)
        y += tam * entrelinha
    return y


def bloco(draw, xy, texto, nome_fonte, largura, altura, tam_max, tam_min, cor, entrelinha=1.18, destaque=None):
    f, linhas, tam = caber(draw, texto, nome_fonte, largura, altura, tam_max, tam_min, entrelinha)
    if destaque is None:
        destaque = LARANJA_PAPEL if cor == TINTA else LARANJA
    return escrever(draw, xy, linhas, f, tam, cor, entrelinha, cor_destaque=destaque), tam


def altura_bloco(draw, texto, nome_fonte, largura, altura, tam_max, tam_min, entrelinha=1.18):
    _, linhas, tam = caber(draw, texto, nome_fonte, largura, altura, tam_max, tam_min, entrelinha)
    return len(linhas) * tam * entrelinha


# ---------- elementos de identidade ----------

def fundo_grafite(seed):
    img = Image.new("RGB", (W, H), GRAFITE)
    d = ImageDraw.Draw(img)
    for x in range(0, W, 54):  # grade de mapa, bem discreta
        d.line([(x, 0), (x, H)], fill=(30, 32, 35), width=1)
    for y in range(0, H, 54):
        d.line([(0, y), (W, y)], fill=(30, 32, 35), width=1)
    rnd = random.Random(seed)
    ruido = Image.effect_noise((W, H), 18).convert("L")
    img = Image.composite(img, Image.new("RGB", (W, H), (16, 17, 19)), ruido.point(lambda v: 255 if v > 40 else 225))
    d = ImageDraw.Draw(img)
    # curvas de nível no canto, lembrando mapa topográfico
    cx, cy = W + rnd.randint(-40, 40), rnd.randint(120, 260)
    for r in range(140, 620, 46):
        d.ellipse([cx - r * 1.3, cy - r, cx + r * 1.3, cy + r], outline=(40, 43, 46), width=2)
    return img


def papel(img, caixa, seed):
    """Ficha de papel off-white com sombra e furos de arquivo."""
    x0, y0, x1, y1 = caixa
    sombra = Image.new("L", (W, H), 0)
    ImageDraw.Draw(sombra).rectangle([x0 + 10, y0 + 14, x1 + 10, y1 + 14], fill=150)
    sombra = sombra.filter(ImageFilter.GaussianBlur(14))
    img.paste((8, 8, 9), (0, 0), sombra)
    folha = Image.new("RGB", (x1 - x0, y1 - y0), PAPEL)
    ruido = Image.effect_noise(folha.size, 10).convert("L")
    folha = Image.composite(folha, Image.new("RGB", folha.size, PAPEL_SOMBRA), ruido.point(lambda v: 255 if v > 30 else 236))
    img.paste(folha, (x0, y0))
    d = ImageDraw.Draw(img)
    d.rectangle([x0, y0, x1, y1], outline=(196, 188, 170), width=2)
    for fy in (y0 + 120, y1 - 120):  # furos de pasta
        d.ellipse([x0 + 22, fy - 11, x0 + 44, fy + 11], fill=GRAFITE)
    return d


def carimbo(img, texto, centro, tam=58, angulo=-7, cor=LARANJA, seed=0):
    f = fonte(TITULO, tam)
    tmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    tw = tmp.textlength(texto, font=f)
    pad_x, pad_y = int(tam * 0.55), int(tam * 0.32)
    cw, ch = int(tw + 2 * pad_x), int(tam * 1.25 + 2 * pad_y)
    camada = Image.new("RGBA", (cw + 20, ch + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(camada)
    d.rectangle([10, 10, cw + 10, ch + 10], outline=cor + (255,), width=6)
    d.rectangle([20, 20, cw, ch], outline=cor + (255,), width=2)
    d.text((10 + pad_x, 10 + pad_y - tam * 0.12), texto, font=f, fill=cor + (255,))
    # desgaste de tinta
    rnd = random.Random(seed)
    alpha = camada.split()[3]
    furos = Image.new("L", camada.size, 255)
    fd = ImageDraw.Draw(furos)
    for _ in range(int(cw * ch / 900)):
        x, y = rnd.randint(0, cw + 20), rnd.randint(0, ch + 20)
        r = rnd.randint(1, 4)
        fd.ellipse([x - r, y - r, x + r, y + r], fill=rnd.randint(0, 120))
    camada.putalpha(Image.composite(alpha, Image.new("L", camada.size, 0), furos))
    camada = camada.rotate(angulo, expand=True, resample=Image.BICUBIC)
    img.paste(camada, (int(centro[0] - camada.width / 2), int(centro[1] - camada.height / 2)), camada)
    return camada.width, camada.height


def rotulo_hipotetico(img):
    d = ImageDraw.Draw(img)
    f = fonte(MONO_B, 26)
    txt = "CENÁRIO HIPOTÉTICO"
    tw = d.textlength(txt, font=f)
    x1 = W - M
    d.rectangle([x1 - tw - 36, 40, x1, 86], fill=LARANJA)
    d.text((x1 - tw - 18, 49), txt, font=f, fill=GRAFITE)


def rodape(img, i, n, claro=True):
    d = ImageDraw.Draw(img)
    f = fonte(MONO, 22)
    cor = CINZA if claro else TINTA_SUAVE
    d.line([(M, H - 82), (W - M, H - 82)], fill=LINHA if claro else PAPEL_SOMBRA, width=2)
    d.text((M, H - 66), MARCA["rodape"], font=f, fill=cor)
    num = f"{i:02d}/{n:02d}"
    d.text((W - M - d.textlength(num, font=f), H - 66), num, font=f, fill=cor)


def cabecalho_ficha(d, x0, y0, x1, esquerda, direita):
    f = fonte(MONO_B, 24)
    d.text((x0 + 80, y0 + 40), esquerda.upper(), font=f, fill=TINTA_SUAVE)
    if direita:
        d.text((x1 - 48 - d.textlength(direita.upper(), font=f), y0 + 40), direita.upper(), font=f, fill=LARANJA)
    d.line([(x0 + 80, y0 + 84), (x1 - 48, y0 + 84)], fill=TINTA, width=3)


def caixa_marcada(d, x, y, lado, marcada, seed):
    d.rectangle([x, y, x + lado, y + lado], outline=TINTA, width=4)
    if marcada:
        rnd = random.Random(seed)
        pts = [(x + lado * 0.15, y + lado * 0.55), (x + lado * 0.42, y + lado * 0.85), (x + lado * 1.05, y - lado * 0.15)]
        pts = [(px + rnd.uniform(-2, 2), py + rnd.uniform(-2, 2)) for px, py in pts]
        d.line(pts, fill=LARANJA, width=9, joint="curve")


# ---------- layouts ----------

def l_capa(s, post, i, n):
    img = fundo_grafite(i)
    d = ImageDraw.Draw(img)
    f = fonte(MONO_B, 24)
    meta = s.get("etiqueta") or {"protocolo": "PROTOCOLO Nº", "cenario": "CENÁRIO E SE", "alerta": "ALERTA EXPLICADO",
                                 "calculadora": "CALCULADORA", "saude": "SAÚDE EM EMERGÊNCIA"}[post["formato"]]
    d.text((M, 108), f"ARQUIVO PZ  ·  {meta.upper()}", font=f, fill=CINZA)
    cw, ch = carimbo(img, f"PROTOCOLO {post['protocolo']}", (M + 230, 260), tam=60, angulo=-6, seed=hash(post["id"]) % 999)
    topo = 260 + ch / 2 + 50
    area = H - 120 - topo - 60
    tit_alt_max = area * (0.68 if s.get("subtitulo") else 0.95)
    alt_t = altura_bloco(d, s["titulo"].upper(), TITULO, W - 2 * M, tit_alt_max, 124, 54, 1.08)
    alt_s = 0
    if s.get("subtitulo"):
        alt_s = 70 + altura_bloco(d, s["subtitulo"], CORPO, W - 2 * M - 40, area - alt_t - 70, 46, 28, 1.18)
    y = topo + max(0, (area - alt_t - alt_s) * 0.42)
    fim, _ = bloco(d, (M, y), s["titulo"].upper(), TITULO, W - 2 * M, tit_alt_max, 124, 54, OFF, 1.08)
    if s.get("subtitulo"):
        d.rectangle([M, fim + 34, M + 90, fim + 42], fill=LARANJA)
        bloco(d, (M, fim + 70), s["subtitulo"], CORPO, W - 2 * M - 40, area - alt_t - 70, 46, 28, OFF)
    if post.get("hipotetico"):
        rotulo_hipotetico(img)
    rodape(img, i, n)
    return img


def area_papel():
    return (M - 12, 128, W - M + 12, H - 118)


def l_ficha(s, post, i, n):
    img = fundo_grafite(i)
    x0, y0, x1, y1 = area_papel()
    d = papel(img, (x0, y0, x1, y1), i)
    cabecalho_ficha(d, x0, y0, x1, s.get("etiqueta", f"Protocolo {post['protocolo']}"), s.get("contador", ""))
    tx, larg = x0 + 80, x1 - x0 - 128
    y = y0 + 120
    y, _ = bloco(d, (tx, y), s["titulo"].upper(), TITULO, larg, 230, 76, 44, TINTA, 1.06)
    y += 64
    itens = s.get("itens", [])
    nota_alt = 0
    if s.get("nota"):
        nota_alt = altura_bloco(d, s["nota"], MONO, larg, 210, 28, 21, 1.3) + 50
    disp = y1 - 60 - y - nota_alt
    lado = 40
    tam = 42
    while tam >= 26:  # mesmo tamanho para todos os itens
        f = fonte(CORPO, tam)
        alts = [len(quebrar(d, it, f, larg - lado - 34)) * tam * 1.22 for it in itens]
        if sum(alts) + 26 * (len(itens) - 1) <= disp:
            break
        tam -= 2
    else:
        raise ValueError(f"itens não cabem na ficha '{s['titulo']}'")
    f = fonte(CORPO, tam)
    marcados = s.get("marcados", [])
    for k, it in enumerate(itens):
        caixa_marcada(d, tx, y + tam * 0.18, lado, k in marcados, k + i)
        linhas = quebrar(d, it, f, larg - lado - 34)
        y = escrever(d, (tx + lado + 34, y), linhas, f, tam, TINTA, 1.22, cor_destaque=LARANJA_PAPEL) + 26
    if s.get("nota"):
        ny = y1 - 60 - nota_alt + 40
        d.line([(tx, ny - 22), (tx + 60, ny - 22)], fill=LARANJA, width=5)
        bloco(d, (tx, ny), s["nota"], MONO, larg, 210, 28, 21, TINTA_SUAVE, 1.3)
    if post.get("hipotetico"):
        rotulo_hipotetico(img)
    rodape(img, i, n)
    return img


def l_texto(s, post, i, n):
    img = fundo_grafite(i)
    x0, y0, x1, y1 = area_papel()
    d = papel(img, (x0, y0, x1, y1), i)
    cabecalho_ficha(d, x0, y0, x1, s.get("etiqueta", f"Protocolo {post['protocolo']}"), s.get("contador", ""))
    tx, larg = x0 + 80, x1 - x0 - 128
    y = y0 + 120
    if s.get("titulo"):
        y, _ = bloco(d, (tx, y), s["titulo"].upper(), TITULO, larg, 260, 76, 44, TINTA, 1.06)
        y += 76
    bloco(d, (tx, y), s["texto"], CORPO, larg, y1 - 70 - y, 50, 28, TINTA, 1.32)
    if post.get("hipotetico"):
        rotulo_hipotetico(img)
    rodape(img, i, n)
    return img


def l_tabela(s, post, i, n):
    img = fundo_grafite(i)
    x0, y0, x1, y1 = area_papel()
    d = papel(img, (x0, y0, x1, y1), i)
    cabecalho_ficha(d, x0, y0, x1, s.get("etiqueta", f"Protocolo {post['protocolo']}"), s.get("contador", ""))
    tx, larg = x0 + 80, x1 - x0 - 128
    y = y0 + 120
    y, _ = bloco(d, (tx, y), s["titulo"].upper(), TITULO, larg, 200, 66, 40, TINTA, 1.06)
    y += 30
    cols, linhas = s["colunas"], s["linhas"]
    nc = len(cols)
    pesos = s.get("larguras") or [1] * nc
    ws = [larg * p / sum(pesos) for p in pesos]
    nota_alt = altura_bloco(d, s["nota"], MONO, larg, 200, 26, 20, 1.3) + 40 if s.get("nota") else 0
    disp = y1 - 60 - y - nota_alt
    fh = fonte(MONO_B, 24)
    cab_alts = [len(quebrar(d, c, fh, wc - 24)) for c, wc in zip(cols, ws)]
    cab_h = max(cab_alts) * 30 + 28
    lh = min(108, (disp - cab_h) / max(1, len(linhas)))
    tam = int(min(52, lh * 0.5))
    fc = fonte(TITULO_2, tam)
    d.rectangle([tx, y, tx + larg, y + cab_h], fill=TINTA)
    cx = tx
    for c, w in zip(cols, ws):
        ly = y + 14
        for ln in quebrar(d, c, fh, w - 24):
            d.text((cx + 12, ly), " ".join(p for p, _ in ln).upper(), font=fh, fill=PAPEL)
            ly += 30
        cx += w
    y += cab_h
    for r, linha in enumerate(linhas):
        if r % 2:
            d.rectangle([tx, y, tx + larg, y + lh], fill=(226, 219, 203))
        cx = tx
        for k, (val, w) in enumerate(zip(linha, ws)):
            destaque = k in s.get("colunas_destaque", [])
            d.text((cx + 12, y + (lh - tam * 1.25) / 2), str(val), font=fc, fill=LARANJA_PAPEL if destaque else TINTA)
            cx += w
        y += lh
        d.line([(tx, y), (tx + larg, y)], fill=PAPEL_SOMBRA, width=2)
    if s.get("nota"):
        bloco(d, (tx, y1 - 60 - nota_alt + 30), s["nota"], MONO, larg, 200, 26, 20, TINTA_SUAVE, 1.3)
    rodape(img, i, n)
    return img


def l_frase(s, post, i, n):
    img = fundo_grafite(i)
    d = ImageDraw.Draw(img)
    cw, ch = carimbo(img, f"PROTOCOLO {post['protocolo']}", (M + 230, 230), tam=52, angulo=-6, seed=i)
    y = 230 + ch / 2 + 60
    fim, _ = bloco(d, (M, y), s["texto"], TITULO_2, W - 2 * M, H - 360 - y, 92, 44, OFF, 1.12)
    if s.get("assinatura"):
        bloco(d, (M, fim + 40), s["assinatura"], MONO, W - 2 * M, 120, 30, 22, CINZA, 1.3)
    d.text((M, H - 200), MARCA["frase_defesa_civil"], font=fonte(MONO, 24), fill=CINZA)
    if post.get("hipotetico"):
        rotulo_hipotetico(img)
    rodape(img, i, n)
    return img


def l_fechamento(s, post, i, n):
    img = fundo_grafite(i)
    d = ImageDraw.Draw(img)
    f = fonte(MONO_B, 24)
    d.text((M, 108), "ARQUIVO PZ  ·  ENCERRAMENTO", font=f, fill=CINZA)
    y = 220
    if s.get("titulo"):
        y, _ = bloco(d, (M, y), s["titulo"], CORPO_B, W - 2 * M, 260, 50, 32, OFF, 1.2)
        y += 40
    if s.get("texto"):
        y, _ = bloco(d, (M, y), s["texto"], CORPO, W - 2 * M, 220, 40, 28, OFF, 1.3)
        y += 40
    # CTA único em caixa laranja
    cta = s["cta"]
    fcta, linhas, tam = caber(d, cta, CORPO_B, W - 2 * M - 80, 200, 44, 28, 1.2)
    alt = len(linhas) * tam * 1.2 + 64
    d.rectangle([M, y, W - M, y + alt], fill=LARANJA)
    escrever(d, (M + 40, y + 32), linhas, fcta, tam, GRAFITE, 1.2, cor_destaque=GRAFITE)
    y += alt + 70
    carimbo(img, "ARQUIVADO", (W - M - 190, max(y + 70, H - 470)), tam=56, angulo=-9, seed=i + 7)
    fy = H - 360
    bloco(d, (M, fy), MARCA["fecho_fixo"], TITULO_2, W - 2 * M, 150, 58, 40, OFF, 1.12)
    d.text((M, H - 170), MARCA["frase_defesa_civil"], font=fonte(MONO, 25), fill=CINZA)
    if post.get("hipotetico"):
        rotulo_hipotetico(img)
    rodape(img, i, n)
    return img


LAYOUTS = {"capa": l_capa, "ficha": l_ficha, "texto": l_texto, "tabela": l_tabela,
           "frase": l_frase, "fechamento": l_fechamento}


def render(pasta):
    pasta = Path(pasta)
    post = json.loads((pasta / "post.json").read_text(encoding="utf-8"))
    if post["tipo"] == "reel":
        print(f"{pasta}: reel, sem slides para renderizar (só a capa, se houver)")
        slides = post.get("slides", [])[:1]
    else:
        slides = post["slides"]
    for velho in pasta.glob("slide-*.jpg"):
        velho.unlink()
    n = len(slides)
    for i, s in enumerate(slides, 1):
        img = LAYOUTS[s["layout"]](s, post, i, n)
        nome = "capa.jpg" if post["tipo"] == "reel" else f"slide-{i:02d}.jpg"
        img.convert("RGB").save(pasta / nome, quality=92, optimize=True)
    print(f"{pasta}: {n} imagem(ns)")


if __name__ == "__main__":
    for alvo in sys.argv[1:]:
        render(alvo)
