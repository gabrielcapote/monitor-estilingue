# ============================================================
# MONITOR ALBUMINA 1KG (NATUROVOS, EGGPRO E GROWTH)
# ============================================================
import html
import json
import os
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

# ============================================================
# CONFIGURAÇÕES GERAIS
# ============================================================
PRECO_MIN = 20.00
PRECO_ALVO = 70.00  # O teto geral (Growth). O código filtra os outros abaixo.

REMETENTE = "gabrielcapote@gmail.com"
DESTINATARIO = "gabrielcapote@gmail.com"

BREVO_API_KEY = os.environ.get("BREVO_API_KEY")
if not BREVO_API_KEY:
    print("ERRO: variável BREVO_API_KEY não encontrada.")
    raise SystemExit(1)

# ============================================================
# LOJAS E SITES
# ============================================================
LOJAS = {
    "Mercado Livre": "mercadolivre.com.br",
    "Amazon": "amazon.com.br",
    "Magazine Luiza": "magazineluiza.com.br",
    "Americanas": "americanas.com.br",
    "Buscapé": "buscape.com.br",
    "Zoom": "zoom.com.br",
    "Promobit": "promobit.com.br",
    "Pelando": "pelando.com.br",
    "Drogasil": "drogasil.com.br",
    "Ponto": "ponto.com.br",
    "Extra": "extra.com.br",
    "Casas Bahia": "casasbahia.com.br",
}

# ============================================================
# HEADERS E DOWNLOAD
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
        with urllib.request.urlopen(req, timeout=timeout) as resposta:
            codificacao = resposta.headers.get_content_charset() or "utf-8"
            return resposta.read().decode(codificacao, errors="ignore")
    except Exception:
        return ""

# ============================================================
# UTILITÁRIOS
# ============================================================
def normalizar(texto):
    texto = html.unescape(texto or "")
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.lower()
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()

def limpar_tags(html_texto):
    html_texto = html_texto or ""
    html_texto = re.sub(r"<script\b[^>]>.?</script>", " ", html_texto, flags=re.I | re.S)
    html_texto = re.sub(r"<style\b[^>]>.?</style>", " ", html_texto, flags=re.I | re.S)
    html_texto = re.sub(r"<[^>]+>", " ", html_texto)
    return html.unescape(html_texto)

def limpar_url(url):
    url = html.unescape(url or "").strip()
    match = re.search(r"[?&]uddg=([^&]+)", url, flags=re.I)
    if match:
        try:
            url = urllib.parse.unquote(match.group(1))
        except Exception:
            pass
    if url.startswith("//"):
        url = "https:" + url
    return url

def pertence_ao_dominio(url, dominio):
    try:
        hostname = urllib.parse.urlparse(url).hostname or ""
        hostname = hostname.lower()
        return hostname == dominio or hostname.endswith("." + dominio)
    except Exception:
        return False

def eh_pagina_busca(url):
    url_normalizada = normalizar(url)
    termos = [
        "/busca", "/search", "/buscar", "/pesquisa", "/result",
        "?q=", "?query=", "?keyword=", "/sch/", "/catalog/", "/lista/",
    ]
    return any(termo in url_normalizada for termo in termos)

def extrair_titulo(pagina, fallback="Albumina 1kg"):
    match = re.search(r"<title[^>]>(.?)</title>", pagina or "", flags=re.I | re.S)
    if not match:
        return fallback[:120]
    titulo = limpar_tags(match.group(1))
    titulo = re.sub(r"\s+", " ", titulo).strip()
    return titulo[:120] or fallback[:120]

# ============================================================
# FILTRO DE PRODUTO (A MÁGICA ACONTECE AQUI)
# ============================================================
def produto_ok(texto):
    texto_normalizado = normalizar(texto)

    # 1. Tem que ser albumina
    if not re.search(r"\balbumina\b", texto_normalizado):
        return False

    # 2. Tem que ter 1kg (ou 1000g)
    if not re.search(r"\b(?:1\s*kg|1000\s*g)\b", texto_normalizado):
        return False

    # 3. Tem que ser de uma das 3 marcas permitidas
    eh_naturovos = bool(re.search(r"\bnaturovos\b", texto_normalizado))
    eh_eggpro = bool(re.search(r"\begg\s*pro\b", texto_normalizado))
    eh_growth = bool(re.search(r"\bgrowth\b", texto_normalizado))
    
    if not (eh_naturovos or eh_eggpro or eh_growth):
        return False

    return True

def extrair_precos_contexto(texto, distancia=400):
    texto_normalizado = normalizar(texto)
    posicoes = []
    for termo in ["albumina", "naturovos", "eggpro", "egg pro", "growth", "1kg", "1000g"]:
        inicio = 0
        while True:
            posicao = texto_normalizado.find(termo, inicio)
            if posicao == -1:
                break
            posicoes.append(posicao)
            inicio = posicao + len(termo)

    if not posicoes:
        return []

    padrao_preco = re.compile(r"R\$\s*(\d{1,3}(?:[.\s]\d{3})*,\d{2})", flags=re.I)
    precos = []

    for match in padrao_preco.finditer(texto_normalizado):
        esta_perto = any(abs(match.start() - posicao) <= distancia for posicao in posicoes)
        if not esta_perto:
            continue
        try:
            valor = match.group(1).replace(".", "").replace(" ", "").replace(",", ".")
            valor = float(valor)
            if PRECO_MIN <= valor <= PRECO_ALVO:
                precos.append(valor)
        except ValueError:
            continue

    return sorted(set(precos))

# ============================================================
# BUSCAS
# ============================================================
def buscar_bing(loja, dominio):
    consultas = [
        f'site:{dominio} "albumina" "naturovos" "1kg"',
        f'site:{dominio} "albumina eggpro" 1kg',
        f'site:{dominio} "albumina egg pro" 1kg',
        f'site:{dominio} "albumina growth" 1kg',
    ]

    resultados = []
    for consulta in consultas:
        url = "https://www.bing.com/search?" + urllib.parse.urlencode({
            "q": consulta, "count": "20", "setlang": "pt-BR",
        })
        pagina = baixar(url)
        if not pagina: continue

        blocos = re.findall(r'<li class=["\']b_algo["\'][^>]>(.?)</li>', pagina, flags=re.I | re.S)

        for bloco in blocos:
            match = re.search(r'<a[^>]+href=["\']([^"\']+)["\'][^>]>(.?)</a>', bloco, flags=re.I | re.S)
            if not match: continue

            link = limpar_url(match.group(1))
            titulo = limpar_tags(match.group(2))
            titulo = re.sub(r"\s+", " ", titulo).strip()

            if not link.startswith(("http://", "https://")): continue
            if not pertence_ao_dominio(link, dominio): continue

            resultados.append({
                "loja": loja, "url": link, "title": titulo, "snippet": "", "origem": "bing",
            })
        time.sleep(0.6)
    return resultados

def buscar_google_shopping():
    consulta = 'albumina (naturovos OR eggpro OR "egg pro" OR growth) 1kg'
    url = "https://www.google.com/search?" + urllib.parse.urlencode({
        "tbm": "shop", "q": consulta, "hl": "pt-BR", "gl": "br",
    })
    pagina = baixar(url)
    if not pagina: return []

    resultados = []
    links = re.findall(r'href=["\'](https?://[^"\']+)["\']', pagina, flags=re.I)

    dominios_ignorar = ["google.", "youtube.", "accounts.", "support.", "gstatic."]
    for link in links:
        if any(d in link.lower() for d in dominios_ignorar): continue
        resultados.append({
            "loja": "Google Shopping", "url": limpar_url(link), "title": "Via Google Shopping",
            "snippet": "", "origem": "google",
        })
    return resultados[:20]

# ============================================================
# ANÁLISE DAS PÁGINAS (COM REGRAS DE PREÇO DIFERENTES)
# ============================================================
def analisar(candidato):
    url = candidato.get("url", "")
    if not url or eh_pagina_busca(url): return None

    pagina = baixar(url, timeout=12)
    if not pagina: return None

    texto_completo = candidato.get("title", "") + "\n" + limpar_tags(pagina)
    
    if not produto_ok(texto_completo): return None

    precos = extrair_precos_contexto(texto_completo)
    if not precos: return None

    # AQUI ESTÁ A REGRA DE PREÇO ESPECÍFICA
    texto_normalizado = normalizar(texto_completo)
    if "growth" in texto_normalizado:
        limite_desta_marca = 70.00
        marca_identificada = "Growth"
    else:
        limite_desta_marca = 60.00
        marca_identificada = "Naturovos/EggPro"

    preco = min(precos)
    
    # Se o preço for maior que o limite específico da marca, ignora
    if preco > limite_desta_marca:
        return None

    titulo = extrair_titulo(pagina, candidato.get("title", f"Albumina {marca_identificada} 1kg"))

    return {
        "loja": candidato.get("loja", "Loja não identificada"),
        "url": url,
        "preco": preco,
        "titulo": titulo,
        "origem": candidato.get("origem", ""),
        "marca": marca_identificada
    }

def remover_duplicados(candidatos):
    vistos = set()
    final = []
    for candidato in candidatos:
        url = candidato.get("url", "")
        url_limpa = url.split("#")[0].split("?")[0].rstrip("/")
        chave = url_limpa.lower()
        if not chave or chave in vistos: continue
        vistos.add(chave)
        final.append(candidato)
    return final

# ============================================================
# ENVIO DE E-MAIL
# ============================================================
def enviar_email(ofertas):
    linhas = [
        "MONITOR ALBUMINA 1KG — NOVA OFERTA",
        f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "Regras: Naturovos/EggPro (até R$60) | Growth (até R$70)",
        "",
    ]

    for oferta in ofertas:
        linhas.extend([
            f"Loja: {oferta['loja']}",
            f"Marca: {oferta['marca']}",
            f"Preço: R$ {oferta['preco']:.2f}",
            f"Produto: {oferta['titulo']}",
            f"Link: {oferta['url']}",
            "",
        ])

    payload = {
        "sender": {"name": "Monitor Albumina", "email": REMETENTE},
        "to": [{"email": DESTINATARIO}],
        "subject": "OFERTA: Albumina 1kg (Naturovos/EggPro/Growth) encontrada",
        "textContent": "\n".join(linhas),
    }

    dados = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    requisicao = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=dados,
        headers={
            "accept": "application/json",
            "api-key": BREVO_API_KEY,
            "content-type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(requisicao, timeout=25) as resposta:
            return resposta.status in (200, 201, 202)
    except Exception as erro:
        print(f"Erro ao enviar e-mail: {erro}")
        return False

# ============================================================
# PESQUISA PRINCIPAL
# ============================================================
def pesquisar():
    print("Iniciando busca —", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    candidatos = []

    try: candidatos.extend(buscar_google_shopping())
    except Exception as erro: print(f"Erro no Google Shopping: {erro}")

    for loja, dominio in LOJAS.items():
        print(f"→ {loja}")
        try: candidatos.extend(buscar_bing(loja, dominio))
        except Exception as erro: print(f"  Erro no Bing: {erro}")

    candidatos = remover_duplicados(candidatos)
    print(f"Total de candidatos únicos: {len(candidatos)}")

    ofertas = []
    for indice, candidato in enumerate(candidatos, start=1):
        try:
            oferta = analisar(candidato)
            if not oferta: continue

            chave = (oferta["url"], round(oferta["preco"], 2))
            if not any((item["url"], round(item["preco"], 2)) == chave for item in ofertas):
                ofertas.append(oferta)
        except Exception:
            pass

    ofertas.sort(key=lambda item: item["preco"])
    return ofertas

# ============================================================
# EXECUÇÃO
# ============================================================
if __name__ == "__main__":
    print("Monitor Albumina (3 marcas) — execução agendada")
    ofertas = pesquisar()

    if ofertas:
        print(f"{len(ofertas)} oferta(s) encontrada(s)!")
        for oferta in ofertas:
            print(f"  → {oferta['loja']} | {oferta['marca']} | R$ {oferta['preco']:.2f} | {oferta['titulo'][:50]}")

        if enviar_email(ofertas):
            print("E-mail enviado com sucesso.")
        else:
            print("Falha no envio do e-mail.")
    else:
        print("Nenhuma oferta de Albumina dentro dos limites de preço.")
