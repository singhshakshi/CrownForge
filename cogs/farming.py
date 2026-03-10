"""cogs/farming.py — Farming with guild_id."""
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from database import get_character,create_farm_plot,get_farm_plots,count_active_plots,water_plots,remove_farm_plot,add_player_item
from helpers import check_jail

CROPS={"Wheat":{"emoji":"🌾","grow_hours":1,"sell":20},"Carrot":{"emoji":"🥕","grow_hours":2,"sell":40},
    "Potato":{"emoji":"🥔","grow_hours":3,"sell":60},"Tomato":{"emoji":"🍅","grow_hours":4,"sell":80},
    "Corn":{"emoji":"🌽","grow_hours":5,"sell":100},"Magic Herb":{"emoji":"🌿","grow_hours":8,"sell":250},
    "Golden Apple":{"emoji":"🍎","grow_hours":24,"sell":1000}}

def crop_status(p,now):
    cd=CROPS.get(p["crop"]); planted=datetime.fromisoformat(p["planted_at"])
    gs=cd["grow_hours"]*3600; gs=int(gs*0.8) if p["watered"] else gs
    el=(now-planted).total_seconds()
    if el>=gs*2: return "dead",0,0
    if el>=gs: return "ready",0,0
    return "growing",gs-el,el/gs

class FarmingCog(commands.Cog):
    def __init__(self,bot): self.bot=bot

    @app_commands.command(name="sow",description="🌱 Plant a crop!")
    @app_commands.describe(crop="Crop")
    @app_commands.choices(crop=[app_commands.Choice(name=f"{v['emoji']}{k}({v['grow_hours']}hr)",value=k) for k,v in CROPS.items()])
    async def sow(self,interaction:discord.Interaction,crop:app_commands.Choice[str]):
        gid=interaction.guild.id; uid=interaction.user.id
        if await check_jail(interaction): return
        char=await get_character(uid,gid)
        if not char: return await interaction.response.send_message(embed=discord.Embed(title="❌",description="Use `/start`!",color=0xE74C3C),ephemeral=True)
        if await count_active_plots(uid,gid)>=5: return await interaction.response.send_message(embed=discord.Embed(title="❌",description="Max 5 plots!",color=0xE74C3C),ephemeral=True)
        cd=CROPS[crop.value]; await create_farm_plot(uid,gid,crop.value,datetime.utcnow().isoformat())
        await interaction.response.send_message(embed=discord.Embed(title=f"🌱 Planted {cd['emoji']}{crop.value}!",description=f"Ready in {cd['grow_hours']}hrs",color=0x2ECC71))

    @app_commands.command(name="water",description="💧 Water crops (-20% time).")
    async def water(self,interaction:discord.Interaction):
        gid=interaction.guild.id
        if await check_jail(interaction): return
        plots=await get_farm_plots(interaction.user.id,gid)
        if not plots: return await interaction.response.send_message(embed=discord.Embed(title="❌",description="No crops!",color=0xE74C3C),ephemeral=True)
        await water_plots(interaction.user.id,gid)
        await interaction.response.send_message(embed=discord.Embed(title="💧 Watered!",color=0x3498DB))

    @app_commands.command(name="harvest",description="🌾 Harvest ready crops!")
    async def harvest(self,interaction:discord.Interaction):
        gid=interaction.guild.id; uid=interaction.user.id
        if await check_jail(interaction): return
        char=await get_character(uid,gid)
        if not char: return await interaction.response.send_message(embed=discord.Embed(title="❌",description="Use `/start`!",color=0xE74C3C),ephemeral=True)
        plots=await get_farm_plots(uid,gid); now=datetime.utcnow()
        if not plots: return await interaction.response.send_message(embed=discord.Embed(title="❌",description="No crops!",color=0xE74C3C),ephemeral=True)
        h,d,g=[],[],[]
        for p in plots:
            s,rem,pct=crop_status(p,now); cd=CROPS.get(p["crop"])
            if s=="ready":
                qty=2 if char["class"]=="Worker" else 1
                await add_player_item(uid,gid,p["crop"],"crop",qty); await remove_farm_plot(p["id"])
                h.append(f"{cd['emoji']}{p['crop']}x{qty}")
            elif s=="dead": await remove_farm_plot(p["id"]); d.append(f"💀{p['crop']}")
            else:
                m2,s2=divmod(int(rem),60); hr,m2=divmod(m2,60)
                g.append(f"{cd['emoji']}{p['crop']} {hr}h{m2}m")
        e=discord.Embed(title="🌾 Harvest",color=0x2ECC71)
        if h: e.add_field(name="✅",value="\n".join(h),inline=False)
        if d: e.add_field(name="💀 Dead",value="\n".join(d),inline=False)
        if g: e.add_field(name="⏳ Growing",value="\n".join(g),inline=False)
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="farm",description="🌱 Farm status.")
    async def farm(self,interaction:discord.Interaction):
        gid=interaction.guild.id
        if await check_jail(interaction): return
        plots=await get_farm_plots(interaction.user.id,gid); now=datetime.utcnow()
        if not plots: return await interaction.response.send_message(embed=discord.Embed(title="🌱 Empty Farm",description="Use `/sow`!",color=0x95A5A6))
        e=discord.Embed(title="🌱 Farm",color=0x2ECC71)
        for p in plots:
            cd=CROPS.get(p["crop"],{}); s,rem,pct=crop_status(p,now)
            if s=="ready": val="🟩"*10+" ✅ Ready!"
            elif s=="dead": val="💀 DEAD"
            else:
                f=int(pct*10); bar="🟩"*f+"⬜"*(10-f)
                m2,s2=divmod(int(rem),60); hr,m2=divmod(m2,60)
                val=f"{bar} {hr}h{m2}m"
            e.add_field(name=f"{cd.get('emoji','🌱')}{p['crop']}",value=val,inline=False)
        await interaction.response.send_message(embed=e)

async def setup(bot): await bot.add_cog(FarmingCog(bot))
