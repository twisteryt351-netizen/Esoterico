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

# --- OS 12 SIGNOS E SUAS PALAVRAS-CHAVE ---
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
    """Busca uma imagem gratuita e temática no Openverse."""
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
    return f'''<table align="center" cellpadding="0" cellspacing="0" class="tr-caption-container" style="margin-left: auto; margin-right: auto; text-align: center;"><tbody><tr><td><img alt="{alt_title}" border="0" height="250" src="{url_img}" title="{alt_title}" style="max-width: 100%; height: auto; border-radius: 8px;" /></td></tr></tbody></table><br />'''


def pedir_ia_groq(prompt, temperatura=0.7):
    response = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model=MODELO_IA,
        temperature=temperatura,
    )
    return response.choices[0].message.content.strip()


def gerar_introducao(data_hoje):
    """Gera o texto de abertura místico sobre o panorama astral do dia."""
    prompt = f"""
    Como um astrólogo profissional e carismático, escreva uma introdução cativante, mística e inspiradora sobre o clima astral de hoje ({data_hoje}). 
    Fale sobre as energias gerais, posição da Lua e o tom para o dia. 
    Apenas responda em HTML puro usando a tag <p>, com 3 a 4 frases, sem títulos.
    """
    return pedir_ia_groq(prompt)


def gerar_horoscopo_signo(signo, periodo):
    """Gera a previsão individual do signo com blocos detalhados."""
    prompt = f"""
    Você é um astrólogo experiente. Escreva a previsão diária para o signo de {signo} ({periodo}) em português do Brasil.

    REGRAS DE FORMATO (HTML puro, sem Markdown ou tags <html>/<body>):
    1. Um parágrafo <p> introdutório sobre o tom geral do dia.
    2. Subtítulo <h3>💖 Amor</h3> + parágrafo curto.
    3. Subtítulo <h3>💼 Trabalho & Finanças</h3> + parágrafo curto.
    4. Subtítulo <h3>🌿 Saúde</h3> + parágrafo curto.
    5. Um bloco <ul> com:
       - <li><strong>🎨 Cor do Dia:</strong> [Nome da Cor]</li>
       - <li><strong>🔢 Número da Sorte:</strong> [Número]</li>
       - <li><strong>🔮 Carta do Tarot:</strong> [Carta]</li>
    6. Termine com uma "Dica Astral" curta dentro de uma tag <blockquote>.

    Seja motivador e envolvente. Não inclua o nome do signo no início como H1 ou H2, pois ele será inserido pela estrutura do script.
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
        'content': conteudo,
        'labels': ["Horóscopo", "Signos", "Astrologia", "Previsão Diária"]
    }
    resultado = blogger.posts().insert(blogId=BLOGGER_ID, body=corpo_postagem).execute()
    print(f"\n✨ POST COMPLETO PUBLICADO COM SUCESSO!\n🔗 Link: {resultado.get('url')}")


if __name__ == "__main__":
    data_hoje = datetime.date.today().strftime("%d/%m/%Y")
    print(f"🌟 Iniciando geração do Guia Completo de Horóscopo ({data_hoje})...")

    # 1. Título do Artigo Único
    titulo_post = f"Horóscopo do Dia: Previsões Aprofundadas para Todos os Signos — {data_hoje}"

    print("🔮 Criando introdução sobre o clima astral do dia...")
    html_final = f"<h2 style='color: #4a2c82;'>✨ Clima Astral de Hoje ({data_hoje})</h2>"
    html_final += gerar_introducao(data_hoje)
    html_final += "<hr style='border: 0; height: 1px; background: #ddd; margin: 25px 0;' />"

    # 2. Compilar os 12 Signos
    for signo, info in SIGNOS.items():
        sucesso = False
        tentativas = 0
        
        while not sucesso and tentativas < 3:
            try:
                tentativas += 1
                print(f"✍️ Compilando previsões para {signo}...")
                
                texto_signo = gerar_horoscopo_signo(signo, info["periodo"])
                img_url = buscar_imagem_openverse(info["img"])
                img_html = gerar_tabela_imagem_blogger(img_url, f"Signo de {signo}")

                # Estrutura chique para cada signo no artigo
                html_final += f"<h2 style='color: #4a2c82; border-bottom: 2px solid #6b3ba7; padding-bottom: 5px;'>✨ {signo} <small style='font-size: 14px; color: #666;'>({info['periodo']})</small></h2>"
                html_final += img_html
                html_final += texto_signo
                html_final += "<br/><hr style='border: 0; height: 1px; background: #eee; margin: 30px 0;' />"
                
                sucesso = True
                time.sleep(2)  # Pausa leve de cortesia entre chamadas da IA
            except Exception as e:
                print(f"⚠️ Erro ao gerar {signo} (tentativa {tentativas}): {e}")
                time.sleep(5)

    # 3. Publicação Única no Blogger
    print("\n🚀 Enviando o guia completo dos 12 signos para o Blogger...")
    publicar_no_blogger(titulo_post, html_final)
    print("✅ Processo concluído com sucesso!")
