# ============================================================
# MONITOR BONÉ FLAMENGO LICENCIADO
# Preço máximo: R$ 50,00
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

PRECO_ALVO = 50.00
PRECO_MIN = 10.00

REMETENTE = "gabrielcapote@gmail.com"
DESTINATARIO = "gabrielcapote@gmail.com"

BREVO_API_KEY = os.environ.get("BREVO_API_KEY")

if not BREVO_API_KEY:
    print("ERRO: variável BREVO_API_KEY não encontrada.")
    print("Configure o secret BREVO_API_KEY no GitHub Actions.")
    raise SystemExit(1)


# ============================================================
# LOJAS E SITES
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
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,/;q=0.8"
    ),
}


def baixar(url, timeout=14):
    """Baixa uma página e retorna o HTML como texto."""
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
    """
    Remove acentos, converte para minúsculas
    e reduz espaços repetidos.
    """
    texto = html.unescape(texto or "")
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(caractere)
    )
    texto = texto.lower()
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def limpar_tags(html_texto):
    """Remove tags HTML e retorna apenas o texto."""
    html_texto = html_texto or ""
    html_texto = re.sub(r"<script\b[^>]>.?</script>", " ", html_texto,
                        flags=re.I | re.S)
    html_texto = re.sub(r"<style\b[^>]>.?</style>", " ", html_texto,
                        flags=re.I | re.S)
    html_texto = re.sub(r"<[^>]+>", " ", html_texto)
    return html.unescape(html_texto)


def limpar_url(url):
    """Remove redirecionamentos comuns de mecanismos de busca."""
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
    """Verifica se o link pertence ao domínio esperado."""
    try:
        hostname = urllib.parse.urlparse(url).hostname or ""
        hostname = hostname.lower()

        return (
            hostname == dominio
            or hostname.endswith("." + dominio)
        )

    except Exception:
        return False


def eh_pagina_busca(url):
    """Identifica páginas de pesquisa, que não são produtos individuais."""
    url_normalizada = normalizar(url)

    termos = [
        "/busca",
        "/search",
        "/buscar",
        "/pesquisa",
        "/result",
        "?q=",
        "?query=",
        "?keyword=",
        "/sch/",
        "/catalog/",
        "/lista/",
    ]

    return any(termo in url_normalizada for termo in termos)


def extrair_titulo(pagina, fallback="Produto Flamengo"):
    """Extrai o título da página."""
    match = re.search(
        r"<title[^>]>(.?)</title>",
        pagina or "",
        flags=re.I | re.S,
    )

    if not match:
        return fallback[:100]

    titulo = limpar_tags(match.group(1))
    titulo = re.sub(r"\s+", " ", titulo).strip()

    return titulo[:100] or fallback[:100]


# ============================================================
# FILTRO DE PRODUTO
# ============================================================

def produto_ok(texto):
    """
    Filtro heurístico.

    Importante: encontrar as palavras 'oficial', 'original'
    ou 'licenciado' não comprova, sozinho, a autenticidade
    do produto.
    """
    texto_normalizado = normalizar(texto)

    eh_bone = bool(
        re.search(r"\b(?:bone|cap|gorro)\b", texto_normalizado)
    )

    if not eh_bone:
        return False

    eh_flamengo = bool(
        re.search(r"\b(?:flamengo|mengao|crf)\b", texto_normalizado)
    )

    if not eh_flamengo:
        return False

    marcas_oficiais = [
        "new era",
        "starter",
        "adidas",
        "supercap",
        "nike",
        "puma",
        "reebok",
        "under armour",
    ]

    termos_licenca = [
        "licenciado",
        "oficial",
        "original",
        "autorizado",
    ]

    tem_marca = any(
        marca in texto_normalizado
        for marca in marcas_oficiais
    )

    tem_termo_licenca = any(
        termo in texto_normalizado
        for termo in termos_licenca
    )

    return tem_marca or tem_termo_licenca


def extrair_precos_contexto(texto, distancia=350):
    """
    Procura preços próximos às palavras boné, Flamengo,
    Mengão ou CRF.
    """
    texto_normalizado = normalizar(texto)

    posicoes = []

    for termo in ["bone", "flamengo", "mengao", "crf"]:
        inicio = 0

        while True:
            posicao = texto_normalizado.find(termo, inicio)

            if posicao == -1:
                break

            posicoes.append(posicao)
            inicio = posicao + len(termo)

    if not posicoes:
        return []

    padrao_preco = re.compile(
        r"R\$\s*"
        r"(\d{1,3}(?:[.\s]\d{3})*,\d{2})",
        flags=re.I,
    )

    precos = []

    for match in padrao_preco.finditer(texto_normalizado):
        esta_perto = any(
            abs(match.start() - posicao) <= distancia
            for posicao in posicoes
        )

        if not esta_perto:
            continue

        try:
            valor = (
                match.group(1)
                .replace(".", "")
                .replace(" ", "")
                .replace(",", ".")
            )

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
        (
            f'site:{dominio} "boné" "flamengo" '
            f'("licenciado" OR "oficial" OR "new era" OR "starter" OR "adidas")'
        ),
        f"site:{dominio} bone flamengo oficial",
        f"site:{dominio} bone flamengo licenciado",
    ]

    resultados = []

    for consulta in consultas:
        url = (
            "https://www.bing.com/search?"
            + urllib.parse.urlencode(
                {
                    "q": consulta,
                    "count": "20",
                    "setlang": "pt-BR",
                }
            )
        )

        pagina = baixar(url)

        if not pagina:
            continue

        blocos = re.findall(
            r'<li class=["\']b_algo["\'][^>]>(.?)</li>',
            pagina,
            flags=re.I | re.S,
        )

        for bloco in blocos:
            match = re.search(
                r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>'
                r'(.*?)</a>',
                bloco,
                flags=re.I | re.S,
            )

            if not match:
                continue

            link = limpar_url(match.group(1))
            titulo = limpar_tags(match.group(2))
            titulo = re.sub(r"\s+", " ", titulo).strip()

            if not link.startswith(("http://", "https://")):
                continue

            if not pertence_ao_dominio(link, dominio):
                continue

            resultados.append(
                {
                    "loja": loja,
                    "url": link,
                    "title": titulo,
                    "snippet": "",
                    "origem": "bing",
                }
            )

        time.sleep(0.8)

    return resultados


def buscar_google_shopping():
    consulta = "boné Flamengo oficial licenciado"

    url = (
        "https://www.google.com/search?"
        + urllib.parse.urlencode(
            {
                "tbm": "shop",
                "q": consulta,
                "hl": "pt-BR",
                "gl": "br",
            }
        )
    )

    pagina = baixar(url)

    if not pagina:
        return []

    resultados = []

    links = re.findall(
        r'href=["\'](https?://[^"\']+)["\']',
        pagina,
        flags=re.I,
    )

    domínios_ignorar = [
        "google.",
        "youtube.",
        "accounts.",
        "support.",
        "gstatic.",
    ]

    for link in links:
        if any(
            dominio in link.lower()
            for dominio in domínios_ignorar
        ):
            continue

        resultados.append(
            {
                "loja": "Google Shopping",
                "url": limpar_url(link),
                "title": "Via Google Shopping",
                "snippet": "",
                "origem": "google",
            }
        )

    return resultados[:15]


# ============================================================
# ANÁLISE DAS PÁGINAS
# ============================================================

def analisar(candidato):
    url = candidato.get("url", "")

    if not url or eh_pagina_busca(url):
        return None

    pagina = baixar(url, timeout=12)

    if not pagina:
        return None

    texto = (
        candidato.get("title", "")
        + "\n"
        + limpar_tags(pagina)
    )

    if not produto_ok(texto):
        return None

    precos = extrair_precos_contexto(texto)

    if not precos:
        return None

    titulo = extrair_titulo(
        pagina,
        candidato.get("title", "Boné Flamengo"),
    )

    return {
        "loja": candidato.get("loja", "Loja não identificada"),
        "url": url,
        "preco": min(precos),
        "titulo": titulo,
        "origem": candidato.get("origem", ""),
    }


def remover_duplicados(candidatos):
    """Remove URLs repetidas."""
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
# ENVIO DE E-MAIL PELA BREVO
# ============================================================

def enviar_email(ofertas):
    linhas = [
        "MONITOR BONÉ FLAMENGO — NOVA OFERTA",
        f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        f"Preço máximo configurado: R$ {PRECO_ALVO:.2f}",
        "Filtro utilizado: Licenciado/Oficial",
        "",
    ]

    for oferta in ofertas:
        linhas.extend(
            [
                f"Loja: {oferta['loja']}",
                f"Preço: R$ {oferta['preco']:.2f}",
                f"Produto: {oferta['titulo']}",
                f"Link: {oferta['url']}",
                "",
            ]
        )

    payload = {
        "sender": {
            "name": "Monitor Boné Flamengo",
            "email": REMETENTE,
        },
        "to": [
            {
                "email": DESTINATARIO,
            }
        ],
        "subject": "OFERTA: Boné Flamengo Licenciado",
        "textContent": "\n".join(linhas),
    }

    dados = json.dumps(
        payload,
        ensure_ascii=False,
    ).encode("utf-8")

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
        with urllib.request.urlopen(
            requisicao,
            timeout=25,
        ) as resposta:
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

def pesquisar():
    print()
    print("=" * 70)
    print(
        "Iniciando busca —",
        datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    )
    print("=" * 70)

    candidatos = []

    print("→ Google Shopping")

    try:
        candidatos.extend(buscar_google_shopping())
    except Exception as erro:
        print(f"  Erro no Google Shopping: {erro}")

    for loja, dominio in LOJAS.items():
        print(f"→ {loja}")

        try:
            candidatos.extend(
                buscar_bing(loja, dominio)
            )
        except Exception as erro:
            print(f"  Erro no Bing: {erro}")

    candidatos = remover_duplicados(candidatos)

    print()
    print(f"Total de candidatos únicos: {len(candidatos)}")

    ofertas = []

    for indice, candidato in enumerate(candidatos, start=1):
        print(
            f"\rAnalisando {indice}/{len(candidatos)}",
            end="",
            flush=True,
        )

        try:
            oferta = analisar(candidato)

            if not oferta:
                continue

            chave = (
                oferta["url"],
                round(oferta["preco"], 2),
            )

            ja_existe = any(
                (
                    item["url"],
                    round(item["preco"], 2),
                ) == chave
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

if _name_ == "_main_":
    print("Monitor Boné Flamengo — execução agendada")
    print(f"Preço máximo: R$ {PRECO_ALVO:.2f}")

    ofertas = pesquisar()

    if ofertas:
        print()
        print(f"{len(ofertas)} oferta(s) encontrada(s)!")

        for oferta in ofertas:
            print(
                f"  → {oferta['loja']} | "
                f"R$ {oferta['preco']:.2f} | "
                f"{oferta['titulo'][:60]}"
            )

        if enviar_email(ofertas):
            print("E-mail enviado com sucesso.")
        else:
            print("Falha no envio do e-mail.")

    else:
        print()
        print("Nenhuma oferta licenciada dentro do preço máximo.")

No arquivo do GitHub Actions, confirme também que a execução está assim:

- name: Executar monitor
  env:
    BREVO_API_KEY: ${{ secrets.BREVO_API_KEY }}
  run: python monitor.py
