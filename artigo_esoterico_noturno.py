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

# --- TAGS/MARCADORES FIXOS DO BLOG ---
TAGS_ESOTERICO = ["Curiosidades", "Histórias", "Resenha"]

# --- TEMAS ESOTÉRICOS (a IA sorteia um por dia, evitando repetir os recentes) ---
TEMAS_ESOTERICOS = [
    "a história de vida e os ensinamentos de Aleister Crowley",
    "os fundamentos da astrologia planetária e o significado de cada planeta",
    "o que é numerologia e como calcular o seu número de destino",
    "a origem histórica da Goetia e o Lemegeton (Chave de Salomão)",
    "os princípios herméticos e o significado do Caduceu de Hermes Trismegisto",
    "a história da Wicca moderna e Gerald Gardner",
    "lendas e mitos sobre os arcanjos na tradição ocultista",
    "a vida de Helena Blavatsky e a Teosofia",
    "o simbolismo dos Arcanos Maiores do Tarot",
    "a tradição da Cabala e a Árvore da Vida",
    "mitos e lendas sobre bruxas na Europa medieval",
    "a história das Sociedades Herméticas como a Aurora Dourada (Golden Dawn)",
    "curiosidades sobre alquimia e a busca pela pedra filosofal",
    "o papel da lua em rituais mágicos através da história",
    "quem foi Nostradamus e suas profecias mais famosas",
    "a mitologia egípcia e seus deuses ligados à magia",
    "a história do espiritismo e Allan Kardec",
    "curiosidades sobre grimórios antigos e livros de magia históricos",
    "os elementos (terra, água, fogo, ar) na tradição mágica ocidental",
    "mitos nórdicos e o papel das runas na adivinhação",
     "a infância rebelde de Aleister Crowley e sua expulsão das sociedades ocultistas",
    "o sistema mágico de Thelema e o princípio de 'Faze o que tu queres'",
    "o Livro da Lei (Liber AL vel Legis) e a ditadura de Aiwass",
    "os rituais da Abadia de Thelema na Sicília e a morte de Raoul Loveday",
    "a relação de Crowley com a Ordem da Aurora Dourada e seus conflitos internos",
    "a influência de Saturno como o Grande Maléfico e seu papel no amadurecimento espiritual",
    "o significado de Júpiter na expansão da consciência e na sorte mágica",
    "Marte na astrologia: agressividade, guerra e impulso sexual nos mapas natais",
    "Vênus e a magia do amor: como usar as fases de Vênus em rituais",
    "Mercúrio retrógrado: mitos, verdades e como lidar com comunicações no ocultismo",
    "o papel das casas astrológicas (1 a 12) na determinação do destino humano",
    "os aspectos de quadratura e oposição em mapas astrológicos e seus desafios cármicos",
    "como calcular não apenas o número de destino, mas também o número da alma e da personalidade",
    "o significado do número 11 como número mestre na numerologia espiritual",
    "a vibração do número 22 e o conceito de 'Mestre Construtor'",
    "a numerologia cabalística e a relação entre números e letras hebraicas",
    "a sequência de Fibonacci e a proporção áurea aplicadas à magia natural",
    "a estrutura detalhada do Lemegeton: Goetia, Theurgia, Ars Paulina e Ars Almadel",
    "a importância do selo de Salomão e sua utilização para constranger espíritos",
    "os 72 demônios da Goetia: hierarquia, poderes e invocações específicas (ex: Bael, Paimon)",
    "o uso do círculo mágico e do triângulo de arte na evocações goéticas",
    "comparação entre a Goetia de Salomão e a grimória 'A Chave Menor de Salomão'",
    "os 7 Princípios Herméticos explicados detalhadamente (Mentalismo, Correspondência, Vibração...)",
    "o significado oculto do Caduceu de Hermes: o equilíbrio entre as serpentes e a varinha",
    "a Tábua de Esmeralda e a frase 'O que está embaixo é como o que está em cima'",
    "as três etapas da alquimia interna: Nigredo (putrefação), Albedo (purificação) e Rubedo (perfeição)",
    "a busca pela Pedra Filosofal não como objeto, mas como estado de iluminação espiritual",
    "alquimistas famosos: Nicolas Flamel, Paracelso e as lendas sobre suas descobertas",
    "Gerald Gardner e a fundação da Wicca na década de 1950 com o Livro das Sombras",
    "a estrutura dos coven wiccanos: Sumo Sacerdote, Sacerdotisa e os graus iniciáticos",
    "a Roda do Ano wiccan: os 8 Sabbats (Samhain, Yule, Imbolc, Ostara, Beltane, Litha, Lammas, Mabon)",
    "a diferença entre bruxaria tradicional (folk magic) e a bruxaria cerimonial",
    "o uso do athame, do cálice, da vassoura e do caldeirão em rituais modernos",
    "as 10 Sephiroth da Árvore da Vida e seus atributos divinos (Kether, Chokhmah, Binah...)",
    "os 22 caminhos da Árvore da Vida e sua correlação com os Arcanos Maiores do Tarot",
    "a Cabala Luriânica e o conceito de Tzimtzum (a contração divina) para a criação do universo",
    "o estudo do Qliphoth (as cascas ou árvore da morte) e seu uso na magia do caos",
    "a jornada do Louco (Arcano 0) através dos Arcanos Maiores como uma alegoria da vida",
    "o simbolismo oculto do Arcano X (Roda da Fortuna) e do Arcano XIII (Morte) como transformação",
    "a história do Tarot de Marselha versus o Tarot de Rider-Waite-Smith",
    "como fazer tiragens de 3 cartas (passado, presente, futuro) e tiragens em cruz celta",
    "Helena Blavatsky: suas viagens pelo Oriente, contatos com mestres ascensionados e a Doutrina Secreta",
    "a Sociedade Teosófica e sua influência sobre o movimento Nova Era",
    "a Ordem Hermética da Aurora Dourada (Golden Dawn): membros ilustres (Mathers, Yeats, Crowley)",
    "os rituais de iniciação da Aurora Dourada e o sistema de graus (Neófito, Zelador, Praticante...)",
    "a rivalidade entre a Aurora Dourada e a Ordem dos Templários Orientais (O.T.O.)",
    "os 4 Arcanjos maiores (Miguel, Gabriel, Rafael, Uriel) e suas funções no plano terrestre",
    "os Arcanjos caídos e a guerra nos céus segundo os textos apócrifos",
    "a mitologia egípcia: Osíris, Ísis e Hórus e o mito da ressurreição ligado à magia funerária",
    "o deus Thoth (Hermes) como patrono da escrita, da magia e da medição do tempo",
    "mitos nórdicos: as 24 runas do Futhark Antigo e suas interpretações divinatórias",
    "a lenda de Odin pendurado na Árvore do Mundo (Yggdrasil) para obter o conhecimento das runas",
    "as Valquírias e seu papel na escolha dos guerreiros mortos em batalha",
    "Allan Kardec e a codificação do Espiritismo: O Livro dos Espíritos e a mediunidade",
    "a diferença entre psicografia, psicofonia e vidência mediúnica",
    "a história do espiritismo no Brasil e a influência de Chico Xavier",
    "rituais antigos de necromancia na Grécia e Roma para consultar os mortos",
    "o uso dos 4 elementos (Terra, Água, Fogo, Ar) em rituais de banimento e consagração",
    "a invocação dos Guardiões das Torres (Elementais: Gnomos, Ondinas, Salamandras e Silfos)",
    "o papel das plantas, ervas e cristais na magia natural (fitoterapia mágica)"
]

ARQUIVO_HISTORICO = "historico_esoterico.txt"


def tema_ja_usado(tema):
    if not os.path.exists(ARQUIVO_HISTORICO):
        return False
    with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as f:
        linhas = f.read().splitlines()
    return tema in linhas[-10:]


def marcar_tema_usado(tema):
    with open(ARQUIVO_HISTORICO, "a", encoding="utf-8") as f:
        f.write(tema + "\n")


def escolher_tema():
    disponiveis = [t for t in TEMAS_ESOTERICOS if not tema_ja_usado(t)]
    if not disponiveis:
        disponiveis = TEMAS_ESOTERICOS
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
            headers={"User-Agent": "RoboEsoterico/1.0"},
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
    """Pede a IA prompts de imagem em ingles: o primeiro uma capa mistica/historica de alto
    impacto visual para atrair o clique, e os demais ligados a cada momento/secao do post."""
    qtd_secoes = max(0, quantidade - 1)
    secoes_usadas = secoes[:qtd_secoes]
    lista_secoes = "\n".join(f"- {s}" for s in secoes_usadas) or "- (sem subtitulos definidos, use o tema geral do post)"

    prompt = f"""
Voce e um diretor de arte criando prompts para um gerador de imagens por IA (estilo Stable Diffusion/Flux)
para um blog documental sobre historia do ocultismo e esoterismo.
Titulo do post: "{titulo_post}"
{contexto_extra}

Preciso de exatamente {quantidade} prompts de imagem em INGLES, cada um em uma linha separada, SEM numeracao,
SEM aspas, SEM explicacoes - apenas os prompts, um por linha, nesta ordem:

1) A PRIMEIRA linha e a imagem de CAPA: precisa ser esteticamente marcante e atmosferica -
   estilo pintura antiga/gravura historica ou fotografia dramatica de biblioteca/manuscrito
   antigo, iluminacao de velas ou dourada, composicao central misteriosa, sem texto escrito
   na imagem, pensada para maximizar cliques mantendo tom serio e documental (nao caricato).
2) As proximas linhas sao uma imagem para CADA um destes momentos/secoes do post (nesta ordem):
{lista_secoes}
   Cada prompt deve remeter visualmente ao conteudo daquela secao especifica, mantendo
   consistencia estetica (manuscritos, simbolos, luz dourada/velas) com o tema geral.

Cada prompt: descritivo, rico em detalhes visuais (cenario, iluminacao, estilo artistico,
composicao), SEM citar nomes proprios de pessoas reais, marcas ou obras protegidas -
descreva visualmente sem citar nomes proprios especificos. Responda APENAS com as
{quantidade} linhas de prompt.
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
    qtd = calcular_qtd_imagens(wc, minimo, maximo, base_palavras=450, palavras_por_imagem_extra=150)
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


def pedir_ia_groq(prompt, temperatura=0.7):
    response = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model=MODELO_IA,
        temperature=temperatura,
    )
    return response.choices[0].message.content.strip()


def gerar_titulo(tema):
    prompt = (
        f"Crie um título envolvente e misterioso, em português do Brasil, sem aspas, para um "
        f"artigo de blog sobre: {tema}. Responda apenas o título, texto puro."
    )
    return pedir_ia_groq(prompt, temperatura=0.7).replace('"', '').strip()


def gerar_artigo_esoterico(tema):
    prompt = f"""
    Você é um escritor especializado em história do ocultismo, esoterismo e tradições
    místicas, escrevendo para um blog respeitado sobre o tema, com tom narrativo envolvente
    e educativo (como um documentário bem escrito, não sensacionalista).

    Escreva um artigo ORIGINAL e aprofundado sobre: {tema}.

    REGRAS DE CONTEÚDO:
    - Trate o tema de forma histórica, cultural e educativa. Baseie-se em fatos históricos
      reais e conhecidos sobre o assunto quando o tema for uma figura ou evento histórico.
    - Não incentive práticas perigosas, ilegais ou que causem dano a si mesmo, a outras
      pessoas ou a animais. Trate qualquer prática ritual mencionada como informação
      histórica/cultural, não como instrução literal a seguir.
    - Não faça previsões, promessas de poder sobre outras pessoas, ou alegações médicas.
    - Mantenha tom respeitoso com diferentes tradições religiosas e culturais.

    REGRAS DE FORMATO (HTML puro, sem Markdown):
    1. Um parágrafo de abertura (<p>) que prenda o leitor com uma curiosidade ou pergunta
       instigante sobre o tema.
    2. NO MÍNIMO 3 subtítulos <h2>, cada um explorando um ângulo diferente (origem histórica,
       principais personagens/símbolos, curiosidades, legado/influência atual).
    3. Pelo menos 1 trecho dentro de <blockquote> com uma frase ou citação histórica marcante
       relacionada ao tema (pode ser parafraseada, sem inventar citação literal atribuída
       falsamente a alguém).
    4. Termine com um parágrafo convidando o leitor a comentar sua opinião, compartilhar
       curiosidades que conhece sobre o tema, ou seguir o blog para mais conteúdos —
       buscando construir uma comunidade engajada de leitores interessados em misticismo.
    5. O texto deve ter entre 400 e 800 palavras, bem escrito e envolvente, sem repetição.
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


def publicar_no_blogger(titulo, conteudo, tags=None):
    creds = obter_credenciais()
    blogger = build('blogger', 'v3', credentials=creds)
    corpo_postagem = {'kind': 'blogger#post', 'title': titulo, 'content': conteudo}
    if tags:
        corpo_postagem['labels'] = tags
    resultado = blogger.posts().insert(blogId=BLOGGER_ID, body=corpo_postagem).execute()
    print(f"🌙 Postado: '{titulo}' -> {resultado.get('url')}")


if __name__ == "__main__":
    print("🌙 Gerando artigo esotérico da noite...")
    tema = escolher_tema()
    print(f"Tema sorteado: {tema}")

    titulo = gerar_titulo(tema)
    corpo = gerar_artigo_esoterico(tema)

    try:
        galeria, secoes_brutas = montar_galeria_ia(
            titulo,
            corpo,
            minimo=QTD_MIN_IMAGENS,
            maximo=QTD_MAX_IMAGENS,
            contexto_extra=f"Tema do artigo: {tema}",
        )
        img_html = gerar_tabela_imagem_blogger(galeria[0][0], titulo)
        corpo = inserir_imagens_no_corpo(corpo, secoes_brutas, galeria)
        print(f"🎨 Galeria com {len(galeria)} imagem(ns) gerada via Pollinations.ai.")
    except Exception as e:
        print(f"⚠️ Geracao de imagens via IA falhou, usando metodo padrao (Openverse): {e}")
        img_url = buscar_imagem_openverse("mystic astrology esoteric")
        img_html = gerar_tabela_imagem_blogger(img_url, titulo)

    aviso = (
        '<p style="font-size: 12px; color: #888; font-style: italic;">Este conteúdo tem '
        'caráter histórico, cultural e educativo sobre tradições místicas e não constitui '
        'aconselhamento médico, financeiro, jurídico, psicológico ou incentivo a qualquer '
        'prática de risco.</p>'
    )

    html_final = f"{img_html}{corpo}{aviso}"
    publicar_no_blogger(titulo, html_final, TAGS_ESOTERICO)
    marcar_tema_usado(tema)
    print("✅ Concluído!")
