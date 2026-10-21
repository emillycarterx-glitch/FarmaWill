import telebot
import base64
import os
import edge_tts
import asyncio
import threading
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai
from google.genai import types

# 1. CHAVES E CONFIGURAÇÕES
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = genai.Client(api_key=GEMINI_API_KEY)

app = Flask(__name__)
CORS(app) # Permite que o App acesse este servidor

@app.route('/')
def home():
    return "FarmaWill está online na nuvem!"

# 2. A PORTA SECRETA DO APLICATIVO
@app.route('/api/audio', methods=['POST'])
def api_audio():
    try:
        dados = request.json
        audio_b64 = dados.get('audioBase64')
        audio_bytes = base64.b64decode(audio_b64)
        
        audio_part = types.Part.from_bytes(data=audio_bytes, mime_type='audio/ogg')
        
        conteudos_para_ia = [audio_part, """
        Você é o FarmaWill, assistente farmacêutico.
        Responda à dúvida do áudio de forma acolhedora.
        Baseie-se no Bulário em PDF anexado (se houver).
        Escreva como um roteiro de rádio.
        No final, adicione OBRIGATORIAMENTE: [MED: Nome | HORAS: X]. Se não houver, [MED: Nenhum | HORAS: 0].
        """]
        
        global ARQUIVO_BULARIO_GEMINI
        if ARQUIVO_BULARIO_GEMINI:
            conteudos_para_ia.append(ARQUIVO_BULARIO_GEMINI)
            
        resposta_ia = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=conteudos_para_ia
        )
        texto_farmawill = resposta_ia.text
        
        # Extrai os dados do Alarme
        remedio, horas = "Medicação", 0
        padrao = r"\[MED:(.*?)\| HORAS:(.*?)\]"
        match = re.search(padrao, texto_farmawill)
        if match:
            remedio = match.group(1).strip()
            horas = int(match.group(2).strip())
            texto_farmawill = re.sub(padrao, "", texto_farmawill).strip()
            
        texto_farmawill = texto_farmawill.replace("*", "")
        
        # Gera o áudio com a voz Premium da Microsoft
        nome_arquivo = "resposta_app.mp3"
        voz = "pt-BR-AntonioNeural"
        comunicar = edge_tts.Communicate(texto_farmawill, voz)
        asyncio.run(comunicar.save(nome_arquivo))
        
        with open(nome_arquivo, "rb") as f:
            audio_gerado_b64 = base64.b64encode(f.read()).decode('utf-8')
            
        return jsonify({
            "remedio": remedio,
            "horas": horas,
            "audioBase64": audio_gerado_b64
        })
        
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

def manter_servidor_online():
    porta = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=porta)

# 3. CARREGAR O LIVRÃO PARA A MEMÓRIA
CAMINHO_BULARIO = "bulario_completo.pdf"
ARQUIVO_BULARIO_GEMINI = None
if os.path.exists(CAMINHO_BULARIO):
    print("Enviando o Bulário Gigante para o Gemini...")
    ARQUIVO_BULARIO_GEMINI = client.files.upload(file=CAMINHO_BULARIO)

# O CÉREBRO DO TELEGRAM CONTINUA AQUI INTACTO
@bot.message_handler(content_types=['text', 'voice'])
def responder_mensagem(mensagem):
    bot.send_message(mensagem.chat.id, "Estou processando pelo aplicativo agora!")

threading.Thread(target=manter_servidor_online, daemon=True).start()
bot.polling(none_stop=True, timeout=90, long_polling_timeout=90)
