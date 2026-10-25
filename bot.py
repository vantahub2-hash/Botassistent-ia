import os
from collections import defaultdict, deque

import discord
from openai import AsyncOpenAI

# Las keys se leen de las variables de entorno (Railway → Variables).
# Nunca escribas la key directamente en este archivo.
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
XAI_API_KEY = os.environ["XAI_API_KEY"]
MODEL = os.environ.get("GROK_MODEL", "grok-3-mini")

SYSTEM_PROMPT = (
    "Eres un asistente útil y amable dentro de un servidor de Discord. "
    "Responde en el idioma del usuario, de forma clara y concisa. "
    "Tus respuestas no deben superar los 1900 caracteres."
)

intents = discord.Intents.default()
intents.message_content = True  # actívalo también en el Developer Portal

client = discord.Client(intents=intents)

# Grok (xAI) usa un API compatible con OpenAI
ai = AsyncOpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")

# Memoria corta por canal (últimos 10 mensajes)
historial = defaultdict(lambda: deque(maxlen=10))


@client.event
async def on_ready():
    print(f"Conectado como {client.user}")


@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # Responde si lo mencionan o si es un mensaje directo
    es_dm = isinstance(message.channel, discord.DMChannel)
    if not (es_dm or client.user in message.mentions):
        return

    texto = message.content.replace(f"<@{client.user.id}>", "").strip()
    if not texto:
        return

    canal = message.channel.id
    historial[canal].append({"role": "user", "content": f"{message.author.display_name}: {texto}"})

    async with message.channel.typing():
        try:
            resp = await ai.chat.completions.create(
                model=MODEL,
                max_tokens=800,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}, *historial[canal]],
            )
            respuesta = resp.choices[0].message.content or "(sin respuesta)"
        except Exception as e:
            print("Error:", e)
            respuesta = "Ups, algo falló al contactar a la IA. Intenta de nuevo."

    historial[canal].append({"role": "assistant", "content": respuesta})
    await message.reply(respuesta[:1990], mention_author=False)


client.run(DISCORD_TOKEN)
