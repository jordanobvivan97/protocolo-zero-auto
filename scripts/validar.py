"""Valida posts antes de renderizar e publicar. Sai com código 1 se houver erro.

Uso: python scripts/validar.py fila/2026-11-09            (todos os posts do dia)
     python scripts/validar.py fila/2026-11-09/01         (um post)
     python scripts/validar.py fila                       (tudo que está na fila)

O que este script garante (regras da Fundação):
- Todo número que aparece nos slides e na legenda está coberto por uma fonte oficial,
  por uma conta derivada que o próprio script refaz, por telefone oficial de emergência
  ou por um "numero_proprio" justificado (contagem interna do post, como "3 decisões").
- Fonte de número é de domínio oficial (fontes_permitidas.json). Matéria de imprensa só
  entra como "imprensa_citando_oficial", com pendência, e aí o post exige aprovação por PR.
- Legenda cita as fontes e traz a frase da Defesa Civil.
- Nada de medo vendido, governo escondendo, armas, saque, compra por pânico.
- Saúde: sem dose, sem diagnóstico, sem se apresentar como médico.
- Cenário de ficção marcado como hipotético.
- Portão de originalidade respondido, formato diferente do post anterior, gancho diferente
  dos dois anteriores, pauta sem repetir em 30 dias, número de protocolo único.

Limite conhecido: números escritos por extenso ("três litros") não são conferidos aqui.
Por isso a regra de escrita é usar algarismos para toda quantidade (ver GERAR.md).
"""
import ast
import json
import math
import re
import sys
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlparse

RAIZ = Path(__file__).resolve().parent.parent
MARCA = json.loads((RAIZ / "marca.json").read_text(encoding="utf-8"))
FONTES_OK = json.loads((RAIZ / "fontes_permitidas.json").read_text(encoding="utf-8"))

FORMATOS = {"protocolo", "cenario", "alerta", "calculadora", "saude"}
TIPOS = {"carrossel", "estatico", "reel"}
LAYOUTS = {"capa", "ficha", "texto", "tabela", "frase", "fechamento"}
CONFERENCIAS = {"pagina_oficial", "perfil_oficial", "imprensa_citando_oficial"}
PORTAO = ["ideia_nova", "formato_diferente_do_ultimo", "gancho_diferente_dos_2_ultimos", "concreto_ate_lamina_2",
          "especifico_do_tema", "numeros_com_fonte", "sem_ficcao_como_fato", "assinaria_com_meu_nome"]
CAMPOS = ["id", "pauta_id", "formato", "tipo", "horario", "protocolo", "gancho_tipo", "slides", "legenda", "fontes", "portao"]

PROIBIDOS = {
    r"[—–]": "travessão",
    r"\bfim do mundo\b": "vender medo",
    r"\bo fim est[áa] pr[óo]ximo\b": "vender medo",
    r"\bapocal[ií]p": "vender medo",
    r"\bcolapso total\b": "vender medo",
    r"\bningu[ée]m vai te salvar\b": "vender medo",
    r"\bgoverno (est[áa] )?escond": "governo escondendo",
    r"\best[ãa]o escondendo\b": "governo escondendo",
    r"\bn[ãa]o querem que voc[êe] saiba\b": "governo escondendo",
    r"\barmas?\b": "armas (fora do escopo)",
    r"\bmuni[çc][ãa]o\b": "armas (fora do escopo)",
    r"\bdefesa armada\b": "armas (fora do escopo)",
    r"\bsaque(ar|s)?\b": "saque (fora do escopo)",
    r"\bcompre (j[áa]|agora)\b": "compra por pânico",
    r"\bantes que acabe\b": "compra por pânico",
    r"\bcorra (para|pro) (o )?mercado\b": "compra por pânico",
}
SAUDE_PROIBIDOS = {
    r"\b\d+[.,]?\d*\s?(mg|mcg|µg|ml|mL|gotas?|comprimidos?|c[áa]psulas?|ui)\b": "dose de medicamento",
    r"\b(tome|tomar|administre|administrar|dê|dar) \d": "dose de medicamento",
    r"\bsou (m[ée]dic|estudante de medicina)": "se apresentar como médico",
    r"\bcomo m[ée]dic": "se apresentar como médico",
    r"\bvoc[êe] (tem|est[áa] com) (leptospirose|hipotermia|infec)": "diagnóstico",
}


def todos_textos(p, com_legenda=True):
    out = [p.get("legenda", "")] if com_legenda else []
    for s in p.get("slides", []):
        for k in ("titulo", "subtitulo", "texto", "etiqueta", "contador", "assinatura", "nota", "cta"):
            if s.get(k):
                out.append(s[k])
        out += s.get("itens", [])
        out += [" ".join(c) for c in s.get("linhas", [])]
        out += s.get("colunas", [])
    return out


def sem_secao_fontes(legenda):
    """Tira o parágrafo 'Fontes:' (datas e anos de publicação não são afirmações)."""
    pars = legenda.split("\n\n")
    return "\n\n".join(x for x in pars if not x.strip().lower().startswith("fontes"))


def numeros_do_texto(texto):
    texto = re.sub(r"#\w+", " ", texto)
    texto = re.sub(r"\bprotocolo\s+0\d\d\b", " ", texto, flags=re.I)
    texto = re.sub(r"\b\d{1,2}/\d{1,2}(/\d{2,4})?\b", " ", texto)  # datas
    texto = re.sub(r"\b\d{1,2}h\d{0,2}\b(?!\s*horas)", lambda m: m.group(0) if m.group(0).endswith("h") else " ", texto)
    achados = re.findall(r"(?<![\w])(\d+(?:[.,]\d+)?)", texto)
    return {a.replace(".", ",") for a in achados}


def avaliar_conta(expr):
    """Calcula contas simples (+ - * / ceil round) sem eval livre."""
    arvore = ast.parse(expr, mode="eval")

    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value
        if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            a, b = ev(n.left), ev(n.right)
            return {ast.Add: a + b, ast.Sub: a - b, ast.Mult: a * b, ast.Div: a / b if b else math.nan}[type(n.op)]
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in ("ceil", "round", "floor"):
            return {"ceil": math.ceil, "round": round, "floor": math.floor}[n.func.id](*[ev(a) for a in n.args])
        raise ValueError(f"conta não permitida: {expr}")
    return ev(arvore)


def dominio_ok(url, conferencia):
    u = urlparse(url)
    host = (u.hostname or "").lower().removeprefix("www.")
    if conferencia == "perfil_oficial":
        handle = u.path.strip("/").split("/")[0].lower()
        return handle in [h.lower() for h in FONTES_OK["perfis_oficiais"].get(host, [])]
    doms = FONTES_OK["dominios_oficiais_br"] + FONTES_OK["dominios_internacionais"]
    return any(host == d or host.endswith("." + d) for d in doms)


def todos_os_posts():
    lista = []
    for base in ("publicados", "fila"):
        for pj in (RAIZ / base).glob("*/*/post.json"):
            try:
                p = json.loads(pj.read_text(encoding="utf-8"))
                lista.append((pj.parent.parent.name, p.get("horario", "00:00"), pj.parent.resolve(), p))
            except (json.JSONDecodeError, OSError):
                continue
    return sorted(lista, key=lambda x: (x[0], x[1], str(x[2])))


def validar_post(pasta):
    erros, avisos = [], []
    pasta = Path(pasta).resolve()
    p = json.loads((pasta / "post.json").read_text(encoding="utf-8"))
    for c in CAMPOS:
        if c not in p:
            erros.append(f"falta o campo '{c}'")
    if erros:
        return erros, avisos, p

    # estrutura
    if p["formato"] not in FORMATOS:
        erros.append(f"formato inválido: {p['formato']}")
    if p["tipo"] not in TIPOS:
        erros.append(f"tipo inválido: {p['tipo']}")
    if not re.fullmatch(r"\d{2}:\d{2}", p["horario"]):
        erros.append("horario deve ser HH:MM")
    if not re.fullmatch(r"\d{3}", str(p["protocolo"])):
        erros.append("protocolo deve ter 3 dígitos, como '007'")
    slides = p["slides"]
    for s in slides:
        if s.get("layout") not in LAYOUTS:
            erros.append(f"layout inválido: {s.get('layout')}")
    if p["tipo"] == "carrossel":
        if not 3 <= len(slides) <= 10:
            erros.append("carrossel precisa de 3 a 10 lâminas (limite da API: 10)")
        if slides and slides[0].get("layout") != "capa":
            erros.append("carrossel precisa abrir com a capa (carimbo PROTOCOLO)")
        if slides and (slides[-1].get("layout") != "fechamento" or not slides[-1].get("cta")):
            erros.append("carrossel precisa terminar no fechamento com um CTA único")
    if p["tipo"] == "estatico" and (len(slides) != 1 or slides[0].get("layout") != "frase"):
        erros.append("estático é exatamente 1 lâmina 'frase'")
    if p["tipo"] == "reel":
        rot = pasta / p.get("roteiro_reel", "roteiro.md")
        if not rot.exists():
            erros.append("reel sem roteiro.md na pasta")
        else:
            r = rot.read_text(encoding="utf-8")
            if MARCA["fecho_fixo"] not in r:
                erros.append("roteiro do reel sem o fecho fixo")
            if not re.search(r"PROTOCOLO \d{3}", r):
                erros.append("roteiro do reel sem o carimbo PROTOCOLO 00X")
    elif p.get("roteiro_reel") and not (pasta / p["roteiro_reel"]).exists():
        avisos.append(f"roteiro_reel indicado ({p['roteiro_reel']}) mas o arquivo não está na pasta")
    if p["formato"] == "cenario" and not p.get("hipotetico"):
        erros.append("cenário 'E se...?' precisa de \"hipotetico\": true (rótulo na tela)")

    textos = todos_textos(p)
    junto = "\n".join(textos)
    baixo = junto.lower()

    # proibidos
    for rx, motivo in PROIBIDOS.items():
        if re.search(rx, junto if rx.startswith("[") else baixo):
            erros.append(f"proibido pela Fundação ({motivo}): /{rx}/")
    for rx, motivo in SAUDE_PROIBIDOS.items():
        if re.search(rx, junto, flags=re.I):
            erros.append(f"saúde ({motivo}): /{rx}/")
    if p["formato"] == "saude" and "educativo" not in p["legenda"].lower():
        erros.append("post de saúde precisa dizer na legenda que o conteúdo é educativo e não substitui atendimento")
    if re.search(r"\b(imagine|e se)\b", baixo) and not p.get("hipotetico") and p["formato"] != "alerta":
        avisos.append("texto com 'imagine' ou 'e se': se for cenário de ficção, marque hipotetico")

    # legenda
    leg = p["legenda"]
    if MARCA["frase_defesa_civil"] not in leg:
        erros.append(f"legenda sem a frase padrão: \"{MARCA['frase_defesa_civil']}\"")
    if "fontes:" not in leg.lower() and "fonte:" not in leg.lower():
        erros.append("legenda sem a seção 'Fontes:'")
    if len(leg) > 2200:
        erros.append("legenda acima de 2200 caracteres")
    if len(re.findall(r"#\w+", leg)) > MARCA["hashtags_max"]:
        erros.append(f"mais de {MARCA['hashtags_max']} hashtags")
    if "link na bio" in baixo and not MARCA.get("link_bio_ativo"):
        erros.append("CTA de link na bio, mas link_bio_ativo é false")
    if re.search(rf"\bcomente\s+{MARCA['isca_palavra'].lower()}\b", baixo) and not MARCA.get("isca_ativa"):
        erros.append("CTA da isca (comente KIT) com isca_ativa false: a automação de DM ainda não existe")
    if p.get("afiliado") and not re.search(r"#publi|afiliad|publicidade", leg.lower()):
        erros.append("post com afiliado sem sinalizar na legenda (#publi ou 'link de afiliado')")

    # fontes e números
    cobertos, exige_pr = set(), False
    for f in p["fontes"]:
        for c in ("orgao", "url", "conferencia", "afirmacao", "numeros", "consultado_em"):
            if c not in f:
                erros.append(f"fonte sem '{c}': {f.get('orgao', f.get('url', '?'))}")
        conf = f.get("conferencia")
        if conf not in CONFERENCIAS:
            erros.append(f"conferencia inválida em {f.get('orgao')}: {conf}")
        elif conf == "imprensa_citando_oficial":
            exige_pr = True
            if not f.get("pendencia"):
                erros.append(f"fonte de imprensa sem 'pendencia' explicando o que falta conferir: {f.get('orgao')}")
        elif not dominio_ok(f.get("url", ""), conf):
            erros.append(f"URL não é de órgão oficial permitido: {f.get('url')} (ver fontes_permitidas.json)")
        nome = re.split(r"[,(]", f.get("orgao", ""))[0].strip()
        if nome and nome.lower() not in leg.lower():
            erros.append(f"fonte '{nome}' não aparece citada na legenda")
        try:
            if (date.today() - date.fromisoformat(f.get("consultado_em", "1900-01-01"))).days > 30:
                avisos.append(f"fonte consultada há mais de 30 dias, reconfira: {f.get('orgao')}")
        except ValueError:
            erros.append(f"consultado_em inválido em {f.get('orgao')}")
        cobertos |= {str(n).replace(".", ",") for n in f.get("numeros", [])}
    for d in p.get("derivados", []):
        try:
            v = avaliar_conta(d["conta"])
            alvo = float(str(d["valor"]).replace(",", "."))
            if not math.isclose(v, alvo, rel_tol=0.02, abs_tol=0.05):
                erros.append(f"conta errada: {d['conta']} = {v:g}, não {d['valor']}")
            else:
                cobertos.add(str(d["valor"]).replace(".", ","))
        except (ValueError, SyntaxError, KeyError) as e:
            erros.append(f"derivado inválido {d}: {e}")
    for n, just in p.get("numeros_proprios", {}).items():
        if not just or len(just) < 10:
            erros.append(f"numero_proprio '{n}' sem justificativa")
        else:
            cobertos.add(str(n).replace(".", ","))
            avisos.append(f"número sem fonte por ser contagem interna: {n} ({just})")
    cobertos |= set(FONTES_OK["numeros_livres"]["telefones"])
    texto_numeros = "\n".join(todos_textos(p, com_legenda=False) + [sem_secao_fontes(leg)])
    soltos = sorted(numeros_do_texto(texto_numeros) - cobertos, key=lambda x: float(x.replace(",", ".")))
    for n in soltos:
        erros.append(f"número sem fonte, conta ou justificativa: {n}")
    if MARCA["modo_aprovacao"] == "direto" and p["formato"] in MARCA.get("pr_sempre", []):
        avisos.append(f"EXIGE PR: formato {p['formato']} está em pr_sempre")
    if exige_pr:
        avisos.append("EXIGE PR: há fonte de imprensa aguardando conferência no órgão oficial")
        if MARCA["modo_aprovacao"] == "direto" and not p.get("pendencia_resolvida_por"):
            erros.append("modo direto não publica post com fonte pendente; resolva a pendência ou mande por PR")

    # portão de originalidade
    port = p["portao"]
    faltando = [k for k in PORTAO if port.get(k) is not True]
    if faltando:
        erros.append(f"portão de originalidade sem 'sim' em: {', '.join(faltando)}")

    # histórico: formato, gancho, pauta, protocolo
    hist = todos_os_posts()
    antes = [x for x in hist if x[2] != pasta and (x[0], x[1]) < (pasta.parent.name, p["horario"])]
    if antes and antes[-1][3].get("formato") == p["formato"]:
        erros.append(f"formato igual ao do post anterior ({p['formato']}): a Fundação pede rotação")
    ganchos = [x[3].get("gancho_tipo") for x in antes[-2:]]
    if p["gancho_tipo"] in ganchos:
        erros.append(f"tipo de gancho '{p['gancho_tipo']}' repetido nos 2 últimos posts")
    limite = date.today() - timedelta(days=30)
    for d, _, pz, q in hist:
        if pz == pasta:
            continue
        try:
            recente = date.fromisoformat(d) >= limite
        except ValueError:
            recente = False
        if recente and q.get("pauta_id") == p["pauta_id"]:
            erros.append(f"pauta {p['pauta_id']} já usada em {d}")
        if q.get("protocolo") == p["protocolo"]:
            erros.append(f"número de protocolo {p['protocolo']} já usado em {d}")
    return erros, avisos, p


def main(alvos):
    falhou = False
    pastas = []
    for a in alvos:
        a = Path(a)
        if (a / "post.json").exists():
            pastas.append(a)
        else:
            pastas += sorted(x.parent for x in a.glob("**/post.json"))
    for pasta in pastas:
        erros, avisos, _ = validar_post(pasta)
        print(f"[{'ERRO' if erros else 'ok'}] {pasta}")
        for e in erros:
            print("   x", e)
        for w in avisos:
            print("   !", w)
        falhou |= bool(erros)
    if not pastas:
        print("nenhum post encontrado")
    sys.exit(1 if falhou else 0)


if __name__ == "__main__":
    main(sys.argv[1:] or ["fila"])
