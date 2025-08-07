import os
import random

from discord import Intents, Object, Interaction, app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = Object(id=1402810501058134151)
SHOULD_SYNC = False

intents = Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
    print("------")

    if not SHOULD_SYNC:
        return

    try:
        guild = Object(id=1402810501058134151)
        synced = await bot.tree.sync(guild=guild)
        print(f"Synced {len(synced)} commands to the guild.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")


@bot.tree.command(
    name="99",
    guild=GUILD_ID,
    description="Get a random quote from Brooklyn 99",
)
async def nine_nine(interaction: Interaction):
    brooklyn_99_quotes = [
        "I'm the human form of the 💯 emoji.",
        "Bingpot!",
        (
            "Cool. Cool cool cool cool cool cool cool, "
            "no doubt no doubt no doubt no doubt."
        ),
    ]
    print(type(interaction))
    response = random.choice(brooklyn_99_quotes)
    await interaction.response.send_message(response)


if __name__ == "__main__":
    if TOKEN is None:
        raise ValueError("No DISCORD_TOKEN found in environment variables.")

    bot.run(TOKEN)
