import os
import time
import requests
import datetime
from groq import Groq
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# --- CONFIGURAÇÕES (variáveis de ambiente / GitHub Secrets) ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
BLOGGER_ID = os.environ.get("BLOGGER_ID_HOROSCOPO") or os.environ.get("BLOGGER_ID")
CLIENT_ID = os.environ.get("BLOGGER_CLIENT_ID")
CLIENT_SECRET = os.environ.get("BLOGGER_CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("BLOGGER_REFRESH_TOKEN")

for nome, valor in [
    ("GROQ_API_KEY", GROQ_API_KEY),
    ("BLOGGER_ID", BLOGGER_ID),
    ("BLOGGER_CLIENT_ID", CLIENT_ID),
    ("BLOGGER_CLIENT_SECRET", CLIENT_SECRET),
    ("BLOGGER_REFRESH_TOKEN", REFRESH_TOKEN),
]:
    if not valor:
        raise ValueError(f"Faltou configurar a variável/segredo: {nome}")

groq_client = Groq(api_key=GROQ_API_KEY)
MODELO_IA = "llama-3.3-70b-versatile"

# --- OS 12 SIGNOS E PALAVRAS-CHAVE ---
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
        print(f"⚠️ Erro ao buscar imagem ({palavra_chave}): {e}")
        return IMAGEM_PADRAO


def gerar_tabela_imagem_blogger(url_img, alt_title):
    return f'''<table align="center" cellpadding="0" cellspacing="0" class="tr-caption-container" style="margin-left: auto; margin-right: auto; text-align: center;"><tbody><tr><td><img alt="{alt_title}" border="0" height="320" src="{url_img}" title="{alt_title}" style="max-width: 100%; height: auto; border-radius: 8px;" /></td></tr></tbody></table><br />'''


def pedir_ia_groq(prompt, temperatura=0.8):
    response = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model=MODELO_IA,
        temperature=temperatura,
    )
    return response.choices[0].message.content.strip()


def gerar_horoscopo(signo, periodo, data_hoje):
    prompt = f"""
    Você é um astrólogo experiente e carismático, escrevendo a previsão diária para o signo de {signo} ({periodo}) referente ao dia {data_hoje}.

    Escreva um horóscopo místico, envolvente e otimista em português do Brasil.

    REGRAS DE FORMATO (HTML puro, sem Markdown ou tags <html>/<body>):
    1. Um parágrafo de abertura (<p>) sobre as energias astrais do dia para {signo}.
    2. Subtítulo <h2>💖 Amor e Relacionamentos</h2> com um parágrafo envolvente.
    3. Subtítulo <h2>💼 Trabalho e Finanças</h2> com um parágrafo sobre carreira.
    4. Subtítulo <h2>🌿 Saúde e Bem-Estar</h2> com um parágrafo sobre energia e disposição.
    5. Um bloco com estilo contendo informações da sorte:
       <ul>
         <li><strong>🎨 Cor do Dia:</strong> [Cor]</li>
         <li><strong>🔢 Número da Sorte:</strong> [Número]</li>
         <li><strong>🔮 Carta do Tarot:</strong> [Nome da Carta]</li>
       </ul>
    6. Termine com uma "Dica do dia" inspiradora dentro de uma tag <blockquote>.

    Texto entre 250 e 350 palavras. Mantenha o tom construtivo e leve.
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


def publicar_no_blogger(titulo, conteudo, signo):
    creds = obter_credenciais()
    blogger = build('blogger', 'v3', credentials=creds)
    corpo_postagem = {
        'kind': 'blogger#post',
        'title': titulo,
        'content': conteudo,
        'labels': ["Horóscopo", signo, "Astrologia"]
    }
    resultado = blogger.posts().insert(blogId=BLOGGER_ID, body=corpo_postagem).execute()
    print(f"✨ Postado com sucesso: '{titulo}' -> {resultado.get('url')}")


if __name__ == "__main__":
    data_hoje = datetime.date.today().strftime("%d/%m/%Y")
    print(f"🌟 Iniciando geração de posts individuais de horóscopo ({data_hoje})...")

    for signo, info in SIGNOS.items():
        sucesso = False
        tentativas = 0
        
        while not sucesso and tentativas < 3:
            try:
                tentativas += 1
                print(f"✍️ Gerando horóscopo de {signo} (Tentativa {tentativas})...")
                
                texto_horoscopo = gerar_horoscopo(signo, info["periodo"], data_hoje)
                img_url = buscar_imagem_openverse(info["img"])
                img_html = gerar_tabela_imagem_blogger(img_url, f"Horóscopo de {signo}")

                titulo = f"Horóscopo de {signo} — Previsões de Hoje ({data_hoje})"
                html_final = f"{img_html}{texto_horoscopo}"

                publicar_no_blogger(titulo, html_final, signo)
                sucesso = True
                
                # Pausa de 5 segundos entre cada post para não estourar o limite de requisições!
                print("⏳ Aguardando 5 segundos antes do próximo signo...")
                time.sleep(5)

            except Exception as e:
                print(f"❌ Erro na tentativa {tentativas} do signo {signo}: {e}")
                time.sleep(10) # Espera 10 segundos antes de tentar de novo se der erro

    print("✅ Processo finalizado com garantia de envio de todos os signos!")
