import os
import re
import time
import requests
import datetime
from groq import Groq
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# --- CONFIGURAÇÕES ---
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

# --- OS 12 SIGNOS ---
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


def limpar_resposta_html(texto):
    """Limpa a resposta da IA para garantir renderização perfeita do HTML no Blogger."""
    texto = re.sub(r"^```html\s*", "", texto, flags=re.MULTILINE)
    texto = re.sub(r"^```\s*", "", texto, flags=re.MULTILINE)
    texto = re.sub(r"```$", "", texto, flags=re.MULTILINE)
    return texto.strip()


def buscar_imagem_openverse(palavra_chave):
    try:
        resposta = requests.get(
            "[https://api.openverse.org/v1/images/](https://api.openverse.org/v1/images/)",
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
    return f'''
    <div style="text-align: center; margin: 15px 0;">
        <img alt="{alt_title}" src="{url_img}" title="{alt_title}" style="max-width: 100%; height: auto; max-height: 280px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.15);" />
    </div>
    '''


def pedir_ia_groq(prompt, temperatura=0.7, max_tokens=1000):
    response = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model=MODELO_IA,
        temperature=temperatura,
        max_tokens=max_tokens
    )
    raw = response.choices[0].message.content
    return limpar_resposta_html(raw)


def gerar_introducao(data_hoje):
    prompt = f"""
    Como um astrólogo profissional e místico, escreva uma introdução completa e envolvente sobre o clima astral de hoje ({data_hoje}).
    
    Explicite os movimentos astrais gerais, a energia da Lua e as vibrações para a jornada do dia.
    
    REGRAS:
    - Escreva 2 parágrafos longos e bem explicados em tags <p style="font-size: 16px; line-height: 1.6; color: #444; margin-bottom: 12px;">.
    - Retorne APENAS HTML limpo, sem Markdown e sem a palavra
