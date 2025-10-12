import disnake
from disnake.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

# Get the bot token from environment variables
token = os.getenv("token")

# Check if token exists
if not token:
    print("Error: Bot token not found in .env file")
    exit(1)

# Create bot instance with default intents
bot = commands.Bot(
    command_prefix="!",
    intents=disnake.Intents.all(),
    help_command=None
)

@bot.event
async def on_ready():
    print(f"Bot is ready! Logged in as {bot.user}")
    
    # Set bot status to "неактивен" and activity to "hallcloud"
    await bot.change_presence(
        status=disnake.Status.idle,  # Yellow status (неактивен)
        activity=disnake.Activity(
            type=disnake.ActivityType.watching,
            name="AmethystCloud"
        )
    )
    
    # Load the ticket cog
    try:
        bot.load_extension("cogs.tickets")
        print("Ticket cog loaded successfully")
    except Exception as e:
        print(f"Error loading ticket cog: {e}")
    
    # Load the apply cog
    try:
        bot.load_extension("cogs.apply")
        print("Apply cog loaded successfully")
    except Exception as e:
        print(f"Error loading apply cog: {e}")

    # Load the pterodactyl cog
    try:
        bot.load_extension("cogs.pterodactyl")
        print("Pterodactyl cog loaded successfully")
    except Exception as e:
        print(f"Error loading pterodactyl cog: {e}")
        
    # Load the invites cog
    try:
        bot.load_extension("cogs.invites")
        print("Invites cog loaded successfully")
    except Exception as e:
        print(f"Error loading invites cog: {e}")


# Run the bot
try:
    bot.run(token)
except disnake.LoginFailure:
    print("Error: Invalid bot token")
except Exception as e:
    print(f"Error running bot: {e}")




