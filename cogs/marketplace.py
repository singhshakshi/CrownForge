"""cogs/marketplace.py — Marketplace with guild_id."""
import discord
from discord import app_commands
from discord.ext import commands
from database import (get_character,add_coins,has_player_item,remove_player_item,add_player_item,
    create_listing,get_listings,get_listing,remove_listing,get_kingdom,update_kingdom)
from helpers import check_jail

class TradeView(discord.ui.View):
    def __init__(self,fid,tid,item,price,gid):
        super().__init__(timeout=120); self.fid,self.tid,self.item,self.price,self.gid=fid,tid,item,price,gid
    async def interaction_check(self,i):
        if i.user.id!=self.tid: await i.response.send_message("❌",ephemeral=True); return False
        return True
    @discord.ui.button(label="Accept ✅",style=discord.ButtonStyle.success)
    async def acc(self,i,b):
        buyer=await get_character(self.tid,self.gid)
        if not buyer or buyer["coins"]<self.price: self.stop(); return await i.response.edit_message(embed=discord.Embed(title="❌",description="Not enough!",color=0xE74C3C),view=None)
        await add_coins(self.tid,self.gid,-self.price); await add_coins(self.fid,self.gid,self.price)
        await remove_player_item(self.fid,self.gid,self.item); await add_player_item(self.tid,self.gid,self.item,"traded")
        self.stop(); await i.response.edit_message(embed=discord.Embed(title="✅ Trade Done!",color=0x2ECC71),view=None)
    @discord.ui.button(label="Decline ❌",style=discord.ButtonStyle.danger)
    async def dec(self,i,b): self.stop(); await i.response.edit_message(embed=discord.Embed(title="❌ Declined",color=0xE74C3C),view=None)

class MarketplaceCog(commands.Cog):
    def __init__(self,bot): self.bot=bot

    @app_commands.command(name="market",description="🏪 Marketplace.")
    async def market(self,i:discord.Interaction):
        gid=i.guild.id
        if await check_jail(i): return
        ls=await get_listings(gid)
        if not ls: return await i.response.send_message(embed=discord.Embed(title="🏪 Empty",description="Use `/sell`!",color=0x95A5A6))
        e=discord.Embed(title="🏪 Marketplace",color=0xF1C40F)
        for l in ls[:15]: e.add_field(name=f"#{l['id']} {l['item_name']}x{l['quantity']}",value=f"`{l['price']}`🪙 by {l['seller_name']}",inline=False)
        await i.response.send_message(embed=e)

    @app_commands.command(name="sell",description="🏪 List item for sale.")
    @app_commands.describe(item="Item",quantity="Qty",price="Price")
    async def sell(self,i:discord.Interaction,item:str,quantity:int=1,price:int=10):
        gid=i.guild.id; uid=i.user.id
        if await check_jail(i): return
        char=await get_character(uid,gid)
        if not char: return await i.response.send_message(embed=discord.Embed(title="❌",description="Use `/start`!",color=0xE74C3C),ephemeral=True)
        if not await has_player_item(uid,gid,item,quantity): return await i.response.send_message(embed=discord.Embed(title="❌",description="Not enough!",color=0xE74C3C),ephemeral=True)
        await remove_player_item(uid,gid,item,quantity); await create_listing(uid,gid,char["username"],item,"item",quantity,price)
        await i.response.send_message(embed=discord.Embed(title="🏪 Listed!",description=f"{quantity}x {item} for {price}🪙",color=0x2ECC71))

    @app_commands.command(name="marketbuy",description="🏪 Buy listing.")
    @app_commands.describe(listing_id="ID")
    async def marketbuy(self,i:discord.Interaction,listing_id:int):
        gid=i.guild.id; uid=i.user.id
        if await check_jail(i): return
        char=await get_character(uid,gid)
        if not char: return await i.response.send_message(embed=discord.Embed(title="❌",description="Use `/start`!",color=0xE74C3C),ephemeral=True)
        l=await get_listing(listing_id)
        if not l: return await i.response.send_message(embed=discord.Embed(title="❌",description="Not found!",color=0xE74C3C),ephemeral=True)
        if l["seller_id"]==uid: return await i.response.send_message(embed=discord.Embed(title="❌",description="Own listing!",color=0xE74C3C),ephemeral=True)
        if char["coins"]<l["price"]: return await i.response.send_message(embed=discord.Embed(title="💸",description="Not enough!",color=0xE74C3C),ephemeral=True)
        k=await get_kingdom(gid); tax_r=k["tax_rate"] if k else 0; tax=int(l["price"]*tax_r)
        await add_coins(uid,gid,-l["price"]); await add_coins(l["seller_id"],gid,l["price"]-tax)
        if tax and k: await update_kingdom(gid,treasury=k["treasury"]+tax)
        await add_player_item(uid,gid,l["item_name"],l["item_type"],l["quantity"]); await remove_listing(listing_id)
        await i.response.send_message(embed=discord.Embed(title="✅ Bought!",description=f"{l['item_name']}x{l['quantity']}",color=0x2ECC71))

    @app_commands.command(name="cancellisting",description="🏪 Cancel your listing.")
    @app_commands.describe(listing_id="ID")
    async def cancellisting(self,i:discord.Interaction,listing_id:int):
        gid=i.guild.id
        if await check_jail(i): return
        l=await get_listing(listing_id)
        if not l or l["seller_id"]!=i.user.id: return await i.response.send_message(embed=discord.Embed(title="❌",color=0xE74C3C),ephemeral=True)
        await add_player_item(i.user.id,gid,l["item_name"],l["item_type"],l["quantity"]); await remove_listing(listing_id)
        await i.response.send_message(embed=discord.Embed(title="✅ Cancelled",color=0xF39C12))

    @app_commands.command(name="offer",description="🤝 Trade offer!")
    @app_commands.describe(target="Player",item="Item",price="Price")
    async def offer(self,i:discord.Interaction,target:discord.Member,item:str,price:int):
        gid=i.guild.id
        if await check_jail(i): return
        if not await has_player_item(i.user.id,gid,item): return await i.response.send_message(embed=discord.Embed(title="❌",description="Don't have!",color=0xE74C3C),ephemeral=True)
        await i.response.send_message(embed=discord.Embed(title="🤝 Trade!",description=f"{i.user.display_name} offers **{item}** to {target.mention} for **{price}**🪙",color=0x3498DB),
            view=TradeView(i.user.id,target.id,item,price,gid))

async def setup(bot): await bot.add_cog(MarketplaceCog(bot))
