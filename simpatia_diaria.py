import os
import urllib.parse
import re
import time
import base64
import random
import requests
from groq import Groq
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# --- CONFIGURAÇÕES ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
BLOGGER_ID = os.environ.get("BLOGGER_ID_HOROSCOPO")
CLIENT_ID = os.environ.get("BLOGGER_CLIENT_ID")
CLIENT_SECRET = os.environ.get("BLOGGER_CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("BLOGGER_REFRESH_TOKEN")

for nome, valor in [
    ("GROQ_API_KEY", GROQ_API_KEY),
    ("BLOGGER_ID_HOROSCOPO", BLOGGER_ID),
    ("BLOGGER_CLIENT_ID", CLIENT_ID),
    ("BLOGGER_CLIENT_SECRET", CLIENT_SECRET),
    ("BLOGGER_REFRESH_TOKEN", REFRESH_TOKEN),
]:
    if not valor:
        raise ValueError(f"Faltou configurar a variável/segredo: {nome}")

groq_client = Groq(api_key=GROQ_API_KEY)
MODELO_IA = "llama-3.3-70b-versatile"

# --- GERACAO DE IMAGENS COM IA (Pollinations.ai) ---
# Opcional: se nao configurado, ou se qualquer etapa falhar, o script cai
# automaticamente no metodo antigo (busca de imagem no Openverse).
POLLINATIONS_TOKEN = os.environ.get("POLLINATIONS_TOKEN")  # opcional: remove marca dagua e aumenta limite
# Sem token: 1 requisicao a cada 15s. Com token gratuito (auth.pollinations.ai): a cada 5s.
INTERVALO_POLLINATIONS = 6 if POLLINATIONS_TOKEN else 16
IMGBB_API_KEY = os.environ.get("IMGBB_API_KEY")
QTD_MIN_IMAGENS = 3
QTD_MAX_IMAGENS = 5

# --- TEMAS DE SIMPATIAS POPULARES (a IA sorteia um por dia, evitando repetir) ---
TEMAS_SIMPATIA = [
    "simpatia para atrair dinheiro e prosperidade",
    "simpatia para atrair amor e paquera",
    "simpatia para proteção da casa e da família",
    "simpatia para conseguir emprego novo",
    "simpatia para abrir os caminhos e tirar obstáculos",
    "simpatia para harmonia no casamento",
    "simpatia para atrair boas energias na lua nova",
    "simpatia para curar mágoas e seguir em frente",
    "simpatia para ter sorte em jogos e sorteios",
    "simpatia para reconciliação entre amigos ou casais",
    "simpatia para proteção contra inveja e olho gordo",
    "simpatia para atrair clientes e prosperar no negócio",
    "simpatia da lua cheia para renovação pessoal",
    "simpatia para ter tranquilidade e paz no lar",
    "simpatia para realizar um desejo específico",
]

ARQUIVO_HISTORICO = "historico_simpatias.txt"


def tema_ja_usado(tema):
    if not os.path.exists(ARQUIVO_HISTORICO):
        return False
    with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as f:
        linhas = f.read().splitlines()
    # Considera "usado recentemente" se estiver entre os últimos 8 temas postados
    return tema in linhas[-8:]


def marcar_tema_usado(tema):
    with open(ARQUIVO_HISTORICO, "a", encoding="utf-8") as f:
        f.write(tema + "\n")


def escolher_tema():
    disponiveis = [t for t in TEMAS_SIMPATIA if not tema_ja_usado(t)]
    if not disponiveis:
        disponiveis = TEMAS_SIMPATIA  # reinicia o ciclo se já usou todos recentemente
    return random.choice(disponiveis)


IMAGEM_PADRAO = "https://upload.wikimedia.org/wikipedia/commons/thumb/9/95/News_icon.svg/640px-News_icon.svg.png"


def buscar_imagem_openverse(palavra_chave):
    try:
        resposta = requests.get(
            "https://api.openverse.org/v1/images/",
            params={
                "q": palavra_chave,
                "license_type": "commercial",
                "page_size": 3,
                "mature": "false",
            },
            headers={"User-Agent": "RoboSimpatia/1.0"},
            timeout=10,
        )
        resultados = resposta.json().get("results", [])
        return resultados[0]["url"] if resultados else IMAGEM_PADRAO
    except Exception as e:
        print(f"⚠️ Erro ao buscar imagem: {e}")
        return IMAGEM_PADRAO


DIMENSOES_RATIO = {
    "16:9": (1280, 720),
    "1:1": (1024, 1024),
    "9:16": (720, 1280),
}


def gerar_imagem_pollinations(prompt, ratio="16:9"):
    """Gera uma imagem via Pollinations.ai (gratuito, sem chave, sem cota diaria).
    Retorna bytes da imagem ou None se falhar."""
    largura, altura = DIMENSOES_RATIO.get(ratio, (1280, 720))
    try:
        prompt_codificado = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{prompt_codificado}"
        params = {
            "width": largura,
            "height": altura,
            "model": "flux",
            "seed": random.randint(1, 999999),
            "nologo": "true",
        }
        headers = {}
        if POLLINATIONS_TOKEN:
            headers["Authorization"] = f"Bearer {POLLINATIONS_TOKEN}"
        resposta = requests.get(url, params=params, headers=headers, timeout=120)
        resposta.raise_for_status()
        content_type = resposta.headers.get("Content-Type", "")
        if "image" not in content_type:
            raise ValueError(f"Resposta nao parece ser uma imagem (Content-Type: {content_type})")
        return resposta.content
    except Exception as e:
        print(f"⚠️ Pollinations.ai falhou para o prompt '{prompt[:40]}...': {e}")
        return None


def hospedar_imagem(imagem_bytes, nome_arquivo="imagem.png"):
    """Sobe a imagem gerada para o imgbb.com (host gratuito via API) e retorna a URL publica.
    Catbox.moe bloqueia uploads vindos de IPs de datacenter (ex: GitHub Actions), por isso
    usamos o imgbb, que aceita chamadas de API normalmente."""
    if not IMGBB_API_KEY:
        print("⚠️ Falha ao hospedar imagem: IMGBB_API_KEY nao configurada")
        return None
    try:
        b64 = base64.b64encode(imagem_bytes).decode("utf-8")
        resposta = requests.post(
            "https://api.imgbb.com/1/upload",
            data={"key": IMGBB_API_KEY, "image": b64, "name": nome_arquivo},
            timeout=30,
        )
        resposta.raise_for_status()
        dados = resposta.json()
        if dados.get("success"):
            return dados["data"]["url"]
        raise ValueError(f"Resposta inesperada do imgbb: {dados}")
    except Exception as e:
        print(f"⚠️ Falha ao hospedar imagem gerada: {e}")
        return None


def gerar_imagem_ia(prompt, ratio="16:9"):
    """Pipeline completo: gera a imagem no Pollinations.ai e hospeda no imgbb. Retorna URL ou None."""
    imagem_bytes = gerar_imagem_pollinations(prompt, ratio)
    if not imagem_bytes:
        return None
    return hospedar_imagem(imagem_bytes)


def _limpar_tag(texto):
    return re.sub(r"<[^>]+>", "", texto).strip()


def extrair_titulos_h2(html):
    return re.findall(r"<h2[^>]*>(.*?)</h2>", html, flags=re.IGNORECASE | re.DOTALL)


def contar_palavras_html(html):
    texto = re.sub(r"<[^>]+>", " ", html)
    return len(texto.split())


def calcular_qtd_imagens(wc, minimo, maximo, base_palavras, palavras_por_imagem_extra):
    if wc <= base_palavras:
        return minimo
    extras = (wc - base_palavras) // palavras_por_imagem_extra
    return min(maximo, minimo + extras)


def gerar_prompts_imagens_ia(titulo_post, secoes, quantidade, contexto_extra=""):
    """Pede a IA prompts de imagem em ingles: o primeiro uma capa mistica de alto impacto
    visual para atrair o clique, e os demais ligados a cada momento/secao do post."""
    qtd_secoes = max(0, quantidade - 1)
    secoes_usadas = secoes[:qtd_secoes]
    lista_secoes = "\n".join(f"- {s}" for s in secoes_usadas) or "- (sem subtitulos definidos, use o tema geral do post)"

    prompt = f"""
Voce e um diretor de arte criando prompts para um gerador de imagens por IA (estilo Stable Diffusion/Flux)
para um blog de misticismo e simpatias populares.
Titulo do post: "{titulo_post}"
{contexto_extra}

Preciso de exatamente {quantidade} prompts de imagem em INGLES, cada um em uma linha separada, SEM numeracao,
SEM aspas, SEM explicacoes - apenas os prompts, um por linha, nesta ordem:

1) A PRIMEIRA linha e a imagem de CAPA: precisa ser esteticamente marcante e atmosferica -
   velas acesas, altar simples, ervas, luz dourada ou dramatica, composicao central,
   clima misterioso e acolhedor ao mesmo tempo, sem texto escrito na imagem, pensada para
   maximizar cliques mantendo o tom respeitoso da tradicao popular.
2) As proximas linhas sao uma imagem para CADA um destes momentos/secoes do post (nesta ordem):
{lista_secoes}
   Cada prompt deve remeter visualmente ao conteudo daquela secao especifica, mantendo
   consistencia estetica (velas, ervas, luz suave, elementos simbolicos) com o tema geral.

Cada prompt: descritivo, rico em detalhes visuais (cenario, iluminacao, estilo artistico,
composicao), SEM citar nomes proprios de pessoas, marcas ou obras protegidas. Responda
APENAS com as {quantidade} linhas de prompt.
"""
    resposta = pedir_ia_groq(prompt, temperatura=0.8)
    linhas = [l.strip(" -\"") for l in resposta.strip().splitlines() if l.strip()]
    if len(linhas) < quantidade:
        while len(linhas) < quantidade:
            linhas.append(linhas[-1] if linhas else titulo_post)
    return linhas[:quantidade]


def montar_galeria_ia(titulo_post, corpo_html, minimo, maximo, contexto_extra=""):
    """Gera a galeria completa de imagens via Pollinations.ai. Lanca excecao se qualquer
    etapa falhar, para o chamador cair no fallback do Openverse."""
    if not IMGBB_API_KEY:
        raise RuntimeError("IMGBB_API_KEY nao configurada")

    secoes_brutas = extrair_titulos_h2(corpo_html)
    secoes = [_limpar_tag(s) for s in secoes_brutas]

    wc = contar_palavras_html(corpo_html)
    qtd = calcular_qtd_imagens(wc, minimo, maximo, base_palavras=300, palavras_por_imagem_extra=100)
    if secoes:
        qtd = min(qtd, len(secoes) + 1)
    qtd = max(1, qtd)

    prompts = gerar_prompts_imagens_ia(titulo_post, secoes, qtd, contexto_extra)

    galeria = []
    for i, prompt in enumerate(prompts):
        url = gerar_imagem_ia(prompt, ratio="16:9")
        if not url:
            raise RuntimeError(f"Falha ao gerar/hospedar imagem {i + 1}/{qtd} da galeria")
        alt = titulo_post if i == 0 else (secoes[i - 1] if i - 1 < len(secoes) else titulo_post)
        galeria.append((url, alt))
        if i < len(prompts) - 1:
            time.sleep(INTERVALO_POLLINATIONS)  # respeita o rate limit do Pollinations.ai

    return galeria, secoes_brutas


def inserir_imagens_no_corpo(corpo_html, secoes_brutas, galeria):
    """Insere as imagens de secao (a partir do indice 1 da galeria) logo apos os respectivos <h2>."""
    novo_html = corpo_html
    imagens_secao = galeria[1:]
    for i, (url, alt) in enumerate(imagens_secao):
        if i >= len(secoes_brutas):
            break
        h2_bruto = secoes_brutas[i]
        padrao = re.compile(r"(<h2[^>]*>" + re.escape(h2_bruto) + r"</h2>)", re.IGNORECASE)
        img_html = gerar_tabela_imagem_blogger(url, alt)
        novo_html, _ = padrao.subn(lambda m: m.group(1) + img_html, novo_html, count=1)
    return novo_html


def gerar_tabela_imagem_blogger(url_img, alt_title):
    return f'''<table align="center" cellpadding="0" cellspacing="0" class="tr-caption-container" style="margin-left: auto; margin-right: auto;"><tbody><tr><td style="text-align: center;"><img alt="{alt_title}" border="0" height="360" src="{url_img}" title="{alt_title}" width="640" /></td></tr></tbody></table><br />'''


def pedir_ia_groq(prompt, temperatura=0.8):
    response = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model=MODELO_IA,
        temperature=temperatura,
    )
    return response.choices[0].message.content.strip()


def gerar_titulo(tema):
    prompt = (
        f"Crie um título chamativo, em português do Brasil, sem aspas, para um post de blog "
        f"sobre '{tema}'. Responda apenas o título, texto puro."
    )
    return pedir_ia_groq(prompt, temperatura=0.7).replace('"', '').strip()


def gerar_artigo_simpatia(tema):
    prompt = f"""
    Você é um redator especializado em cultura popular brasileira, simpatias e tradições
    folclóricas, escrevendo para um blog de misticismo bem estabelecido e acolhedor.

    Escreva um artigo ORIGINAL e bem escrito sobre: {tema}.

    REGRAS DE FORMATO (HTML puro, sem Markdown):
    1. Um parágrafo de abertura (<p>) contextualizando a tradição e a origem popular da simpatia.
    2. Um subtítulo <h2>Como Fazer</h2> com uma lista <ul><li> dos materiais/ingredientes
       simples (velas, ervas comuns, papel, etc — nada perigoso, ilegal ou que envolva
       maus-tratos a animais) e o passo a passo em <p> ou <ol><li>.
    3. Um subtítulo <h2>Quando Fazer</h2> explicando o melhor dia/fase da lua/horário
       tradicionalmente associado.
    4. Um subtítulo <h2>Significado</h2> explicando o simbolismo por trás dos elementos usados.
    5. Termine com um parágrafo convidando o leitor a compartilhar nos comentários se já fez
       essa simpatia ou contar sua própria experiência — buscando gerar engajamento e senso
       de comunidade.
    6. O texto deve ter entre 300 e 450 palavras, tom acolhedor, respeitoso com a tradição,
       sem fazer promessas médicas, financeiras ou legais garantidas (é uma tradição cultural
       e de fé popular, não uma garantia de resultado).
    7. Coloque tag´s nos post´s
    """
    return pedir_ia_groq(prompt, temperatura=0.75)


def obter_credenciais():
    creds = Credentials(
        token=None,
        refresh_token=REFRESH_TOKEN,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
    )
    creds.refresh(Request())
    return creds


def publicar_no_blogger(titulo, conteudo):
    creds = obter_credenciais()
    blogger = build('blogger', 'v3', credentials=creds)
    corpo_postagem = {'kind': 'blogger#post', 'title': titulo, 'content': conteudo}
    resultado = blogger.posts().insert(blogId=BLOGGER_ID, body=corpo_postagem).execute()
    print(f"🕯️ Postado: '{titulo}' -> {resultado.get('url')}")


if __name__ == "__main__":
    print("🕯️ Gerando simpatia popular do dia...")
    tema = escolher_tema()
    print(f"Tema sorteado: {tema}")

    titulo = gerar_titulo(tema)
    corpo = gerar_artigo_simpatia(tema)

    try:
        galeria, secoes_brutas = montar_galeria_ia(
            titulo,
            corpo,
            minimo=QTD_MIN_IMAGENS,
            maximo=QTD_MAX_IMAGENS,
            contexto_extra=f"Tema da simpatia: {tema}",
        )
        img_html = gerar_tabela_imagem_blogger(galeria[0][0], titulo)
        corpo = inserir_imagens_no_corpo(corpo, secoes_brutas, galeria)
        print(f"🎨 Galeria com {len(galeria)} imagem(ns) gerada via Pollinations.ai.")
    except Exception as e:
        print(f"⚠️ Geracao de imagens via IA falhou, usando metodo padrao (Openverse): {e}")
        img_url = buscar_imagem_openverse("candle ritual mystic")
        img_html = gerar_tabela_imagem_blogger(img_url, titulo)

    aviso = (
        '<p style="font-size: 12px; color: #888; font-style: italic;">Este conteúdo é '
        'baseado em tradições populares e culturais, com fins de entretenimento e '
        'informação cultural. Não substitui aconselhamento médico, financeiro, jurídico '
        'ou psicológico profissional.</p>'
    )

    html_final = f"{img_html}{corpo}{aviso}"
    publicar_no_blogger(titulo, html_final)
    marcar_tema_usado(tema)
    print("✅ Concluído!")
