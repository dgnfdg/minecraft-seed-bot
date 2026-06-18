import discord
from discord.ext import commands
import aiohttp
import io
import os
from aiohttp import web
import asyncio

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
PORT = int(os.getenv('PORT', 10000))

MODELS = [
    "deepseek/deepseek-chat-v3.1:free",
    "google/gemini-2.0-flash-exp:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "qwen/qwen-2.5-72b-instruct:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
]

intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages = True
bot = commands.Bot(command_prefix='!', intents=intents)

SYSTEM_PROMPT = """Ты — генератор сидов Minecraft. Твоя задача: по описанию игрока подобрать сид (число от 1 до 9999999999), который соответствует запросу.

Используй свои знания о том, как работает генерация мира в Minecraft версий 1.18-1.21:
- Биомы генерируются по шуму Перлина
- Деревни появляются в равнинах, саваннах, пустынях, тайге, заснеженных равнинах
- Древние города - под Y=-50 в глубинах
- Цитадели - в радиусе 1408-2688 блоков от спавна
- Вишневые рощи - в горных биомах (1.20+)

ПРАВИЛА:
1. Подбирай сид так, чтобы он логично соответствовал описанию
2. Координаты структур указывай реалистичные
3. Не выдумывай невозможные комбинации
4. Указывай версию Minecraft, для которой подобран сид

Формат ответа:
🌱 **Сид:** [число]
🎮 **Версия:** [например 1.21]
📍 **Спавн:** X, Y, Z
🏛 **Что есть рядом:**
- Объект 1: координаты
- Объект 2: координаты
- Объект 3: координаты
📝 **Почему этот мир подходит:** [объяснение]
💎 **Совет:** [что стоит сделать в этом мире]

Пиши на русском, используй эмодзи."""

async def get_ai_response(user_text):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://discord.com",
        "X-Title": "Minecraft Seed Finder"
    }
    
    for model in MODELS:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text}
            ]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload, timeout=60) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        text = result['choices'][0]['message']['content']
                        print(f"✅ Модель: {model}")
                        return text, model
                    else:
                        print(f"⚠️ {model} не сработала ({resp.status})")
                        continue
        except Exception as e:
            print(f"❌ Ошибка {model}: {e}")
            continue
    
    return "❌ Все модели недоступны. Попробуй через минуту.", None

@bot.command()
async def поиск(ctx, *, description: str):
    async with ctx.typing():
        seed_info, used_model = await get_ai_response(description)
        
        clean_desc = description.replace(" ", "%20")[:150]
        img_url = f"https://image.pollinations.ai/prompt/minecraft%20landscape%20{clean_desc}%20cinematic%20shaders%204k?width=1024&height=768&nologo=true"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(img_url, timeout=60) as resp:
                    if resp.status == 200:
                        img_data = io.BytesIO(await resp.read())
                        file = discord.File(img_data, filename="world.png")
                        
                        embed = discord.Embed(
                            title="🗺️ Идеальный мир сгенерирован!",
                            description=seed_info[:4000],
                            color=0x2ecc71
                        )
                        embed.set_image(url="attachment://world.png")
                        if used_model:
                            embed.set_footer(text=f"Модель: {used_model}")
                        
                        await ctx.send(file=file, embed=embed)
                    else:
                        embed = discord.Embed(
                            title="🗺️ Идеальный мир сгенерирован!",
                            description=seed_info[:4000],
                            color=0x2ecc71
                        )
                        await ctx.send(embed=embed)
            except Exception:
                await ctx.send(seed_info)

@bot.command()
async def помощь(ctx):
    embed = discord.Embed(title="📚 Команды бота", color=0x3498db)
    embed.add_field(
        name="!поиск [описание]",
        value="Подобрать сид по описанию\nПример: `!поиск деревня в вишневом биоме рядом с горами`",
        inline=False
    )
    embed.add_field(
        name="💬 Где использовать",
        value="Можно писать на сервере или **в личные сообщения боту**!",
        inline=False
    )
    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    print(f"✅ Бот {bot.user} запущен!")
    print(f"📩 Работает в ЛС и на серверах")

async def handle_ping(request):
    return web.Response(text="Bot is alive! 🟢")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    app.router.add_get('/ping', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    print(f"🌐 Веб-сервер для пинга запущен на порту {PORT}")

async def main():
    await start_web_server()
    await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
