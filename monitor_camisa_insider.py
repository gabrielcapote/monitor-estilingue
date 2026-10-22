# ============================================================
# V12.0 — MONITOR BONÉ FLAMENGO LICENCIADO
# Preço máximo: R$ 50,00
# Filtro: Apenas Licenciado/Oficial
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
PRECO_ALVO   = 50.00
PRECO_MIN    = 10.00
PRECO_MAX    = 150.00
REMETENTE    = "gabrielcapote@gmail.com"
DESTINATARIO = "gabrielcapote@gmail.com"

BREVO_API_KEY = os.environ.get("BREVO_API_KEY")

if not BREVO_API_KEY:
    print("ERRO: variável BREVO_API_KEY não encontrada.")
    raise SystemExit(1)

# ============================================================
# LOJAS (Foco em esportivo e oficial)
# ============================================================
LOJAS = {
    # --- Oficiais e Esportivas ---
    "Loja Oficial Flamengo": "loja.flamengo.com.br",
    "Netshoes":              "netshoes.com.br",
    "Centauro":              "centauro.com.br",
    "FutFanatics":           "futfanatics.com.br",
    "Shopee":                "shopee.com.br",
    
    # --- Marketplaces (onde há vendedores oficiais) ---
    "Mercado Livre":         "mercadolivre.com.br",
    "Amazon":                "amazon.com.br",
    "Magazine Luiza":        "magazineluiza.com.br",
    "Americanas":            "americanas.com.br",
    
    # --- Sites de Ofertas (para achar promoções) ---
    "Promobit":              "promobit.com.br",
    "Pelando":               "pelando.com.br",
    "Buscapé":               "buscape.com.br",
    
    # --- Outras lojas de artigos esportivos ---
    "Kanui":                 "kanui.com.br",
    "Dafiti":                "dafiti.com.br",
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

# ============================================================
# FILTRO DE PRODUTO (Apenas Boné Licenciado)
# ============================================================
def produto_ok(texto):
    t = normalizar(texto)
    
    # 1. Tem que ser boné
    eh_bone = any(x in t for x in ["boné", "bone ", "cap ", "gorro"])
    if not eh_bone: return False
    
    # 2. Tem que ser do Flamengo
    eh_flamengo = any(x in t for x in ["flamengo", "mengão", "mengao", "crf"])
    if not eh_flamengo: return False
    
    # 3. Tem que ser LICENCIADO/OFICIAL (Filtro rígido)
    # Busca por termos que indicam licenciamento ou marcas oficiais
    marcas_oficiais = ["new era", "starter", "adidas", "supercap", "nike", "puma", "rebook", "under armour"]
    termos_licenca = ["licenciado", "oficial", "original", " licenciado", " produto oficial"]
    
    tem_marca = any(m in t for m in marcas_oficiais)
    tem_termo = any(termo in t for termo in termos_licenca)
    
    if not (tem_marca or tem_termo):
        return False
        
    return True

def extrair_precos_contexto(texto, dist=250):
    t = texto.lower()
    pos = []
    for p in ["boné", "bone", "flamengo", "mengão"]:
        i = 0
        while True:
            i = t.find(p, i)
            if i == -1: break
            pos.append(i)
            i += len(p)
    if not pos: return []
    precos = []
    for m in re.finditer(r'R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2})', texto, re.I):
        if any(abs(m.start() - p) <= dist for p in pos):
            try:
                v = float(m.group(1).replace(".", "").replace(",", "."))
                if PRECO_MIN <= v <= PRECO_MAX:
                    precos.append(v)
            except: pass
    return sorted(set(precos))

# ============================================================
# BUSCAS
# ============================================================
def buscar_bing(loja, dominio):
    queries = [
        f'site:{dominio} "boné" "flamengo" ("licenciado" OR "oficial" OR "new era" OR "starter" OR "adidas")',
        f'site:{dominio} bone flamengo oficial',
        f'site:{dominio} bone flamengo licenciado',
    ]
    resultados = []
    for q in queries:
        url = "https://www.bing.com/search?q=" + urllib.parse.quote_plus(q) + "&count=20&setlang=pt-BR"
        pagina = baixar(url)
        if not pagina: continue
        blocos = re.findall(r'<li class="b_algo"[^>]>(.?)</li>', pagina, re.S|re.I)
        for b in blocos:
            m = re.search(r'<a[^>]+href="([^"]+)"[^>]>(.?)</a>', b, re.S)
            if not m: continue
            link = limpar_url(m.group(1))
            titulo = html.unescape(limpar_tags(m.group(2))).strip()
            if dominio not in link: continue
            resultados.append({
                "loja": loja, "url": link, "title": titulo,
                "snippet": "", "origem": "bing"
            })
        time.sleep(0.8)
    return resultados

def buscar_google_shopping():
    q = 'boné flamengo oficial licenciado'
    url = "https://www.google.com/search?tbm=shop&q=" + urllib.parse.quote_plus(q) + "&hl=pt-BR&gl=br"
    pagina = baixar(url)
    if not pagina: return []
    resultados = []
    links = re.findall(r'href="(https?://[^"]+)"', pagina)
    for link in links:
        if any(x in link.lower() for x in ["google.", "youtube.", "accounts.", "support."]):
            continue
        if len(link) > 15:
            resultados.append({
                "loja": "Google Shopping", "url": link, "title": "Via Google Shopping",
                "snippet": "", "origem": "google"
            })
    return resultados[:15]

def buscar_direto(loja, dominio):
    termo = "bone+flamengo+oficial"
    mapa = {
        "loja.flamengo.com.br": f"https://www.loja.flamengo.com.br/busca?q={termo}",
        "netshoes.com.br": f"https://www.netshoes.com.br/busca?q={termo}",
        "centauro.com.br": f"https://www.centauro.com.br/busca?q={termo}",
        "futfanatics.com.br": f"https://www.futfanatics.com.br/busca?q={termo}",
        "mercadolivre.com.br": f"https://lista.mercadolivre.com.br/{termo}",
        "amazon.com.br": f"https://www.amazon.com.br/s?k={termo}",
        "magazineluiza.com.br": f"https://www.magazineluiza.com.br/busca/{termo}/",
        "americanas.com.br": f"https://www.americanas.com.br/busca/{termo}",
        "shopee.com.br": f"https://shopee.com.br/search?keyword={termo}",
        "promobit.com.br": f"https://www.promobit.com.br/busca/?q={termo}",
        "pelando.com.br": f"https://www.pelando.com.br/search?q={termo}",
        "buscape.com.br": f"https://www.buscape.com.br/search?q={termo}",
        "kanui.com.br": f"https://www.kanui.com.br/busca?q={termo}",
        "dafiti.com.br": f"https://www.dafiti.com.br/catalog/?q={termo}",
    }
    url = mapa.get(dominio)
    if not url: return []
    pagina = baixar(url)
    if not pagina: return []
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
        
    # Tenta extrair o título real da página para o e-mail
    m_title = re.search(r'<title[^>]>(.?)</title>', pagina, re.S|re.I)
    titulo_real = html.unescape(limpar_tags(m_title.group(1))).strip() if m_title else cand.get("title", "")
    
    return {
        "loja": cand["loja"],
        "url": cand["url"],
        "preco": min(validos),
        "titulo": titulo_real[:90],
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
        "🚨 MONITOR BONÉ FLAMENGO — NOVA OFERTA",
        f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        f"Preço máximo configurado: R$ {PRECO_ALVO:.2f}",
        "Filtro: Apenas Licenciado/Oficial",
        ""
    ]
    for o in ofertas:
        linhas.append(f"🏪 {o['loja']}")
        linhas.append(f"💰 R$ {o['preco']:.2f}")
        linhas.append(f"🧢 {o['titulo']}")
        linhas.append(f"🔗 {o['url']}")
        linhas.append("")
    
    payload = {
        "sender": {"name": "Monitor Boné Flamengo", "email": REMETENTE},
        "to": [{"email": DESTINATARIO}],
        "subject": "🚨 OFERTA: Boné Flamengo Licenciado",
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
    print("Iniciando busca —", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    print("="*70)
    
    candidatos = []
    
    print("→ Google Shopping")
    try: candidatos.extend(buscar_google_shopping())
    except Exception as e: print("  Erro:", e)
    
    for loja, dominio in LOJAS.items():
        print(f"→ {loja}")
        try: candidatos.extend(buscar_bing(loja, dominio))
        except Exception as e: print("  Bing erro:", e)
        try: candidatos.extend(buscar_direto(loja, dominio))
        except Exception as e: print("  Direto erro:", e)
    
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
        except: pass
    print()
    
    ofertas.sort(key=lambda x: x["preco"])
    return ofertas

# ============================================================
# EXECUÇÃO ÚNICA
# ============================================================
if _name_ == "_main_":
    print("Monitor Boné Flamengo V12.0 — execução agendada")
    print(f"Preço máximo: R$ {PRECO_ALVO:.2f}")
    ofertas = pesquisar()
    
    if ofertas:
        print(f"\n{len(ofertas)} oferta(s) encontrada(s)!")
        for o in ofertas:
            print(f"  → {o['loja']} | R$ {o['preco']:.2f} | {o['titulo'][:50]}")
        
        if enviar_email(ofertas):
            print("E-mail enviado com sucesso.")
        else:
            print("Falha no envio do e-mail.")
    else:
        print("\nNenhuma oferta licenciada dentro do preço máximo.")
