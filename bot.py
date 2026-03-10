"""bot.py — Main entry point."""
import os, asyncio, discord
from discord.ext import commands
from dotenv import load_dotenv
from database import init_db

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not TOKEN or TOKEN == "YOUR_BOT_TOKEN_HERE": print("❌ Set token in .env!"); exit(1)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

COG_EXTENSIONS = [
    "cogs.character","cogs.quest","cogs.duel","cogs.shop","cogs.leaderboard",
    "cogs.tournament","cogs.kingdom","cogs.roles","cogs.events","cogs.pets","cogs.friends",
    "cogs.farming","cogs.bank","cogs.hospital","cogs.marketplace","cogs.inventory_cog",
    "cogs.jail","cogs.lawyers",
]

@bot.event
async def on_ready():
    await init_db()
    print(f"{'─'*50}\n⚔️  RPG Bot online as {bot.user}\n🌐  {len(bot.guilds)} guild(s)\n{'─'*50}")
    try:
        synced = await bot.tree.sync()
        print(f"✅  Synced {len(synced)} command(s)")
    except Exception as e: print(f"❌  Sync: {e}")

async def load_extensions():
    for ext in COG_EXTENSIONS:
        try: await bot.load_extension(ext); print(f"  ✅  {ext}")
        except Exception as e: print(f"  ❌  {ext}: {e}")

async def main():
    async with bot:
        await load_extensions(); await bot.start(TOKEN)

if __name__ == "__main__": asyncio.run(main())
