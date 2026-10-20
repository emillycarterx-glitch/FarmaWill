import telebot
import base64
import os
import edge_tts
import asyncio
import threading
from flask import Flask
from google import genai
from google.genai import types

# 1. CHAVES E CONFIGURAÇÕES
TELEGRAM_TOKEN = "8710361844:AAEmxd-8WYAmO410jJvLLs5ePfTWTDRS_ew"
GEMINI_API_KEY = "AIzaSyBrbElh7TqTAiAi23G2kU7j-6cR7r0jCO8"

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = genai.Client(api_key=GEMINI_API_KEY)

# 2. O SERVIDOR FANTASMA (Para enganar o Render e ficar Free)
app = Flask(__name__)

@app.route('/')
def home():
    return "FarmaWill está online e operando na nuvem!"

def manter_servidor_online():
    porta = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=porta)

# 3. SISTEMA DE FALA NEURAL
def gerar_audio_resposta(texto, nome_arquivo="resposta.ogg"):
    try:
        voz = "pt-BR-AntonioNeural"
        comunicar = edge_tts.Communicate(texto, voz)
        asyncio.run(comunicar.save(nome_arquivo))
        return True
    except Exception as e:
        print(f"Erro áudio: {e}")
        return False

# 4. CARREGAR O LIVRÃO PARA A MEMÓRIA
CAMINHO_BULARIO = "bulario_completo.pdf"
ARQUIVO_BULARIO_GEMINI = None

if os.path.exists(CAMINHO_BULARIO):
    print("Enviando o Bulário Gigante para o Gemini...")
    ARQUIVO_BULARIO_GEMINI = client.files.upload(file=CAMINHO_BULARIO)
else:
    print("Aviso: Bulário não encontrado.")

# 5. O CÉREBRO DO FARMAWILL
@bot.message_handler(content_types=['text', 'voice'])
def responder_mensagem(mensagem):
    try:
        texto_usuario = ""
        bot.send_chat_action(mensagem.chat.id, 'record_voice')

        conteudos_para_ia = []
        
        if mensagem.content_type == 'voice':
            file_info = bot.get_file(mensagem.voice.file_id)
            audio_bytes = bot.download_file(file_info.file_path)
            
            audio_part = types.Part.from_bytes(data=audio_bytes, mime_type='audio/ogg')
            conteudos_para_ia.append(audio_part)
            
            resposta_transcricao = client.models.generate_content(
                model='gemini-3.5-flash',
                contents=[audio_part, "Transcreva exatamente o que foi dito neste áudio."]
            )
            texto_usuario = resposta_transcricao.text.strip()

        elif mensagem.content_type == 'text':
            texto_usuario = mensagem.text
            if texto_usuario == "/start":
                bot.send_message(mensagem.chat.id, "Olá! Sou o FarmaWill. Mande seu áudio.")
                return
            conteudos_para_ia.append(texto_usuario)

        if ARQUIVO_BULARIO_GEMINI:
            conteudos_para_ia.append(ARQUIVO_BULARIO_GEMINI)

        prompt = f"""
        Você é o FarmaWill, um assistente farmacêutico virtual.
        Sua resposta será lida por um sintetizador de voz.
        Responda em tom de conversa, direta, fluida, calma e acolhedora.
        NUNCA use asteriscos, emojis ou listas. Escreva como um roteiro de rádio.
        Baseie-se na bula em PDF anexada.
        Dúvida da mãe: '{texto_usuario}'
        """
        conteudos_para_ia.append(prompt)

        resposta_final_ia = client.models.generate_content(
            model='gemini-3.5-flash',
            contents=conteudos_para_ia
        )
        texto_farmawill = resposta_final_ia.text

        nome_arquivo = "resposta_farmawill.ogg"
        if gerar_audio_resposta(texto_farmawill, nome_arquivo):
            with open(nome_arquivo, 'rb') as audio_file:
                bot.send_voice(mensagem.chat.id, audio_file)
        else:
             bot.send_message(mensagem.chat.id, texto_farmawill)

    except Exception as e:
        bot.send_message(mensagem.chat.id, "Ocorreu um erro técnico.")

# LIGA TUDO: O site fantasma e o robô
print("Iniciando o Servidor Fantasma e o Telegram...")
threading.Thread(target=manter_servidor_online, daemon=True).start()
bot.polling(none_stop=True, timeout=90, long_polling_timeout=90)
