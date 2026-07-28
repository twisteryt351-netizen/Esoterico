import os
import json
import base64
import requests
import datetime
import time
import traceback
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

# --- GERACAO DE IMAGENS COM IA (Cloudflare Worker) ---
# O simbolo de cada signo nao muda dia a dia (so a previsao muda), entao a imagem de
# cada signo e gerada UMA UNICA VEZ via IA e reaproveitada nas rodadas seguintes,
# usando um cache em JSON commitado no repositorio.
CLOUDFLARE_WORKER_URL = os.environ.get("CLOUDFLARE_WORKER_URL")
CLOUDFLARE_API_KEY = "0001"
IMGBB_API_KEY = os.environ.get("IMGBB_API_KEY")
CACHE_IMAGENS_SIGNOS = "imagens_signos.json"

# --- OS 12 SIGNOS COM PALAVRAS-CHAVE ---
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
    """Busca uma imagem gratuita e sem direitos autorais no Openverse."""
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


def _endpoint_cloudflare():
    if not CLOUDFLARE_WORKER_URL:
        return None
    return f"{CLOUDFLARE_WORKER_URL.rstrip('/')}/v1/images/generations"


def gerar_imagem_cloudflare(prompt, ratio="1:1"):
    """Gera uma imagem via Cloudflare Worker. Retorna bytes PNG ou None se falhar."""
    endpoint = _endpoint_cloudflare()
    if not endpoint:
        return None
    try:
        resposta = requests.post(
            endpoint,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {CLOUDFLARE_API_KEY}",
            },
            json={"prompt": prompt, "ratio": ratio},
            timeout=60,
        )
        resposta.raise_for_status()
        dados = resposta.json()
        b64 = dados["data"][0]["b64_json"]
        return base64.b64decode(b64)
    except Exception as e:
        print(f"⚠️ Cloudflare Worker falhou para o prompt '{prompt[:40]}...': {e}")
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


def gerar_imagem_ia(prompt, ratio="1:1"):
    """Pipeline completo: gera a imagem no Cloudflare Worker e hospeda no imgbb. Retorna URL ou None."""
    imagem_bytes = gerar_imagem_cloudflare(prompt, ratio)
    if not imagem_bytes:
        return None
    return hospedar_imagem(imagem_bytes)


def carregar_cache_imagens_signos():
    if not os.path.exists(CACHE_IMAGENS_SIGNOS):
        return {}
    try:
        with open(CACHE_IMAGENS_SIGNOS, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Nao foi possivel ler o cache de imagens dos signos: {e}")
        return {}


def salvar_cache_imagens_signos(cache):
    with open(CACHE_IMAGENS_SIGNOS, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def montar_prompt_imagem_signo(palavra_chave_signo):
    """Prompt deterministico (sem chamar a IA de texto) para a arte do simbolo do signo."""
    return (
        f"A beautiful mystical illustration of the {palavra_chave_signo}, elegant zodiac "
        f"constellation art, deep cosmic night sky background with stars and nebula, gold "
        f"and deep purple color palette, symmetrical composition, ethereal glowing lines, "
        f"high detail digital art, no text, no watermark"
    )


def obter_imagem_signo(signo, palavra_chave, cache):
    """Retorna (url, cache_mudou). Usa o cache se ja existir imagem gerada para o signo;
    caso contrario tenta gerar via IA (Cloudflare Worker + imgbb) e salva no cache. Se a IA
    falhar, cai no Openverse SEM salvar no cache, para tentar a IA novamente no proximo dia."""
    if cache.get(signo):
        return cache[signo], False

    if CLOUDFLARE_WORKER_URL and IMGBB_API_KEY:
        prompt = montar_prompt_imagem_signo(palavra_chave)
        url = gerar_imagem_ia(prompt, ratio="1:1")
        if url:
            cache[signo] = url
            return url, True
        print(f"⚠️ Geracao de imagem via IA falhou para {signo}, usando Openverse desta vez.")

    return buscar_imagem_openverse(palavra_chave), False


def gerar_tabela_imagem_blogger(url_img, alt_title):
    return f'''<table align="center" cellpadding="0" cellspacing="0" class="tr-caption-container" style="margin-left: auto; margin-right: auto; text-align: center;"><tbody><tr><td><img alt="{alt_title}" border="0" height="250" src="{url_img}" title="{alt_title}" style="max-width: 100%; height: auto; border-radius: 8px;" /></td></tr></tbody></table><br />'''


def pedir_ia_groq(prompt, temperatura=0.7):
    """Chamada direta à Groq sem tratamento de erro."""
    response = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model=MODELO_IA,
        temperature=temperatura,
    )
    return response.choices[0].message.content.strip()


def pedir_ia_groq_com_retry(prompt, max_retries=5, base_delay=2):
    """
    Tenta chamar a Groq com retry exponencial e verifica se a resposta é válida.
    Levanta exceção se falhar após todas as tentativas.
    """
    for tentativa in range(max_retries):
        try:
            print(f"   [IA] Tentativa {tentativa+1}/{max_retries}...")
            resposta = pedir_ia_groq(prompt)
            # Verifica se a resposta é razoável (pelo menos 50 caracteres)
            if len(resposta) < 50:
                raise ValueError(f"Resposta muito curta ({len(resposta)} caracteres).")
            # Verifica se contém as tags esperadas (pelo menos <p> ou <h3>)
            if "<p>" not in resposta and "<h3>" not in resposta:
                raise ValueError("Resposta não parece conter HTML válido.")
            return resposta
        except Exception as e:
            print(f"   ⚠️ Falha na tentativa {tentativa+1}: {e}")
            if tentativa == max_retries - 1:
                raise  # Falhou todas as tentativas
            # Espera exponencial com jitter
            sleep_time = base_delay * (2 ** tentativa) + (tentativa * 0.5)
            print(f"   ⏳ Aguardando {sleep_time:.1f}s antes de tentar novamente...")
            time.sleep(sleep_time)
    raise RuntimeError("Nunca deveria chegar aqui.")


def gerar_introducao(data_hoje):
    """Gera um parágrafo introdutório sobre o panorama astral do dia."""
    prompt = f"""
    Como um astrólogo profissional, escreva uma introdução cativante, mística e inspiradora sobre o clima astral de hoje ({data_hoje}). 
    Fale sobre as energias gerais, posição da Lua e o tom para o dia. 
    Apenas responda em HTML puro usando a tag <p>, com 3 a 4 frases sem títulos.
    """
    return pedir_ia_groq_com_retry(prompt)


def gerar_horoscopo_signo(signo, periodo):
    """Gera a previsão individual do signo com detalhes extras."""
    prompt = f"""
    Você é um astrólogo carismático. Escreva a previsão diária para {signo} ({periodo}) em português do Brasil.

    REGRAS DE FORMATO (HTML puro, sem Markdown ou tags <html>/<body>):
    1. Um parágrafo <p> curto sobre o clima do dia para o signo.
    2. Subtítulo <h3> Amor</h3> + parágrafo curto.
    3. Subtítulo <h3> Trabalho & Finanças</h3> + parágrafo curto.
    4. Um bloco <ul> com <li><strong>Cor do Dia:</strong> [Cor]</li>, <li><strong>Número da Sorte:</strong> [Número]</li> e <li><strong>Carta do Tarot:</strong> [Carta]</li>.
    5. Termine com uma "Dica do dia" curta dentro de uma tag <blockquote>.

    Seja envolvente, otimista e construtivo. Não inclua o nome do signo em <h1> ou <h2> (isso será inserido externamente).
    """
    return pedir_ia_groq_com_retry(prompt)


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
        'labels': ["Horóscopo", "Signos", "Astrologia"]
    }
    resultado = blogger.posts().insert(blogId=BLOGGER_ID, body=corpo_postagem).execute()
    print(f"\n✨ POST COMPLETO PUBLICADO COM SUCESSO!\n🔗 Link: {resultado.get('url')}")
    return resultado


if __name__ == "__main__":
    data_hoje = datetime.date.today().strftime("%d/%m/%Y")
    print(f"🌟 Iniciando geração do Portal de Horóscopo ({data_hoje})...")
    
    # 1. Título e Introdução
    titulo_post = f"Horóscopo do Dia: Previsões para Todos os Signos - {data_hoje}"
    
    print("🔮 Criando panorama astral do dia...")
    try:
        intro_html = gerar_introducao(data_hoje)
    except Exception as e:
        print(f"❌ Falha ao gerar introdução: {e}")
        intro_html = "<p>Hoje o céu nos convida a refletir e a nos conectar com nossas emoções. As estrelas sugerem um dia de introspecção e oportunidades para crescimento pessoal.</p>"
    
    html_final = f"<h2>✨ Clima Astral de Hoje ({data_hoje})</h2>"
    html_final += intro_html
    html_final += "<hr style='border: 0; height: 1px; background: #ddd; margin: 20px 0;' />"

    # 2. Dicionário para armazenar os conteúdos de cada signo (caso precise repetir)
    conteudos_signos = {}
    signos_processados = 0
    falhas = []
    cache_imagens_signos = carregar_cache_imagens_signos()
    cache_mudou = False

    # Processar cada signo
    for signo, info in SIGNOS.items():
        print(f"✍️ Processando {signo}...")
        for tentativa in range(2):  # no máximo 2 tentativas por signo (a segunda é repetição)
            try:
                if tentativa == 0:
                    texto_signo = gerar_horoscopo_signo(signo, info["periodo"])
                else:
                    print(f"   🔁 Re-tentando {signo} (tentativa 2)...")
                    texto_signo = gerar_horoscopo_signo(signo, info["periodo"])
                
                # Verifica conteúdo
                if len(texto_signo) < 100:
                    raise ValueError("Conteúdo muito curto.")
                
                # Buscar imagem (gerada uma unica vez via IA e reaproveitada do cache)
                img_url, imagem_nova = obter_imagem_signo(signo, info["img"], cache_imagens_signos)
                if imagem_nova:
                    cache_mudou = True
                img_html = gerar_tabela_imagem_blogger(img_url, f"Signo de {signo}")

                # Monta o bloco do signo
                bloco = f"<h2 style='color: #4a2c82;'>✨ {signo} <small>({info['periodo']})</small></h2>"
                bloco += img_html
                bloco += texto_signo
                bloco += "<br/><hr style='border: 0; height: 1px; background: #eee; margin: 30px 0;' />"
                
                # Salva no dicionário
                conteudos_signos[signo] = bloco
                signos_processados += 1
                print(f"   ✅ {signo} processado com sucesso.")
                break  # sai do loop de tentativas
            except Exception as e:
                print(f"   ❌ Erro ao processar {signo} (tentativa {tentativa+1}): {e}")
                if tentativa == 1:  # já é a segunda tentativa
                    falhas.append(signo)
                    # Conteúdo de fallback para não deixar o signo de fora
                    fallback = f"""
                    <h2 style='color: #4a2c82;'>✨ {signo} <small>({info['periodo']})</small></h2>
                    <p>As estrelas hoje sugerem um dia de equilíbrio e harmonia para {signo}. Procure ouvir sua intuição e confiar no processo.</p>
                    <h3>Amor</h3><p>O amor está no ar, mas é importante manter a calma e a paciência.</p>
                    <h3>Trabalho & Finanças</h3><p>Oportunidades podem surgir, esteja atento.</p>
                    <ul><li><strong>Cor do Dia:</strong> Dourado</li><li><strong>Número da Sorte:</strong> 7</li><li><strong>Carta do Tarot:</strong> A Estrela</li></ul>
                    <blockquote>Confie no fluxo da vida.</blockquote>
                    <br/><hr style='border: 0; height: 1px; background: #eee; margin: 30px 0;' />
                    """
                    conteudos_signos[signo] = fallback
                    print(f"   ⚠️ Fallback aplicado para {signo}.")
                else:
                    # Primeira tentativa falhou, aguarda um pouco antes da segunda
                    time.sleep(5)
        
        # Delay entre signos para não sobrecarregar a API
        time.sleep(1.5)

    # Salva o cache de imagens dos signos (se alguma imagem nova foi gerada via IA)
    if cache_mudou:
        try:
            salvar_cache_imagens_signos(cache_imagens_signos)
            print("💾 Cache de imagens dos signos atualizado.")
        except Exception as e:
            print(f"⚠️ Falha ao salvar cache de imagens dos signos: {e}")

    # Adiciona todos os blocos ao HTML final na ordem correta
    for signo in SIGNOS.keys():
        if signo in conteudos_signos:
            html_final += conteudos_signos[signo]
        else:
            # Caso extremo: se algum signo não estiver no dicionário, adiciona um placeholder
            info = SIGNOS[signo]
            html_final += f"<h2 style='color: #4a2c82;'>✨ {signo} <small>({info['periodo']})</small></h2>"
            html_final += "<p>Previsão não disponível no momento. Volte mais tarde!</p><hr/>"

    # Estatísticas
    print(f"\n📊 Resumo: {signos_processados} signos processados com sucesso de {len(SIGNOS)}.")
    if falhas:
        print(f"⚠️ Signos que usaram fallback: {', '.join(falhas)}")
    else:
        print("🎉 Todos os signos foram gerados com sucesso!")

    # Salvar HTML local para depuração
    with open("horoscopo_completo.html", "w", encoding="utf-8") as f:
        f.write(html_final)
    print("📄 HTML salvo em 'horoscopo_completo.html' para verificação.")

    # 3. Publicar no Blogger
    print("🚀 Enviando artigo completo para o Blogger...")
    try:
        publicar_no_blogger(titulo_post, html_final)
        print("✅ Processo finalizado com sucesso!")
    except Exception as e:
        print(f"❌ Falha ao publicar no Blogger: {e}")
        traceback.print_exc()
        # Não encerra com erro, para podermos ver o HTML salvo.
        print("⚠️ O HTML foi salvo localmente, você pode publicar manualmente.")
