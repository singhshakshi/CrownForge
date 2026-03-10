"""cogs/hospital.py — Hospital with guild_id."""
import random,discord
from discord import app_commands
from discord.ext import commands
from database import get_character,update_character,add_coins,get_cooldown,set_cooldown,check_cooldown,clear_debuffs,is_king,is_queen
from helpers import check_jail

class HospitalCog(commands.Cog):
    def __init__(self,bot): self.bot=bot

    @app_commands.command(name="hospital",description="🏥 Treatments.")
    async def hospital(self,i:discord.Interaction):
        if await check_jail(i): return
        e=discord.Embed(title="🏥 Kingdom Hospital",color=0x2ECC71)
        e.add_field(name="💊 /heal",value="Full HP. Cost: 10×lvl (1hr CD). 👑50% off",inline=False)
        e.add_field(name="✨ /treat",value="Remove debuffs. 100🪙. 👑50% off",inline=False)
        e.add_field(name="⚡ /revive",value="From 0HP. 200🪙. 👑50% off",inline=False)
        e.add_field(name="⛏️ /workhospital",value="Workers only. 4hr CD",inline=False)
        await i.response.send_message(embed=e)

    @app_commands.command(name="heal",description="💊 Heal to full HP.")
    async def heal(self,i:discord.Interaction):
        gid=i.guild.id; uid=i.user.id
        if await check_jail(i): return
        char=await get_character(uid,gid)
        if not char: return await i.response.send_message(embed=discord.Embed(title="❌",description="Use `/start`!",color=0xE74C3C),ephemeral=True)
        last=await get_cooldown(uid,gid,"heal"); ready,rem=check_cooldown(last,3600)
        if not ready: return await i.response.send_message(embed=discord.Embed(title="⏳",description=f"{rem//60}m CD",color=0xF39C12),ephemeral=True)
        if char["hp"]>=char["max_hp"]: return await i.response.send_message(embed=discord.Embed(title="❤️",description="Full HP!",color=0x2ECC71),ephemeral=True)
        cost=10*char["level"]
        if await is_king(gid,uid) or await is_queen(gid,uid): cost//=2
        if char["coins"]<cost: return await i.response.send_message(embed=discord.Embed(title="💸",description=f"Need {cost}🪙",color=0xE74C3C),ephemeral=True)
        await add_coins(uid,gid,-cost); await update_character(uid,gid,hp=char["max_hp"]); await set_cooldown(uid,gid,"heal")
        await i.response.send_message(embed=discord.Embed(title="💊 Healed!",description=f"Full HP! Cost: {cost}🪙",color=0x2ECC71))

    @app_commands.command(name="treat",description="✨ Remove debuffs.")
    async def treat(self,i:discord.Interaction):
        gid=i.guild.id; uid=i.user.id
        if await check_jail(i): return
        char=await get_character(uid,gid)
        if not char: return await i.response.send_message(embed=discord.Embed(title="❌",description="Use `/start`!",color=0xE74C3C),ephemeral=True)
        cost=100 if not (await is_king(gid,uid) or await is_queen(gid,uid)) else 50
        if char["coins"]<cost: return await i.response.send_message(embed=discord.Embed(title="💸",description=f"Need {cost}🪙",color=0xE74C3C),ephemeral=True)
        await add_coins(uid,gid,-cost); await clear_debuffs(uid,gid)
        await i.response.send_message(embed=discord.Embed(title="✨ Treated!",description=f"Debuffs removed! {cost}🪙",color=0x2ECC71))

    @app_commands.command(name="revive",description="⚡ Revive from 0 HP.")
    async def revive(self,i:discord.Interaction):
        gid=i.guild.id; uid=i.user.id
        char=await get_character(uid,gid)
        if not char: return await i.response.send_message(embed=discord.Embed(title="❌",description="Use `/start`!",color=0xE74C3C),ephemeral=True)
        if char["hp"]>0: return await i.response.send_message(embed=discord.Embed(title="❤️",description="Not knocked out!",color=0x2ECC71),ephemeral=True)
        cost=200 if not (await is_king(gid,uid) or await is_queen(gid,uid)) else 100
        if char["coins"]<cost: return await i.response.send_message(embed=discord.Embed(title="💸",description=f"Need {cost}🪙",color=0xE74C3C),ephemeral=True)
        await add_coins(uid,gid,-cost); await update_character(uid,gid,hp=char["max_hp"])
        await i.response.send_message(embed=discord.Embed(title="⚡ Revived!",description=f"Full HP! {cost}🪙",color=0x2ECC71))

    @app_commands.command(name="workhospital",description="🏥 (Worker) Hospital shift. 4hr CD.")
    async def workhospital(self,i:discord.Interaction):
        gid=i.guild.id; uid=i.user.id
        if await check_jail(i): return
        char=await get_character(uid,gid)
        if not char or char["class"]!="Worker": return await i.response.send_message(embed=discord.Embed(title="❌",description="Workers only!",color=0xE74C3C),ephemeral=True)
        last=await get_cooldown(uid,gid,"workhospital"); ready,rem=check_cooldown(last,14400)
        if not ready: h=rem//3600; return await i.response.send_message(embed=discord.Embed(title="⏳",description=f"{h}h CD",color=0xF39C12),ephemeral=True)
        await set_cooldown(uid,gid,"workhospital"); earnings=50+char["level"]*8+random.randint(0,30)
        await add_coins(uid,gid,earnings)
        await i.response.send_message(embed=discord.Embed(title="🏥 Shift Done!",description=f"+**{earnings}**🪙",color=0x2ECC71))

async def setup(bot): await bot.add_cog(HospitalCog(bot))
