"""cogs/bank.py — Bank with guild_id."""
import discord
from discord import app_commands
from discord.ext import commands,tasks
from datetime import datetime,timedelta
from database import (get_character,add_coins,get_bank_account,ensure_bank_account,update_bank,
    get_active_loan,create_loan,repay_loan,is_king,is_wallet_locked)
from helpers import check_jail

class BankCog(commands.Cog):
    def __init__(self,bot): self.bot=bot; self.interest.start(); self.loan_penalty.start()
    def cog_unload(self): self.interest.cancel(); self.loan_penalty.cancel()
    @tasks.loop(hours=24)
    async def interest(self):
        import aiosqlite; from database import DB_PATH
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT * FROM bank_accounts WHERE savings>0") as c:
                for r in await c.fetchall(): await db.execute("UPDATE bank_accounts SET savings=savings+? WHERE user_id=? AND guild_id=?",(int(r[2]*0.05),r[0],r[1]))
            await db.commit()
    @tasks.loop(hours=24)
    async def loan_penalty(self):
        import aiosqlite; from database import DB_PATH; now=datetime.utcnow()
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory=aiosqlite.Row
            async with db.execute("SELECT * FROM loans WHERE repaid=0") as c:
                for l in await c.fetchall():
                    if now>datetime.fromisoformat(l["due_at"]): await db.execute("UPDATE loans SET amount=amount+? WHERE id=?",(int(l["amount"]*0.2),l["id"]))
            await db.commit()
    @interest.before_loop
    async def b1(self): await self.bot.wait_until_ready()
    @loan_penalty.before_loop
    async def b2(self): await self.bot.wait_until_ready()

    @app_commands.command(name="bank",description="🏦 Bank account.")
    async def bank(self,interaction:discord.Interaction):
        gid=interaction.guild.id; uid=interaction.user.id
        if await check_jail(interaction): return
        char=await get_character(uid,gid)
        if not char: return await interaction.response.send_message(embed=discord.Embed(title="❌",description="Use `/start`!",color=0xE74C3C),ephemeral=True)
        await ensure_bank_account(uid,gid); acc=await get_bank_account(uid,gid); loan=await get_active_loan(uid,gid)
        e=discord.Embed(title="🏦 Bank",color=0x3498DB)
        e.add_field(name="👛 Wallet",value=f"`{char['coins']}`🪙",inline=True)
        e.add_field(name="🏦 Bank",value=f"`{acc['balance']}`🪙",inline=True)
        e.add_field(name="💎 Savings",value=f"`{acc['savings']}`🪙 (5%/day)",inline=True)
        if loan: e.add_field(name="📋 Loan",value=f"Owe `{loan['amount']}`🪙",inline=False)
        if await is_wallet_locked(uid, gid):
            e.add_field(name="🔒",value="Wallet locked — thieves cannot steal your coins.",inline=False)
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="deposit",description="🏦 Deposit coins.")
    @app_commands.describe(amount="Amount")
    async def deposit(self,interaction:discord.Interaction,amount:int):
        gid=interaction.guild.id; uid=interaction.user.id
        if await check_jail(interaction): return
        char=await get_character(uid,gid)
        if not char or char["coins"]<amount or amount<=0: return await interaction.response.send_message(embed=discord.Embed(title="❌",description="Invalid!",color=0xE74C3C),ephemeral=True)
        await ensure_bank_account(uid,gid); await add_coins(uid,gid,-amount)
        acc=await get_bank_account(uid,gid); await update_bank(uid,gid,balance=acc["balance"]+amount)
        await interaction.response.send_message(embed=discord.Embed(title="🏦 Deposited!",description=f"**{amount}**🪙",color=0x2ECC71))

    @app_commands.command(name="withdraw",description="🏦 Withdraw coins.")
    @app_commands.describe(amount="Amount")
    async def withdraw(self,interaction:discord.Interaction,amount:int):
        gid=interaction.guild.id; uid=interaction.user.id
        if await check_jail(interaction): return
        await ensure_bank_account(uid,gid); acc=await get_bank_account(uid,gid)
        if acc["balance"]<amount or amount<=0: return await interaction.response.send_message(embed=discord.Embed(title="❌",description="Not enough!",color=0xE74C3C),ephemeral=True)
        await update_bank(uid,gid,balance=acc["balance"]-amount); await add_coins(uid,gid,amount)
        await interaction.response.send_message(embed=discord.Embed(title="🏦 Withdrawn!",description=f"**{amount}**🪙",color=0x2ECC71))

    @app_commands.command(name="savings",description="💎 Save coins (5%/day, 3-day lock).")
    @app_commands.describe(amount="Amount")
    async def savings(self,interaction:discord.Interaction,amount:int):
        gid=interaction.guild.id; uid=interaction.user.id
        if await check_jail(interaction): return
        char=await get_character(uid,gid)
        if not char or char["coins"]<amount or amount<=0: return await interaction.response.send_message(embed=discord.Embed(title="❌",description="Invalid!",color=0xE74C3C),ephemeral=True)
        await ensure_bank_account(uid,gid); acc=await get_bank_account(uid,gid)
        await add_coins(uid,gid,-amount); await update_bank(uid,gid,savings=acc["savings"]+amount,savings_locked_until=(datetime.utcnow()+timedelta(days=3)).isoformat())
        await interaction.response.send_message(embed=discord.Embed(title="💎 Saved!",description=f"**{amount}**🪙 locked 3 days, 5%/day interest",color=0x9B59B6))

    @app_commands.command(name="loan",description="📋 Borrow coins (max 500, King:2000).")
    @app_commands.describe(amount="Amount")
    async def loan(self,interaction:discord.Interaction,amount:int):
        gid=interaction.guild.id; uid=interaction.user.id
        if await check_jail(interaction): return
        char=await get_character(uid,gid)
        if not char: return await interaction.response.send_message(embed=discord.Embed(title="❌",description="Use `/start`!",color=0xE74C3C),ephemeral=True)
        if await get_active_loan(uid,gid): return await interaction.response.send_message(embed=discord.Embed(title="❌",description="Repay existing loan!",color=0xE74C3C),ephemeral=True)
        mx=2000 if await is_king(gid,uid) else 500
        if amount<=0 or amount>mx: return await interaction.response.send_message(embed=discord.Embed(title="❌",description=f"Max {mx}!",color=0xE74C3C),ephemeral=True)
        await create_loan(uid,gid,amount); await add_coins(uid,gid,amount)
        await interaction.response.send_message(embed=discord.Embed(title="📋 Loan!",description=f"**{amount}**🪙. Repay in 7 days!",color=0xF1C40F))

    @app_commands.command(name="repayloan",description="📋 Repay loan.")
    async def repayloan(self,interaction:discord.Interaction):
        gid=interaction.guild.id; uid=interaction.user.id
        if await check_jail(interaction): return
        loan=await get_active_loan(uid,gid)
        if not loan: return await interaction.response.send_message(embed=discord.Embed(title="❌",description="No loan!",color=0x95A5A6),ephemeral=True)
        char=await get_character(uid,gid)
        if char["coins"]<loan["amount"]: return await interaction.response.send_message(embed=discord.Embed(title="💸",description=f"Need {loan['amount']}🪙!",color=0xE74C3C),ephemeral=True)
        await add_coins(uid,gid,-loan["amount"]); await repay_loan(uid,gid)
        await interaction.response.send_message(embed=discord.Embed(title="✅ Repaid!",color=0x2ECC71))

async def setup(bot): await bot.add_cog(BankCog(bot))
