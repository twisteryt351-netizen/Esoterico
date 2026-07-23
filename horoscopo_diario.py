import os
import re
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

def limpar_resposta_html(texto):
    """Remove marcações Markdown para garantir HTML limpo e renderizável."""
    texto = re.sub(r"^```html\s*", "", texto, flags=re.MULTILINE)
    texto = re.sub(r"^```\s*", "", texto, flags=re.MULTILINE)
    texto = re.sub(r"```$", "", texto, flags=re.MULTILINE)
    return texto.strip()

def gerar_portal_horoscopo_completo(data_hoje):
    """Gera o portal completo do dia com introdução e os 12 signos de uma só vez."""
    prompt = f"""
    Você é um astrólogo renomado e colunista de um grande portal místico. 
    Escreva o GUIA COMPLETO DO HORÓSCOPO DIÁRIO para TODOS OS 12 SIGNOS referente ao dia {data_hoje}.

    REGRAS DE FORMATAÇÃO (Retorne APENAS o HTML interno, sem tags <html> ou <body>):

    1. Crie uma introdução mística (2 parágrafos curtos) sobre as energias astrais do dia.
    
    2. Para CADA UM dos 12 signos (Áries, Touro, Gêmeos, Câncer, Leão, Virgem, Libra, Escorpião, Sagitário, Capricórnio, Aquário, Peixes), crie a estrutura exata abaixo:

       <div style="background: #ffffff; border: 1px solid #ede7f6; border-radius: 12px; padding: 20px; margin-bottom: 25px; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
         <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid #ba68c8; padding-bottom: 8px; margin-bottom: 15px;">
           <h2 style="margin: 0; color: #4a148c; font-size: 22px;">✨ [NOME DO SIGNO]</h2>
           <span style="font-size: 13px; background: #f3e5f5; color: #7b1fa2; padding: 4px 10px; border-radius: 20px; font-weight: bold;">[Período do Signo]</span>
         </div>
         
         <p style="font-size: 15px; line-height: 1.6; color: #333;">[Parágrafo com a visão geral do dia para o signo]</p>
         
         <h3 style="color: #6a1b9a; margin-top: 12px; font-size: 17px;">💖 Amor e Relacionamentos</h3>
         <p style="font-size: 14px; line-height: 1.5; color: #555;">[Previsão para o amor]</p>
         
         <h3 style="color: #6a1b9a; margin-top: 12px; font-size: 17px;">💼 Trabalho e Finanças</h3>
         <p style="font-size: 14px; line-height: 1.5; color: #555;">[Previsão para trabalho e finanças]</p>
         
         <div style="background-color: #f3e5f5; border-left: 4px solid #8e24aa; padding: 10px 15px; margin: 15px 0; border-radius: 0 8px 8px 0;">
           <ul style="list-style: none; padding: 0; margin: 0; font-size: 14px; color: #4a148c;">
             <li style="margin-bottom: 4px;"><strong>🎨 Cor do Dia:</strong> [Cor]</li>
             <li style="margin-bottom: 4px;"><strong>🔢 Número da Sorte:</strong> [Número]</li>
             <li><strong>🔮 Carta do Tarot:</strong> [Carta]</li>
           </ul>
         </div>
         
         <blockquote style="background: #fafafa; border-left: 4px solid #ab47bc; margin: 10px 0; padding: 8px 12px; font-style: italic; color: #666; font-size: 13px;">
           "[Dica Astral inspiradora do dia]"
         </blockquote>
       </div>

    Importante: Mantenha as respostas envolventes, ricas e bem escritas. Não resuma. Escreva sobre TODOS os 12 signos na ordem zodiacal.
    """
    
    response = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model=MODELO_IA,
        temperature=0.7,
        max_tokens=7000
    )
    
    raw = response.choices[0].message.content
    return limpar_resposta_html(raw)

def obter_credenciais():
    creds = Credentials(
        token=None,
        refresh_token=REFRESH_TOKEN,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        token_uri="[https://oauth2.googleapis.com/token](https://oauth2.googleapis.com/token)",
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
    print(f"\n✨ PORTAL COMPLETO PUBLICADO COM SUCESSO!\n🔗 Link: {resultado.get('url')}")

if __name__ == "__main__":
    data_hoje = datetime.date.today().strftime("%d/%m/%Y")
    print(f"🌟 Gerando Portal do Horóscopo Diário Completo ({data_hoje})...")

    titulo_post = f"Horóscopo do Dia: Previsões Aprofundadas para Todos os Signos — {data_hoje}"

    topo_html = f'''
    <div style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; max-width: 800px; margin: 0 auto; color: #333;">
        <div style="background: linear-gradient(135deg, #4a148c, #7b1fa2); color: #fff; padding: 25px; border-radius: 12px; text-align: center; margin-bottom: 25px;">
            <h1 style="margin: 0; font-size: 26px; color: #ffffff;">✨ Clima Astral de Hoje ({data_hoje})</h1>
        </div>
    '''

    conteudo_ia = gerar_portal_horoscopo_completo(data_hoje)
    html_final = topo_html + conteudo_ia + "</div>"

    print("🚀 Publicando o artigo completo no Blogger...")
    publicar_no_blogger(titulo_post, html_final)
    print("✅ Processo finalizado com sucesso!")
