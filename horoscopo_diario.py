import os
import requests
from groq import Groq
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# --- CONFIGURAÇÕES (variáveis de ambiente / GitHub Secrets) ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
BLOGGER_ID = os.environ.get("BLOGGER_ID_HOROSCOPO")  # ID do blog NOVO de horóscopo
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

# --- OS 12 SIGNOS, com palavra-chave em inglês pra buscar imagem relacionada ---
SIGNOS = {
    "Áries":      {"periodo": "21/03 a 19/04", "img": "aries zodiac symbol"},
    "Touro":      {"periodo": "20/04 a 20/05", "img": "taurus zodiac symbol"},
    "Gêmeos":     {"periodo": "21/05 a 20/06", "img": "gemini zodiac symbol"},
    "Câncer":     {"periodo": "21/06 a 22/07", "img": "cancer zodiac symbol"},
    "Leão":       {"periodo": "23/07 a 22/08", "img": "leo zodiac symbol"},
    "Virgem":     {"periodo": "23/08 a 22/09", "img": "virgo zodiac symbol"},
    "Libra":      {"periodo": "23/09 a 22/10", "img": "libra zodiac symbol"},
    "Escorpião":  {"periodo": "23/10 a 21/11", "img": "scorpio zodiac symbol"},
    "Sagitário":  {"periodo": "22/11 a 21/12", "img": "sagittarius zodiac symbol"},
    "Capricórnio":{"periodo": "22/12 a 19/01", "img": "capricorn zodiac symbol"},
    "Aquário":    {"periodo": "20/01 a 18/02", "img": "aquarius zodiac symbol"},
    "Peixes":     {"periodo": "19/02 a 20/03", "img": "pisces zodiac symbol"},
}

IMAGEM_PADRAO = "https://upload.wikimedia.org/wikipedia/commons/thumb/9/95/News_icon.svg/640px-News_icon.svg.png"


def buscar_imagem_openverse(palavra_chave):
    """Busca uma imagem gratuita e sem direitos autorais no Openverse (sem precisar de chave)."""
    try:
        resposta = requests.get(
            "https://api.openverse.org/v1/images/",
            params={
                "q": palavra_chave,
                "license_type": "commercial",
                "page_size": 3,
                "mature": "false",
            },
            headers={"User-Agent": "RoboHoroscopo/1.0"},
            timeout=10,
        )
        dados = resposta.json()
        resultados = dados.get("results", [])
        if resultados:
            return resultados[0]["url"]
        return IMAGEM_PADRAO
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


def gerar_horoscopo(signo, periodo):
    """Gera o texto original do horóscopo diário para um signo, em tom leve e místico."""
    prompt = f"""
    Você é um astrólogo experiente e carismático, escrevendo o horóscopo diário do signo de {signo}
    ({periodo}) para um blog popular brasileiro.

    Escreva um horóscopo ORIGINAL e envolvente, em português do Brasil, com tom leve, positivo e
    um toque de humor sutil (nunca debochado). NÃO mencione que é gerado por IA. NÃO use a mesma
    estrutura de frase repetidamente.

    REGRAS DE FORMATO (HTML puro, sem Markdown):
    1. Um parágrafo de abertura (<p>) sobre o clima geral do dia para o signo.
    2. Um subtítulo <h2>Amor</h2> com um parágrafo sobre relacionamentos.
    3. Um subtítulo <h2>Trabalho e Dinheiro</h2> com um parágrafo sobre carreira/finanças.
    4. Um subtítulo <h2>Saúde e Bem-estar</h2> com um parágrafo curto sobre disposição/energia.
    5. Termine com uma frase de "Dica do dia" dentro de uma tag <blockquote>, curta e inspiradora.
    6. O texto deve ter entre 300 e 400 palavras no total — bem escrito, envolvente, com
       parágrafos completos (não seja telegráfico nem raso). Não seja repetitivo. Não invente
       previsões alarmantes (evite prever doenças graves, mortes, desastres — mantenha tom
       leve e otimista mesmo nos alertas, e sempre construtivo).

    Não inclua links, não inclua chamadas de venda.
    """
    return pedir_ia_groq(prompt)


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
    corpo_postagem = {
        'kind': 'blogger#post',
        'title': titulo,
        'content': conteudo
    }
    resultado = blogger.posts().insert(blogId=BLOGGER_ID, body=corpo_postagem).execute()
    print(f"🔮 Postado: '{titulo}' -> {resultado.get('url')}")


if __name__ == "__main__":
    print("🌟 Iniciando geração do horóscopo diário para os 12 signos...")

    for signo, info in SIGNOS.items():
        try:
            print(f"✍️ Gerando horóscopo de {signo}...")
            texto_horoscopo = gerar_horoscopo(signo, info["periodo"])
            img_url = buscar_imagem_openverse(info["img"])
            img_html = gerar_tabela_imagem_blogger(img_url, f"Horóscopo de {signo}")

            titulo = f"Horóscopo de {signo} — Previsões de Hoje"
            html_final = f"{img_html}{texto_horoscopo}"

            publicar_no_blogger(titulo, html_final)
        except Exception as e:
            print(f"❌ Erro ao processar o signo {signo}: {e}")

    print("✅ Processo concluído!")
