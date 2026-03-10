"""cogs/inventory_cog.py — Inventory, eat, gift with guild_id."""
import discord
from discord import app_commands
from discord.ext import commands
from database import (get_character,get_inventory,get_player_items,get_player_pets,has_player_item,
    remove_player_item,add_player_item,add_buff,update_character,set_mood)
from helpers import check_jail

FOOD={"Wheat":{"buff":"attack","value":5,"hours":0.5},"Carrot":{"buff":"defense","value":8,"hours":1},
    "Potato":{"buff":"defense","value":12,"hours":1},"Tomato":{"buff":"attack","value":12,"hours":1},
    "Corn":{"buff":"defense","value":15,"hours":1.5},"Magic Herb":{"buff":"hp_restore","value":50,"hours":0},
    "Golden Apple":{"buff":"attack","value":50,"hours":1},"Health Potion":{"buff":"hp_restore","value":80,"hours":0},
    "Attack Elixir":{"buff":"attack","value":20,"hours":1},"Defense Brew":{"buff":"defense","value":20,"hours":1}}

class InventoryCog(commands.Cog):
    def __init__(self,bot): self.bot=bot

    @app_commands.command(name="inventory",description="🎒 Full inventory.")
    async def inventory(self,i:discord.Interaction):
        gid=i.guild.id; uid=i.user.id
        if await check_jail(i): return
        char=await get_character(uid,gid)
        if not char: return await i.response.send_message(embed=discord.Embed(title="❌",description="Use `/start`!",color=0xE74C3C),ephemeral=True)
        e=discord.Embed(title=f"🎒 {i.user.display_name}'s Inventory",color=0x3498DB)
        gear=await get_inventory(uid,gid)
        if gear: e.add_field(name="⚔️ Gear",value="\n".join(f"{'✅' if g['equipped'] else '🔹'} {g['item_name']}" for g in gear[:10]),inline=False)
        items=await get_player_items(uid,gid)
        if items: e.add_field(name="📦 Items",value="\n".join(f"• {it['item_name']} x{it['quantity']}" for it in items[:15]),inline=False)
        pets=await get_player_pets(uid,gid)
        if pets: e.add_field(name="🐾 Pets",value="\n".join(f"{'✅' if p['equipped'] else '🐾'} {p['pet_name']}" for p in pets),inline=False)
        if not gear and not items and not pets: e.description="Empty! `/shop`, `/farm`, `/pets`"
        await i.response.send_message(embed=e)

    @app_commands.command(name="eat",description="🍎 Eat food for buffs!")
    @app_commands.describe(food="Food name")
    async def eat(self,i:discord.Interaction,food:str):
        gid=i.guild.id; uid=i.user.id
        if await check_jail(i): return
        char=await get_character(uid,gid)
        if not char: return await i.response.send_message(embed=discord.Embed(title="❌",description="Use `/start`!",color=0xE74C3C),ephemeral=True)
        fb=None; actual=food
        for n,d in FOOD.items():
            if n.lower()==food.lower(): fb=d; actual=n; break
        if not fb: return await i.response.send_message(embed=discord.Embed(title="❌",description=f"Can't eat that! Try: {', '.join(FOOD.keys())}",color=0xE74C3C),ephemeral=True)
        if not await has_player_item(uid,gid,actual): return await i.response.send_message(embed=discord.Embed(title="❌",description=f"No {actual}!",color=0xE74C3C),ephemeral=True)
        await remove_player_item(uid,gid,actual)
        if fb["buff"]=="hp_restore":
            nhp=min(char["max_hp"],char["hp"]+fb["value"]); await update_character(uid,gid,hp=nhp)
            desc=f"Restored {fb['value']} HP → `{nhp}`"
        else: await add_buff(uid,gid,fb["buff"],fb["value"],fb["hours"]); desc=f"+{fb['value']} {fb['buff']} for {fb['hours']}hr"
        await i.response.send_message(embed=discord.Embed(title=f"🍎 Ate {actual}!",description=desc,color=0x2ECC71))

    @app_commands.command(name="giftitem",description="🎁 Gift an item!")
    @app_commands.describe(target="Player",item="Item")
    async def giftitem(self,i:discord.Interaction,target:discord.Member,item:str):
        gid=i.guild.id; uid=i.user.id
        if await check_jail(i): return
        if not await has_player_item(uid,gid,item): return await i.response.send_message(embed=discord.Embed(title="❌",description="Don't have!",color=0xE74C3C),ephemeral=True)
        tc=await get_character(target.id,gid)
        if not tc: return await i.response.send_message(embed=discord.Embed(title="❌",description="No character!",color=0xE74C3C),ephemeral=True)
        await remove_player_item(uid,gid,item); await add_player_item(target.id,gid,item,"gift")
        await set_mood(target.id,gid,"happy")
        await i.response.send_message(embed=discord.Embed(title="🎁 Gifted!",description=f"**{item}** → **{target.display_name}** 😊",color=0xE67E22))

async def setup(bot): await bot.add_cog(InventoryCog(bot))
