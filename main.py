import disnake
from disnake.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

# Получение токена бота из переменных окружения
token = os.getenv("token")

if not token:
    print("❌ Ошибка: Токен бота не найден в .env файле")
    exit(1)

# Создание экземпляра бота
bot = commands.Bot(
    command_prefix="!",
    intents=disnake.Intents.all(),
    help_command=None
)

@bot.event
async def on_ready():
    """Событие при успешном запуске бота"""
    print(f"✅ Бот запущен! Вошли как {bot.user}")
    
    # Установка статуса бота
    await bot.change_presence(
        status=disnake.Status.idle,
        activity=disnake.Activity(
            type=disnake.ActivityType.watching,
            name="AmethystCloud"
        )
    )
    
    # Загрузка расширений (cogs)
    cogs = [
        ("cogs.tickets", "Tickets"),
        ("cogs.apply", "Apply"),
        ("cogs.pterodactyl", "Pterodactyl"),
        ("cogs.invites", "Invites")
    ]
    
    for cog_path, cog_name in cogs:
        try:
            bot.load_extension(cog_path)
            print(f"✅ {cog_name} cog загружен успешно")
        except Exception as e:
            print(f"❌ Ошибка загрузки {cog_name} cog: {e}")
        


@bot.command(name="оплата")
async def oplata(ctx):
    """Показать реквизиты для оплаты"""
    embed = disnake.Embed(
        title="💳 AmethystCloud • Реквизиты для оплаты",
        description="Выберите удобный для вас способ оплаты:",
        color=disnake.Color.purple(),
        timestamp=ctx.message.created_at
    )
    
    embed.add_field(
        name="🇷🇺 Карты РФ",
        value=(
            "**Т-Банк**\n"
            "`000000000000000000000000`\n\n"
            "**Сбербанк**\n"
            "`000000000000000000000000`\n\n"
            "**Озон Банк**\n"
            "`000000000000000000000000`"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🇺🇦 Карта Украины",
        value=(
            "`000000000000000000000000`\n"
            "*Присутствует небольшая комиссия*"
        ),
        inline=False
    )
    
    embed.add_field(
        name="💎 Другие способы оплаты",
        value=(
            "• Криптовалюта\n"
            "• DonationAlerts\n"
            "• FunPay\n\n"
            "*Присутствует высокая комиссия*\n"
            "*Уточняйте индивидуально*"
        ),
        inline=False
    )
    
    embed.set_thumbnail(url=bot.user.avatar.url if bot.user.avatar else bot.user.default_avatar.url)
    
    embed.set_footer(
        text=f"Спасибо за вашу поддержку! • Запросил {ctx.author}",
        icon_url=ctx.author.display_avatar.url
    )
    
    await ctx.send(embed=embed)


# Запуск бота
if __name__ == "__main__":
    try:
        bot.run(token)
    except disnake.LoginFailure:
        print("❌ Ошибка: Неверный токен бота")
    except Exception as e:
        print(f"❌ Ошибка запуска бота: {e}")
