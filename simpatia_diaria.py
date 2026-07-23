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
    7. Não inclua links nem chamadas de venda.
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
