# ============================================================
# MONITOR CHINELO + SUNGA FLAMENGO
# Chinelo: até R$ 25,00 | tamanhos 43 / 43-44 / 44
# Sunga: tamanho M | até R$ 50,00
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
# CONFIGURAÇÕES
# ============================================================
REMETENTE = "gabrielcapote@gmail.com"
DESTINATARIO = "gabrielcapote@gmail.com"

BREVO_API_KEY = os.environ.get("BREVO_API_KEY")
if not BREVO_API_KEY:
    print("ERRO: variável BREVO_API_KEY não encontrada.")
    print("Configure o secret BREVO_API_KEY no GitHub Actions.")
    raise SystemExit(1)

# ============================================================
# PRODUTOS QUE SERÃO MONITORADOS
# ============================================================
PRODUTOS = [
    {
        "nome": "Chinelo Flamengo",
        "preco_max": 25.00,
        "preco_min": 5.00,
        "keywords_obrigatorias": [r"\b(?:chinelo|sandalia|sandália|slide|slides)\b", r"\b(?:flamengo|mengao|mengão|crf)\b"],
        "keywords_tamanho": [r"\b(?:43|43/?44|44)\b"],
        "termos_busca": [
            'chinelo flamengo 43',
            'chinelo flamengo 44',
            'chinelo flamengo 43/44',
            'slide flamengo 43',
            'slide flamengo 44',
        ],
        "assunto_email": "OFERTA: Chinelo Flamengo ≤ R$ 25",
    },
    {
        "nome": "Sunga Flamengo",
        "preco_max": 50.00,
        "preco_min": 10.00,
        "keywords_obrigatorias": [r"\b(?:sunga|cueca de banho|swim)\b", r"\b(?:flamengo|mengao|mengão|crf)\b"],
        "keywords_tamanho": [r"\b(?:tamanho\s*m|tam\.?\s*m|\bM\b)"],
        "termos_busca": [
            'sunga flamengo M',
            'sunga flamengo tamanho M',
            'sunga oficial flamengo M',
        ],
        "assunto_email": "OFERTA: Sunga Flamengo M ≤ R$ 50",
    },
]

# ============================================================
# LOJAS
# ============================================================
LOJAS = {
    "Loja Oficial Flamengo": "loja.flamengo.com.br",
    "Netshoes": "netshoes.com.br",
    "Centauro": "centauro.com.br",
    "FutFanatics": "futfanatics.com.br",
    "Shopee": "shopee.com.br",
    "Mercado Livre": "mercadolivre.com.br",
    "Amazon": "amazon.com.br",
    "Magazine Luiza": "magazineluiza.com.br",
    "Americanas": "americanas.com.br",
    "Promobit": "promobit.com.br",
    "Pelando": "pelando.com.br",
    "Buscapé": "buscape.com.br",
    "Kanui": "kanui.com.br",
    "Dafiti": "dafiti.com.br",
    "Casas Bahia": "casasbahia.com.br",
    "Extra": "extra.com.br",
    "Ponto": "ponto.com.br",
    "Zoom": "zoom.com.br",
    "Riachuelo": "riachuelo.com.br",
    "C&A": "cea.com.br",
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
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def baixar(url, timeout=14):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resposta:
            codificacao = resposta.headers.get_content_charset() or "utf-8"
            return resposta.read().decode(codificacao, errors="ignore")
    except urllib.error.HTTPError as erro:
        print(f"\nHTTP {erro.code} ao acessar: {url}")
        return ""
    except urllib.error.URLError as erro:
        print(f"\nFalha de conexão ao acessar {url}: {erro.reason}")
        return ""
    except Exception as erro:
        print(f"\nErro ao acessar {url}: {erro}")
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
    html_texto = re.sub(r"<script\b[^>]*>.*?</script>", " ", html_texto, flags=re.I | re.S)
    html_texto = re.sub(r"<style\b[^>]*>.*?</style>", " ", html_texto, flags=re.I | re.S)
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

def extrair_titulo(pagina, fallback="Produto Flamengo"):
    match = re.search(r"<title[^>]*>(.*?)</title>", pagina or "", flags=re.I | re.S)
    if not match:
        return fallback[:120]
    titulo = limpar_tags(match.group(1))
    titulo = re.sub(r"\s+", " ", titulo).strip()
    return titulo[:120] or fallback[:120]

# ============================================================
# FILTRO DE PRODUTO
# ============================================================
def produto_ok(texto, produto):
    texto_normalizado = normalizar(texto)

    # Verifica palavras obrigatórias
    for padrao in produto["keywords_obrigatorias"]:
        if not re.search(padrao, texto_normalizado, flags=re.I):
            return False

    # Verifica tamanho (quando especificado)
    if produto.get("keywords_tamanho"):
        tem_tamanho = any(
            re.search(padrao, texto_normalizado, flags=re.I)
            for padrao in produto["keywords_tamanho"]
        )
        if not tem_tamanho:
            return False

    return True

def extrair_precos_contexto(texto, produto, distancia=400):
    texto_normalizado = normalizar(texto)
    posicoes = []

    # Pega posições das palavras-chave principais
    palavras = ["flamengo", "mengao", "mengão", "crf", "chinelo", "sunga", "slide"]
    for termo in palavras:
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
            if produto["preco_min"] <= valor <= produto["preco_max"]:
                precos.append(valor)
        except ValueError:
            continue

    return sorted(set(precos))

# ============================================================
# BUSCAS
# ============================================================
def buscar_bing(loja, dominio, termo):
    consultas = [
        f'site:{dominio} {termo}',
        f'site:{dominio} "{termo}"',
    ]

    resultados = []
    for consulta in consultas:
        url = "https://www.bing.com/search?" + urllib.parse.urlencode({
            "q": consulta,
            "count": "15",
            "setlang": "pt-BR",
        })
        pagina = baixar(url)
        if not pagina:
            continue

        blocos = re.findall(r'<li class=["\']b_algo["\'][^>]*>(.*?)</li>', pagina, flags=re.I | re.S)

        for bloco in blocos:
            match = re.search(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', bloco, flags=re.I | re.S)
            if not match:
                continue

            link = limpar_url(match.group(1))
            titulo = limpar_tags(match.group(2))
            titulo = re.sub(r"\s+", " ", titulo).strip()

            if not link.startswith(("http://", "https://")):
                continue
            if not pertence_ao_dominio(link, dominio):
                continue

            resultados.append({
                "loja": loja,
                "url": link,
                "title": titulo,
                "snippet": "",
                "origem": "bing",
            })
        time.sleep(0.6)

    return resultados

def buscar_google_shopping(termo):
    url = "https://www.google.com/search?" + urllib.parse.urlencode({
        "tbm": "shop",
        "q": termo,
        "hl": "pt-BR",
        "gl": "br",
    })
    pagina = baixar(url)
    if not pagina:
        return []

    resultados = []
    links = re.findall(r'href=["\'](https?://[^"\']+)["\']', pagina, flags=re.I)

    dominios_ignorar = ["google.", "youtube.", "accounts.", "support.", "gstatic."]
    for link in links:
        if any(d in link.lower() for d in dominios_ignorar):
            continue
        resultados.append({
            "loja": "Google Shopping",
            "url": limpar_url(link),
            "title": "Via Google Shopping",
            "snippet": "",
            "origem": "google",
        })
    return resultados[:15]

# ============================================================
# ANÁLISE DAS PÁGINAS
# ============================================================
def analisar(candidato, produto):
    url = candidato.get("url", "")
    if not url or eh_pagina_busca(url):
        return None

    pagina = baixar(url, timeout=12)
    if not pagina:
        return None

    texto = candidato.get("title", "") + "\n" + limpar_tags(pagina)

    if not produto_ok(texto, produto):
        return None

    precos = extrair_precos_contexto(texto, produto)
    if not precos:
        return None

    titulo = extrair_titulo(pagina, candidato.get("title", produto["nome"]))

    return {
        "produto": produto["nome"],
        "loja": candidato.get("loja", "Loja não identificada"),
        "url": url,
        "preco": min(precos),
        "titulo": titulo,
        "origem": candidato.get("origem", ""),
    }

def remover_duplicados(candidatos):
    vistos = set()
    final = []
    for candidato in candidatos:
        url = candidato.get("url", "")
        url_limpa = url.split("#")[0].split("?")[0].rstrip("/")
        chave = url_limpa.lower()
        if not chave or chave in vistos:
            continue
        vistos.add(chave)
        final.append(candidato)
    return final

# ============================================================
# ENVIO DE E-MAIL
# ============================================================
def enviar_email(ofertas, produto):
    linhas = [
        f"MONITOR {produto['nome'].upper()} — NOVA OFERTA",
        f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        f"Preço máximo configurado: R$ {produto['preco_max']:.2f}",
        "",
    ]

    for oferta in ofertas:
        linhas.extend([
            f"Loja: {oferta['loja']}",
            f"Preço: R$ {oferta['preco']:.2f}",
            f"Produto: {oferta['titulo']}",
            f"Link: {oferta['url']}",
            "",
        ])

    payload = {
        "sender": {"name": f"Monitor {produto['nome']}", "email": REMETENTE},
        "to": [{"email": DESTINATARIO}],
        "subject": produto["assunto_email"],
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
    except urllib.error.HTTPError as erro:
        corpo = erro.read().decode("utf-8", errors="ignore")
        print(f"Erro Brevo HTTP {erro.code}: {corpo}")
        return False
    except Exception as erro:
        print(f"Erro ao enviar e-mail: {erro}")
        return False

# ============================================================
# PESQUISA PRINCIPAL
# ============================================================
def pesquisar(produto):
    print()
    print("=" * 70)
    print(f"Buscando: {produto['nome']} —", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    print(f"Preço máximo: R$ {produto['preco_max']:.2f}")
    print("=" * 70)

    candidatos = []

    # Google Shopping
    for termo in produto["termos_busca"]:
        print(f"→ Google Shopping: {termo}")
        try:
            candidatos.extend(buscar_google_shopping(termo))
        except Exception as erro:
            print(f"  Erro no Google Shopping: {erro}")

    # Bing por loja
    for loja, dominio in LOJAS.items():
        for termo in produto["termos_busca"]:
            print(f"→ {loja} | {termo}")
            try:
                candidatos.extend(buscar_bing(loja, dominio, termo))
            except Exception as erro:
                print(f"  Erro no Bing: {erro}")

    candidatos = remover_duplicados(candidatos)
    print()
    print(f"Total de candidatos únicos: {len(candidatos)}")

    ofertas = []
    for indice, candidato in enumerate(candidatos, start=1):
        print(f"\rAnalisando {indice}/{len(candidatos)}", end="", flush=True)
        try:
            oferta = analisar(candidato, produto)
            if not oferta:
                continue

            chave = (oferta["url"], round(oferta["preco"], 2))
            ja_existe = any(
                (item["url"], round(item["preco"], 2)) == chave
                for item in ofertas
            )
            if not ja_existe:
                ofertas.append(oferta)
        except Exception as erro:
            print(f"\nErro ao analisar candidato: {erro}")

    print()
    ofertas.sort(key=lambda item: item["preco"])
    return ofertas

# ============================================================
# EXECUÇÃO
# ============================================================
if __name__ == "__main__":
    print("Monitor Chinelo + Sunga Flamengo — execução agendada")

    for produto in PRODUTOS:
        ofertas = pesquisar(produto)

        if ofertas:
            print()
            print(f"{len(ofertas)} oferta(s) encontrada(s) para {produto['nome']}!")
            for oferta in ofertas:
                print(f"  → {oferta['loja']} | R$ {oferta['preco']:.2f} | {oferta['titulo'][:70]}")

            if enviar_email(ofertas, produto):
                print("E-mail enviado com sucesso.")
            else:
                print("Falha no envio do e-mail.")
        else:
            print()
            print(f"Nenhuma oferta de {produto['nome']} dentro do preço máximo.")
