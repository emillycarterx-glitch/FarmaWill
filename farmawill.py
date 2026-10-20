import telebot
import base64
import os
import edge_tts
import asyncio
from google import genai
from google.genai import types

# 1. CHAVES E CONFIGURAÇÕES
TELEGRAM_TOKEN = "8710361844:AAEmxd-8WYAmO410jJvLLs5ePfTWTDRS_ew"
GEMINI_API_KEY = "AIzaSyBrbElh7TqTAiAi23G2kU7j-6cR7r0jCO8"

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = genai.Client(api_key=GEMINI_API_KEY)

# 2. SISTEMA DE FALA NEURAL (Vozes Premium Microsoft)
def gerar_audio_resposta(texto, nome_arquivo="resposta.ogg"):
    """Transforma o texto num arquivo de áudio usando voz neural realista."""
    try:
        # Você pode trocar para "pt-BR-FranciscaNeural" se quiser uma voz feminina
        voz = "pt-BR-AntonioNeural" 
        comunicar = edge_tts.Communicate(texto, voz)
        asyncio.run(comunicar.save(nome_arquivo))
        return True
    except Exception as e:
        print(f"Erro ao gerar áudio neural: {e}")
        return False

# 3. CARREGAR O LIVRÃO PARA A MEMÓRIA (Só roda 1 vez ao ligar)
CAMINHO_BULARIO = "bulario_completo.pdf"
ARQUIVO_BULARIO_GEMINI = None

if os.path.exists(CAMINHO_BULARIO):
    print("A enviar o Bulário Gigante para o cérebro do Gemini (isso pode demorar uns minutos dependendo do tamanho do PDF)...")
    ARQUIVO_BULARIO_GEMINI = client.files.upload(file=CAMINHO_BULARIO)
    print("Bulário carregado com sucesso! FarmaWill agora sabe tudo.")
else:
    print(f"AVISO CRÍTICO: O arquivo {CAMINHO_BULARIO} não foi encontrado na pasta. Ele vai responder sem a base oficial.")

# 4. O CÉREBRO DO FARMAWILL
@bot.message_handler(content_types=['text', 'voice'])
def responder_mensagem(mensagem):
    try:
        texto_usuario = ""
        # Mostra o status "Gravando áudio..." lá no Telegram para a mãe ver
        bot.send_chat_action(mensagem.chat.id, 'record_voice')

        conteudos_para_ia = []
        
        # Se a mãe enviar ÁUDIO
        if mensagem.content_type == 'voice':
            file_info = bot.get_file(mensagem.voice.file_id)
            audio_bytes = bot.download_file(file_info.file_path)
            
            # Injeta o áudio da mãe cru para a IA
            audio_part = types.Part.from_bytes(data=audio_bytes, mime_type='audio/ogg')
            conteudos_para_ia.append(audio_part)
            
            # Apenas para mostrar no teu terminal o que ele ouviu
            resposta_transcricao = client.models.generate_content(
                model='gemini-3.5-flash-lite',
                contents=[audio_part, "Transcreva exatamente o que foi dito neste áudio."]
            )
            texto_usuario = resposta_transcricao.text.strip()

        # Se a mãe enviar TEXTO
        elif mensagem.content_type == 'text':
            texto_usuario = mensagem.text
            if texto_usuario == "/start":
                bot.send_message(mensagem.chat.id, "Olá! Sou o FarmaWill. Pode me mandar um áudio perguntando sobre a dose do remédio do seu bebê.")
                return
            conteudos_para_ia.append(texto_usuario)

        print(f"Mãe perguntou: {texto_usuario}")

        # Adiciona o Livrão Gigante na memória do raciocínio
        if ARQUIVO_BULARIO_GEMINI:
            conteudos_para_ia.append(ARQUIVO_BULARIO_GEMINI)

        prompt_farmaceutico = f"""
        Você é o FarmaWill, um assistente farmacêutico virtual desenhado para ser acessado por voz.
        A sua resposta será transformada num áudio falado por um sintetizador de voz.
        REGRA 1: Responda em tom de conversa, de forma direta, fluida, calma e super acolhedora.
        REGRA 2: NUNCA use formatações visuais como asteriscos, negritos, emojis ou listas com pontinhos. Escreva como se fosse um roteiro de rádio.
        REGRA 3: Baseie a sua resposta matemática e posológica estritamente no documento PDF do bulário anexado.
        Dúvida da mãe: '{texto_usuario}'
        """
        conteudos_para_ia.append(prompt_farmaceutico)

        print("A calcular a dose e preparar a resposta baseada no Bulário...")
        resposta_final_ia = client.models.generate_content(
            model='gemini-3.5-flash-lite',
            contents=conteudos_para_ia
        )
        
        texto_farmawill = resposta_final_ia.text
        print(f"FarmaWill Roteiro: {texto_farmawill}")

        # TIRA A RESPOSTA DA BOCA DO FARMAWILL PARA O TELEGRAM
        nome_arquivo_resposta = "resposta_farmawill.ogg"
        if gerar_audio_resposta(texto_farmawill, nome_arquivo_resposta):
            with open(nome_arquivo_resposta, 'rb') as audio_file:
                bot.send_voice(mensagem.chat.id, audio_file)
        else:
             bot.send_message(mensagem.chat.id, "Desculpe, tive um problema na voz. " + texto_farmawill)

    except Exception as e:
        print(f"ERRO: {e}")
        bot.send_message(mensagem.chat.id, "Desculpe, ocorreu um erro técnico e não consegui gerar a resposta.")

print("FarmaWill está online com o Bulário Gigante e Voz Sintética ativados!")
bot.polling(none_stop=True, timeout=90, long_polling_timeout=90)