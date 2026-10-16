# ============================================================
# V11.5 — MONITOR CAMISA INSIDER (versão para GitHub Actions)
# Preço máximo: R$ 80,00
# ============================================================
import urllib.request
import urllib.parse
import urllib.error
import json
import re
import time
import html
import os
from datetime import datetime

# ============================================================
# CONFIGURAÇÕES
# ============================================================
PRECO_ALVO   = 80.00
PRECO_MIN    = 20.00
PRECO_MAX    = 300.00
REMETENTE    = "gabrielcapote@gmail.com"
DESTINATARIO = "gabrielcapote@gmail.com"

BREVO_API_KEY = os.environ.get("BREVO_API_KEY")

if not BREVO_API_KEY:
    print("ERRO: variável BREVO_API_KEY não encontrada.")
    raise SystemExit(1)

# ============================================================
# LOJAS
# ============================================================
LOJAS = {
    # --- Grandes marketplaces ---
    "Mercado Livre":         "mercadolivre.com.br",
    "Amazon":                "amazon.com.br",
    "Shopee":                "shopee.com.br",
    "Magazine Luiza":        "magazineluiza.com.br",
    "Americanas":            "americanas.com.br",
    "Casas Bahia":           "casasbahia.com.br",
    "Extra":                 "extra.com.br",
    "Carrefour":             "carrefour.com.br",
    "Kabum":                 "kabum.com.br",
    "Ponto Frio":            "pontofrio.com.br",
    "Submarino":             "submarino.com.br",
    "Shoptime":              "shoptime.com.br",
    "Fast Shop":             "fastshop.com.br",
    "MadeiraMadeira":        "madeiramadeira.com.br",
    "Leroy Merlin":          "leroymerlin.com.br",
    "Mobly":                 "mobly.com.br",
    "Camicado":              "camicado.com.br",
    "eBay":                  "ebay.com",
    "AliExpress":            "aliexpress.com",
    "Shopee Global":         "shopee.com",

    # --- Lojas de roupa / esportivas (onde a Insider costuma vender) ---
    "Netshoes":              "netshoes.com.br",
    "Centauro":              "centauro.com.br",
    "Dafiti":                "dafiti.com.br",
    "Zattini":               "zattini.com.br",
    "Renner":                "lojasrenner.com.br",
    "Riachuelo":             "riachuelo.com.br",
    "C&A":                   "cea.com.br",
    "Hering":                "hering.com.br",

    # --- Outras lojas sugeridas ---
    "FNAC Brasil":           "fnac.com.br",
    "Buscapé":               "buscape.com.br",
    "Zoom":                  "zoom.com.br",
    "Jacotei":               "jacotei.com.br",
    "Promobit":              "promobit.com.br",
    "Pelando":               "pelando.com.br",

    # --- Novas lojas adicionadas nesta versão ---
    "Temu":                  "temu.com",
    "Shein":                 "shein.com.br",
    "Wish":                  "wish.com",
    "DHgate":                "dhgate.com",
    "Banggood":              "banggood.com",
    "Gearbest":              "gearbest.com",
    "TomTop":                "tomtop.com",
    "LightInTheBox":         "lightinthebox.com",
    "Mercado Shops":         "mercadolivre.com.br",
    "Via":                   "via.com.br",
    "Shopfy":                "shopfy.com.br",
    "Nuvemshop":             "nuvemshop.com.br",
}

# ============================================================
# HEADERS + DOWNLOAD
# ============================================================
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,/;q=0.8",
}

def baixar(url, timeout=14):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            enc = r.headers.get_content_charset() or "utf-8"
            return r.read().decode(enc, errors="ignore")
    except Exception:
        return ""

# ============================================================
# UTILITÁRIOS
# ============================================================
def normalizar(t):
    t = html.unescape(t or "")
    t = t.lower()
    t = re.sub(r"\s+", " ", t)
    return t.strip()

def limpar_tags(h):
    return re.sub(r"<[^>]+>", " ", h or "")

def limpar_url(url):
    url = html.unescape(url or "")
    m = re.search(r"[?&]uddg=([^&]+)", url)
    if m:
        try:
            return urllib.parse.unquote(m.group(1))
        except:
            pass
    if url.startswith("//"):
        url = "https:" + url
    return url

def eh_pagina_busca(url):
    u = url.lower()
    return any(x in u for x in [
        "/busca", "/search", "/buscar", "/pesquisa", "/sch/",
        "/result", "?q=", "?query=", "?keyword=", "/w/wholesale"
    ])

def produto_ok(texto):
    t = normalizar(texto)
    # O produto é uma camisa da Insider
    camisa = any(x in t for x in ["camisa", "camiseta", "t-shirt", "t shirt"])
    insider = "insider" in t
    # A cor deve ser branca
    branca = "branca" in t or "branco" in t or "white" in t
    return camisa and insider and branca

def tem_metal(texto):
    # Esta função não se aplica mais, mas a mantemos para evitar quebras.
    # Retornamos False para que não interfira na lógica.
    return False

def extrair_precos_contexto(texto, dist=280):
    t = texto.lower()
    pos = []
    # Palavras-chave para o contexto do preço
    for p in ["camisa", "camiseta", "t-shirt", "insider"]:
        i = 0
        while True:
            i = t.find(p, i)
            if i == -1:
                break
            pos.append(i)
            i += len(p)
    if not pos:
        return []
    precos = []
    for m in re.finditer(r'R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2})', texto, re.I):
        if any(abs(m.start() - p) <= dist for p in pos):
            try:
                v = float(m.group(1).replace(".", "").replace(",", "."))
                if PRECO_MIN <= v <= PRECO_MAX:
                    precos.append(v)
            except:
                pass
    return sorted(set(precos))

# ============================================================
# BUSCAS
# ============================================================
def buscar_bing(loja, dominio):
    queries = [
        f'site:{dominio} "camisa insider" ("branca" OR "branco" OR "white")',
        f'site:{dominio} "camiseta insider" ("branca" OR "branco" OR "white")',
        f'site:{dominio} "camisa insider" M',
    ]
    resultados = []
    for q in queries:
        url = "https://www.bing.com/search?q=" + urllib.parse.quote_plus(q) + "&count=20&setlang=pt-BR"
        pagina = baixar(url)
        if not pagina:
            continue
        blocos = re.findall(r'<li class="b_algo"[^>]>(.?)</li>', pagina, re.S|re.I)
        for b in blocos:
            m = re.search(r'<a[^>]+href="([^"]+)"[^>]>(.?)</a>', b, re.S)
            if not m:
                continue
            link = limpar_url(m.group(1))
            titulo = html.unescape(limpar_tags(m.group(2))).strip()
            if dominio not in link:
                continue
            resultados.append({
                "loja": loja, "url": link, "title": titulo,
                "snippet": "", "origem": "bing"
            })
        time.sleep(0.8)
    return resultados

def buscar_google_shopping():
    q = 'camisa insider branca'
    url = "https://www.google.com/search?tbm=shop&q=" + urllib.parse.quote_plus(q) + "&hl=pt-BR&gl=br"
    pagina = baixar(url)
    if not pagina:
        return []
    resultados = []
    links = re.findall(r'href="(https?://[^"]+)"', pagina)
    for link in links:
        if any(x in link.lower() for x in ["google.", "youtube.", "accounts.", "support."]):
            continue
        if len(link) > 15:
            resultados.append({
                "loja": "Google Shopping",
                "url": link,
                "title": "Via Google Shopping",
                "snippet": "",
                "origem": "google"
            })
    return resultados[:15]

def buscar_direto(loja, dominio):
    termo = "camisa+insider+branca+M"
    mapa = {
        "mercadolivre.com.br": f"https://lista.mercadolivre.com.br/{termo}",
        "amazon.com.br": f"https://www.amazon.com.br/s?k={termo}",
        "shopee.com.br": f"https://shopee.com.br/search?keyword={termo}",
        "magazineluiza.com.br": f"https://www.magazineluiza.com.br/busca/{termo}/",
        "americanas.com.br": f"https://www.americanas.com.br/busca/{termo}",
        "casasbahia.com.br": f"https://www.casasbahia.com.br/busca?query={termo}",
        "extra.com.br": f"https://www.extra.com.br/busca?query={termo}",
        "carrefour.com.br": f"https://www.carrefour.com.br/busca/{termo}",
        "kabum.com.br": f"https://www.kabum.com.br/busca/{termo}",
        "pontofrio.com.br": f"https://www.pontofrio.com.br/busca?q={termo}",
        "submarino.com.br": f"https://www.submarino.com.br/busca?q={termo}",
        "shoptime.com.br": f"https://www.shoptime.com.br/busca?q={termo}",
        "madeiramadeira.com.br": f"https://www.madeiramadeira.com.br/busca?q={termo}",
        "leroymerlin.com.br": f"https://www.leroymerlin.com.br/search?q={termo}",
        "ebay.com": f"https://www.ebay.com/sch/i.html?_nkw={termo}",
        "aliexpress.com": f"https://pt.aliexpress.com/w/wholesale-{termo}.html",
        # --- Lojas de roupa ---
        "netshoes.com.br": f"https://www.netshoes.com.br/busca?q={termo}",
        "centauro.com.br": f"https://www.centauro.com.br/busca?q={termo}",
        "dafiti.com.br": f"https://www.dafiti.com.br/catalog/?q={termo}",
        "zattini.com.br": f"https://www.zattini.com.br/busca?q={termo}",
        "lojasrenner.com.br": f"https://www.lojasrenner.com.br/busca?q={termo}",
        "riachuelo.com.br": f"https://www.riachuelo.com.br/busca?q={termo}",
        "cea.com.br": f"https://www.cea.com.br/busca?q={termo}",
        "hering.com.br": f"https://www.hering.com.br/busca?q={termo}",
        # --- Sites de comparação ---
        "buscape.com.br": f"https://www.buscape.com.br/search?q={termo}",
        "zoom.com.br": f"https://www.zoom.com.br/search?q={termo}",
        "jacotei.com.br": f"https://www.jacotei.com.br/busca?q={termo}",
        "promobit.com.br": f"https://www.promobit.com.br/busca/?q={termo}",
        "pelando.com.br": f"https://www.pelando.com.br/search?q={termo}",
        # --- Novas lojas internacionais ---
        "temu.com": f"https://www.temu.com/search_result.html?search_key={termo}",
        "shein.com.br": f"https://br.shein.com/pdsearch/{termo}/",
        "wish.com": f"https://www.wish.com/search/{termo}",
        "dhgate.com": f"https://www.dhgate.com/wholesale/search.do?searchkey={termo}",
        "banggood.com": f"https://www.banggood.com/search/{termo}.html",
        "gearbest.com": f"https://www.gearbest.com/search?q={termo}",
        "tomtop.com": f"https://www.tomtop.com/search?q={termo}",
        "lightinthebox.com": f"https://www.lightinthebox.com/search?q={termo}",
    }
    url = mapa.get(dominio)
    if not url:
        return []
    pagina = baixar(url)
    if not pagina:
        return []
    return [{
        "loja": loja, "url": url, "title": f"Busca {loja}",
        "snippet": "", "origem": "direto"
    }]

# ============================================================
# ANÁLISE
# ============================================================
def analisar(cand):
    if eh_pagina_busca(cand["url"]):
        return None
    pagina = baixar(cand["url"], timeout=12)
    texto = cand.get("title", "") + "\n" + limpar_tags(pagina)
    if not produto_ok(texto):
        return None
    precos = extrair_precos_contexto(texto)
    validos = [p for p in precos if p <= PRECO_ALVO]
    if not validos:
        return None
    return {
        "loja": cand["loja"],
        "url": cand["url"],
        "preco": min(validos),
        "metal": tem_metal(texto), # Mantido para compatibilidade, mas sempre False
        "titulo": cand.get("title", "")[:90],
        "origem": cand.get("origem", "")
    }

def remover_duplicados(lista):
    vistos = set()
    final = []
    for item in lista:
        u = item["url"].split("#")[0].split("?")[0]
        if u not in vistos:
            vistos.add(u)
            final.append(item)
    return final

# ============================================================
# E-MAIL
# ============================================================
def enviar_email(ofertas):
    linhas = [
        "🚨 MONITOR CAMISA INSIDER V11.5 — NOVA OFERTA",
        f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        f"Preço máximo configurado: R$ {PRECO_ALVO:.2f}",
        ""
    ]
    for o in ofertas:
        linhas.append(f"🏪 {o['loja']}")
        linhas.append(f"💰 R$ {o['preco']:.2f}")
        linhas.append("👕 Cor: Branca confirmada" if "branca" in normalizar(o['titulo']) else "👕 Cor: Branca não confirmada")
        linhas.append(f"🔗 {o['url']}")
        linhas.append("")
    
    payload = {
        "sender": {"name": "Monitor Camisa Insider", "email": REMETENTE},
        "to": [{"email": DESTINATARIO}],
        "subject": "🚨 OFERTA CAMISA INSIDER BRANCA",
        "textContent": "\n".join(linhas)
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=data,
        headers={
            "accept": "application/json",
            "api-key": BREVO_API_KEY,
            "content-type": "application/json"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status in (200, 201, 202)
    except Exception as e:
        print("Erro ao enviar e-mail:", e)
        return False

# ============================================================
# PESQUISA PRINCIPAL
# ============================================================
def pesquisar():
    print("\n" + "="*70)
    print("Iniciando busca ampla —", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    print("="*70)
    
    candidatos = []
    
    print("→ Google Shopping")
    try:
        candidatos.extend(buscar_google_shopping())
    except Exception as e:
        print("  Erro:", e)
    
    for loja, dominio in LOJAS.items():
        print(f"→ {loja}")
        try:
            candidatos.extend(buscar_bing(loja, dominio))
        except Exception as e:
            print("  Bing erro:", e)
        try:
            candidatos.extend(buscar_direto(loja, dominio))
        except Exception as e:
            print("  Direto erro:", e)
    
    candidatos = remover_duplicados(candidatos)
    print(f"\nTotal de candidatos únicos: {len(candidatos)}")
    
    ofertas = []
    for i, c in enumerate(candidatos, 1):
        print(f"\rAnalisando {i}/{len(candidatos)}", end="")
        try:
            of = analisar(c)
            if of:
                chave = (of["url"], round(of["preco"], 2))
                if not any((x["url"], round(x["preco"], 2)) == chave for x in ofertas):
                    ofertas.append(of)
        except:
            pass
    print()
    
    ofertas.sort(key=lambda x: x["preco"])
    return ofertas

# ============================================================
# EXECUÇÃO ÚNICA
# ============================================================
if _name_ == "_main_":
    print("Monitor Camisa Insider V11.5 — execução agendada")
    print(f"Preço máximo: R$ {PRECO_ALVO:.2f}")
    ofertas = pesquisar()
    
    if ofertas:
        print(f"\n{len(ofertas)} oferta(s) encontrada(s)!")
        for o in ofertas:
            print(f"  → {o['loja']} | R$ {o['preco']:.2f}")
        
        if enviar_email(ofertas):
            print("E-mail enviado com sucesso.")
        else:
            print("Falha no envio do e-mail.")
    else:
        print("\nNenhuma oferta dentro do preço máximo.")
