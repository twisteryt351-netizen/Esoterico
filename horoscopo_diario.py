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
    - Retorne APENAS HTML limpo, sem Markdown e sem a palavra ```html.
    """
    return pedir_ia_groq(prompt, max_tokens=600)


def gerar_horoscopo_signo(signo, periodo, data_hoje):
    prompt = f"""
    Você é um astrólogo carismático e profundo. Escreva uma previsão DIÁRIA EXTENSA, COMPLETA E DETALHADA para o signo de {signo} ({periodo}) referente a {data_hoje}.

    O leitor quer ler um texto completo e individualizado sobre o seu signo! Não faça resumos curtos.

    REGRAS DE FORMATO (HTML Puro):
    1. <p style="font-size: 15px; line-height: 1.6; color: #333;">Escreva um parágrafo longo e profundo (de 4 a 5 frases) sobre o panorama geral do signo no dia de hoje.</p>
    
    2. <h3 style="color: #6a1b9a; margin-top: 15px; font-size: 18px;">💖 Amor e Relacionamentos</h3>
       <p style="font-size: 15px; line-height: 1.6; color: #555;">Escreva um parágrafo detalhado abordando solteiros e comprometidos deste signo hoje.</p>
       
    3. <h3 style="color: #6a1b9a; margin-top: 15px; font-size: 18px;">💼 Trabalho e Finanças</h3>
       <p style="font-size: 15px; line-height: 1.6; color: #555;">Escreva um parágrafo focado na carreira, decisões financeiras e oportunidades profissionais.</p>
       
    4. <h3 style="color: #6a1b9a; margin-top: 15px; font-size: 18px;">🌿 Saúde e Vitalidade</h3>
       <p style="font-size: 15px; line-height: 1.6; color: #555;">Escreva orientações sobre energia física, saúde mental e bem-estar para o dia.</p>
       
    5. <div style="background-color: #f3e5f5; border-left: 4px solid #8e24aa; padding: 12px 15px; margin: 15px 0; border-radius: 0 8px 8px 0;">
         <ul style="list-style: none; padding: 0; margin: 0; font-size: 14px; color: #4a148c;">
           <li style="margin-bottom: 5px;"><strong>🎨 Cor do Dia:</strong> [Nome da Cor]</li>
           <li style="margin-bottom: 5px;"><strong>🔢 Número da Sorte:</strong> [Número]</li>
           <li><strong>🔮 Carta do Tarot:</strong> [Nome da Carta do Tarot]</li>
         </ul>
       </div>
       
    6. <blockquote style="background: #fafafa; border-left: 4px solid #ab47bc; margin: 15px 0; padding: 10px 15px; font-style: italic; color: #666;">
         "Frase/Dica de sabedoria inspiradora para o dia de {signo}"
       </blockquote>

    NÃO inclua o nome do signo em H1 ou H2 (ele é colocado externamente).
    Retorne SOMENTE código HTML válido.
    """
    return pedir_ia_groq(prompt, max_tokens=1000)


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
    print(f"\n✨ POST COMPLETO E DETALHADO PUBLICADO!\n🔗 Link: {resultado.get('url')}")


if __name__ == "__main__":
    data_hoje = datetime.date.today().strftime("%d/%m/%Y")
    print(f"🌟 Gerando Portal Completo de Horóscopo com Conteúdo Extenso ({data_hoje})...")

    titulo_post = f"Horóscopo do Dia: Previsões Aprofundadas para Todos os Signos — {data_hoje}"

    html_final = f'''
    <div style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; max-width: 800px; margin: 0 auto; color: #333;">
        <div style="background: linear-gradient(135deg, #4a148c, #7b1fa2); color: #fff; padding: 25px; border-radius: 12px; text-align: center; margin-bottom: 25px;">
            <h1 style="margin: 0; font-size: 26px; color: #ffffff;">✨ Clima Astral de Hoje ({data_hoje})</h1>
        </div>
    '''
    
    print("🔮 Criando introdução geral...")
    html_final += gerar_introducao(data_hoje)
    html_final += '<hr style="border: 0; height: 1px; background: #e0e0e0; margin: 30px 0;" />'

    # Loop para garantir a análise individual de TODOS os 12 signos
    for signo, info in SIGNOS.items():
        sucesso = False
        tentativas = 0
        
        while not sucesso and tentativas < 3:
            try:
                tentativas += 1
                print(f"✍️ Gerando análise extensa para {signo}...")
                
                texto_signo = gerar_horoscopo_signo(signo, info["periodo"], data_hoje)
                img_url = buscar_imagem_openverse(info["img"])
                img_html = gerar_tabela_imagem_blogger(img_url, f"Signo de {signo}")

                # Card exclusivo do signo
                html_final += f'''
                <div style="background: #ffffff; border: 1px solid #ede7f6; border-radius: 12px; padding: 22px; margin-bottom: 35px; box-shadow: 0 4px 12px rgba(0,0,0,0.06);">
                    <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid #ba68c8; padding-bottom: 10px; margin-bottom: 18px;">
                        <h2 style="margin: 0; color: #4a148c; font-size: 24px;">✨ {signo}</h2>
                        <span style="font-size: 13px; background: #f3e5f5; color: #7b1fa2; padding: 5px 12px; border-radius: 20px; font-weight: bold;">{info['periodo']}</span>
                    </div>
                    {img_html}
                    {texto_signo}
                </div>
                '''
                
                sucesso = True
                time.sleep(2)
            except Exception as e:
                print(f"⚠️ Erro ao gerar {signo}: {e}")
                time.sleep(4)

    html_final += "</div>"

    print("\n🚀 Publicando post completo de todos os signos no Blogger...")
    publicar_no_blogger(titulo_post, html_final)
    print("✅ Processo finalizado com sucesso!")
