import os
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
    6. Não inclua links nem chamadas de venda.
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
    print(f"🌙 Postado: '{titulo}' -> {resultado.get('url')}")


if __name__ == "__main__":
    print("🌙 Gerando artigo esotérico da noite...")
    tema = escolher_tema()
    print(f"Tema sorteado: {tema}")

    titulo = gerar_titulo(tema)
    corpo = gerar_artigo_esoterico(tema)
    img_url = buscar_imagem_openverse("mystic astrology esoteric")
    img_html = gerar_tabela_imagem_blogger(img_url, titulo)

    aviso = (
        '<p style="font-size: 12px; color: #888; font-style: italic;">Este conteúdo tem '
        'caráter histórico, cultural e educativo sobre tradições místicas e não constitui '
        'aconselhamento médico, financeiro, jurídico, psicológico ou incentivo a qualquer '
        'prática de risco.</p>'
    )

    html_final = f"{img_html}{corpo}{aviso}"
    publicar_no_blogger(titulo, html_final)
    marcar_tema_usado(tema)
    print("✅ Concluído!")
