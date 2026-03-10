"""cogs/leaderboard.py — Leaderboard with guild_id."""
import discord
from discord import app_commands
from discord.ext import commands
from database import get_leaderboard, xp_for_level, get_kingdom
from helpers import check_jail

RANK_EMOJIS=["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
CE={"Warrior":"⚔️","Mage":"🔮","Thief":"🗡️","Worker":"⛏️","Rival":"😈","Commoner":"👤","Rogue":"🗡️"}

class LeaderboardCog(commands.Cog):
    def __init__(self,bot): self.bot=bot
    @app_commands.command(name="leaderboard",description="🏆 Top 10!")
    async def leaderboard(self, interaction: discord.Interaction):
        gid=interaction.guild.id if interaction.guild else None
        if not gid: return
        if await check_jail(interaction): return
        players=await get_leaderboard(gid)
        if not players: return await interaction.response.send_message(embed=discord.Embed(title="🏆",description="No adventurers!",color=0xF39C12))
        k=await get_kingdom(gid)
        lines=[]
        for i,p in enumerate(players):
            r=RANK_EMOJIS[i] if i<len(RANK_EMOJIS) else f"#{i+1}"
            tags=""
            if k and k.get("king_id")==p["user_id"]: tags=" 👑"
            elif k and k.get("queen_id")==p["user_id"]: tags=" 👑"
            mood={"happy":"😊","sad":"😢"}.get(p.get("mood",""),"")
            lines.append(f"{r} **{p['username']}** {CE.get(p['class'],'')}{tags} {mood}\n   Lvl `{p['level']}` • XP `{p['xp']}`/`{xp_for_level(p['level'])}` • 🪙`{p['coins']}`")
        await interaction.response.send_message(embed=discord.Embed(title="🏆 Leaderboard",description="\n".join(lines),color=0xFFD700))

async def setup(bot): await bot.add_cog(LeaderboardCog(bot))
