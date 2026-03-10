"""cogs/shop.py — Shop with guild_id + jail check."""
import discord
from discord import app_commands
from discord.ext import commands
from database import get_character, add_item_to_inventory, has_item, equip_item, add_coins
from helpers import check_jail

SHOP_ITEMS = [
    {"name":"Rusty Sword","type":"weapon","emoji":"🗡️","attack_bonus":5,"defense_bonus":0,"hp_bonus":0,"cost":50},
    {"name":"Iron Longsword","type":"weapon","emoji":"⚔️","attack_bonus":12,"defense_bonus":0,"hp_bonus":0,"cost":150},
    {"name":"Enchanted Staff","type":"weapon","emoji":"🪄","attack_bonus":18,"defense_bonus":0,"hp_bonus":0,"cost":300},
    {"name":"Shadow Dagger","type":"weapon","emoji":"🔪","attack_bonus":15,"defense_bonus":0,"hp_bonus":0,"cost":220},
    {"name":"Dragon Slayer","type":"weapon","emoji":"🔥","attack_bonus":30,"defense_bonus":5,"hp_bonus":0,"cost":800},
    {"name":"Leather Vest","type":"armor","emoji":"🧥","attack_bonus":0,"defense_bonus":5,"hp_bonus":10,"cost":60},
    {"name":"Chainmail","type":"armor","emoji":"🛡️","attack_bonus":0,"defense_bonus":12,"hp_bonus":20,"cost":200},
    {"name":"Mage Robes","type":"armor","emoji":"🧙","attack_bonus":8,"defense_bonus":5,"hp_bonus":15,"cost":250},
    {"name":"Dark Plate Armor","type":"armor","emoji":"⚫","attack_bonus":0,"defense_bonus":22,"hp_bonus":40,"cost":500},
    {"name":"Phoenix Armor","type":"armor","emoji":"🔶","attack_bonus":5,"defense_bonus":28,"hp_bonus":60,"cost":1000},
    {"name":"Lucky Charm","type":"accessory","emoji":"🍀","attack_bonus":3,"defense_bonus":3,"hp_bonus":5,"cost":100},
    {"name":"Amulet of Power","type":"accessory","emoji":"📿","attack_bonus":10,"defense_bonus":5,"hp_bonus":15,"cost":350},
]
def find_shop_item(n): return next((i for i in SHOP_ITEMS if i["name"].lower()==n.lower()), None)

class ShopCog(commands.Cog):
    def __init__(self,bot): self.bot=bot

    @app_commands.command(name="shop",description="🛒 Browse the shop!")
    async def shop(self, interaction: discord.Interaction):
        if await check_jail(interaction): return
        e=discord.Embed(title="🏪 Shop",color=0xF1C40F)
        for t,h in [("weapon","⚔️ Weapons"),("armor","🛡️ Armor"),("accessory","💎 Accessories")]:
            items=[i for i in SHOP_ITEMS if i["type"]==t]
            lines=[f"{i['emoji']} **{i['name']}** `{i['cost']}`🪙 (+{i['attack_bonus']}ATK +{i['defense_bonus']}DEF +{i['hp_bonus']}HP)" for i in items]
            e.add_field(name=h,value="\n".join(lines),inline=False)
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="buy",description="💰 Buy a shop item.")
    @app_commands.describe(item_name="Item name")
    async def buy(self, interaction: discord.Interaction, item_name: str):
        gid=interaction.guild.id if interaction.guild else None
        if not gid: return
        if await check_jail(interaction): return
        char=await get_character(interaction.user.id,gid)
        if not char: return await interaction.response.send_message(embed=discord.Embed(title="❌",description="Use `/start`!",color=0xE74C3C),ephemeral=True)
        si=find_shop_item(item_name)
        if not si: return await interaction.response.send_message(embed=discord.Embed(title="❌",description="Not found!",color=0xE74C3C),ephemeral=True)
        if await has_item(interaction.user.id,gid,si["name"]): return await interaction.response.send_message(embed=discord.Embed(title="⚠️",description="Already owned!",color=0xF39C12),ephemeral=True)
        if char["coins"]<si["cost"]: return await interaction.response.send_message(embed=discord.Embed(title="💸",description="Not enough!",color=0xE74C3C),ephemeral=True)
        await add_coins(interaction.user.id,gid,-si["cost"])
        await add_item_to_inventory(interaction.user.id,gid,si["name"],si["type"],si["attack_bonus"],si["defense_bonus"],si["hp_bonus"],si["cost"])
        await interaction.response.send_message(embed=discord.Embed(title=f"✅ Bought {si['emoji']} {si['name']}!",description=f"Use `/equip {si['name']}`",color=0x2ECC71))

    @app_commands.command(name="equip",description="🎒 Equip an item.")
    @app_commands.describe(item_name="Item name")
    async def equip(self, interaction: discord.Interaction, item_name: str):
        gid=interaction.guild.id if interaction.guild else None
        if not gid: return
        if await check_jail(interaction): return
        ok=await equip_item(interaction.user.id,gid,item_name)
        if not ok: return await interaction.response.send_message(embed=discord.Embed(title="❌",description="Not owned!",color=0xE74C3C),ephemeral=True)
        await interaction.response.send_message(embed=discord.Embed(title=f"✅ Equipped {item_name}!",color=0x3498DB))

async def setup(bot): await bot.add_cog(ShopCog(bot))
