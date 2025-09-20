import discord
from discord.ext import commands
from discord import app_commands
from text_utils import extract_text_from_message
from moderation import analyze_text
from youtube_utils import fetch_youtube_videos
from rag_model_stub import query_model_stub

TOKEN = "YOUR_DISCORD_BOT_TOKEN"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Slash komutlar
@bot.tree.command(name="youtube", description="Bir kanalın videolarını çek")
@app_commands.describe(channel_id="Hedef kanal ID")
async def youtube(interaction: discord.Interaction, channel_id: str):
    videos = fetch_youtube_videos(channel_id)
    msg = f"{len(videos)} video bulundu!\n"
    for v in videos:
        msg += f"{v['başlık']}: https://www.youtube.com/watch?v={v['videoId']}\n"
    await interaction.response.send_message(msg)

@bot.tree.command(name="analyze", description="Mesaj veya URL analizi")
@app_commands.describe(content="Mesaj metni veya URL")
async def analyze(interaction: discord.Interaction, content: str):
    text = extract_text_from_message(content)
    analysis = analyze_text(text)
    rag_response = query_model_stub(text)
    await interaction.response.send_message(
        f"Temiz metin: {text}\n"
        f"Analiz: {analysis}\n"
        f"RAG cevabı (stub): {rag_response}"
    )

# Webhook / mesaj eventleri (isteğe göre eklenebilir)
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    text = extract_text_from_message(message.content)
    analysis = analyze_text(text)
    print(f"[Event] {message.author}: {text} -> {analysis}")

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot giriş yaptı: {bot.user}")

bot.run(TOKEN)
