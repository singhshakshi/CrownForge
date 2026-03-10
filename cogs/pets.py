"""cogs/pets.py — Pet system with guild_id."""
import discord
from discord import app_commands
from discord.ext import commands
from database import get_character, add_coins, add_pet, has_pet, get_player_pets, equip_pet_db
from helpers import check_jail

PETS_DATA = [
    {"name":"Baby Dragon","emoji":"🐲","cost":500,"atk_boost":10,"def_boost":5,"hp_boost":20,"ability":"Fireball"},
    {"name":"Wolf Pup","emoji":"🐺","cost":300,"atk_boost":8,"def_boost":3,"hp_boost":10,"ability":"Bite"},
    {"name":"Fairy","emoji":"🧚","cost":400,"atk_boost":3,"def_boost":3,"hp_boost":30,"ability":"Heal"},
    {"name":"Shadow Cat","emoji":"🐈‍⬛","cost":350,"atk_boost":12,"def_boost":2,"hp_boost":5,"ability":"Shadow Strike"},
    {"name":"Phoenix Chick","emoji":"🐦‍🔥","cost":800,"atk_boost":15,"def_boost":10,"hp_boost":30,"ability":"Rebirth"},
    {"name":"Slime","emoji":"🟢","cost":100,"atk_boost":2,"def_boost":5,"hp_boost":10,"ability":"Absorb"},
    {"name":"Owl","emoji":"🦉","cost":250,"atk_boost":5,"def_boost":5,"hp_boost":15,"ability":"Wisdom"},
    {"name":"Golem","emoji":"🪨","cost":600,"atk_boost":5,"def_boost":15,"hp_boost":40,"ability":"Shield Bash"},
]
def find_pet(n): return next((p for p in PETS_DATA if p["name"].lower()==n.lower()),None)

class PetsCog(commands.Cog):
    def __init__(self,bot): self.bot=bot
    @app_commands.command(name="pets",description="🐾 Pet shop!")
    async def pets(self,interaction:discord.Interaction):
        if await check_jail(interaction): return
        e=discord.Embed(title="🐾 Pet Shop",color=0xE67E22)
        for p in PETS_DATA:
            e.add_field(name=f"{p['emoji']} {p['name']} `{p['cost']}`🪙",value=f"+{p['atk_boost']}ATK +{p['def_boost']}DEF +{p['hp_boost']}HP • {p['ability']}",inline=True)
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="buypet",description="🐾 Buy a pet!")
    @app_commands.describe(name="Pet name")
    async def buypet(self,interaction:discord.Interaction,name:str):
        gid=interaction.guild.id; uid=interaction.user.id
        if await check_jail(interaction): return
        char=await get_character(uid,gid)
        if not char: return await interaction.response.send_message(embed=discord.Embed(title="❌",description="Use `/start`!",color=0xE74C3C),ephemeral=True)
        p=find_pet(name)
        if not p: return await interaction.response.send_message(embed=discord.Embed(title="❌",description="Not found!",color=0xE74C3C),ephemeral=True)
        if await has_pet(uid,gid,p["name"]): return await interaction.response.send_message(embed=discord.Embed(title="⚠️",description="Already owned!",color=0xF39C12),ephemeral=True)
        if char["coins"]<p["cost"]: return await interaction.response.send_message(embed=discord.Embed(title="💸",description="Not enough!",color=0xE74C3C),ephemeral=True)
        await add_coins(uid,gid,-p["cost"]); await add_pet(uid,gid,p["name"])
        await interaction.response.send_message(embed=discord.Embed(title=f"🐾 Adopted {p['emoji']} {p['name']}!",color=0x2ECC71))

    @app_commands.command(name="equippet",description="🐾 Equip a pet.")
    @app_commands.describe(name="Pet name")
    async def equippet(self,interaction:discord.Interaction,name:str):
        gid=interaction.guild.id
        if await check_jail(interaction): return
        p=find_pet(name); pn=p["name"] if p else name
        ok=await equip_pet_db(interaction.user.id,gid,pn)
        if not ok: return await interaction.response.send_message(embed=discord.Embed(title="❌",description="Not owned!",color=0xE74C3C),ephemeral=True)
        await interaction.response.send_message(embed=discord.Embed(title=f"🐾 Equipped {pn}!",color=0x3498DB))

    @app_commands.command(name="mypets",description="🐾 Your pets.")
    async def mypets(self,interaction:discord.Interaction):
        gid=interaction.guild.id
        if await check_jail(interaction): return
        pets=await get_player_pets(interaction.user.id,gid)
        if not pets: return await interaction.response.send_message(embed=discord.Embed(title="🐾 No Pets",description="Buy at `/pets`!",color=0x95A5A6))
        e=discord.Embed(title="🐾 Your Pets",color=0xE67E22)
        for pt in pets:
            pd=find_pet(pt["pet_name"]); em=pd["emoji"] if pd else "🐾"; eq=" ✅" if pt["equipped"] else ""
            e.add_field(name=f"{em} {pt['pet_name']}{eq}",value=f"+{pd['atk_boost']}ATK +{pd['def_boost']}DEF" if pd else "",inline=True)
        await interaction.response.send_message(embed=e)

async def setup(bot): await bot.add_cog(PetsCog(bot))
