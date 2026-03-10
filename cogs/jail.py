"""cogs/jail.py — Jail system: jailstatus, fine, bail, pardon, jail list, crimelog, patrol."""
import random, discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from database import (get_character, get_active_jail, release_prisoner, get_all_prisoners,
    get_crime_log, add_coins, get_kingdom, update_kingdom, jail_player,
    is_king, is_royal_soldier, remove_royal_soldier, add_xp,
    get_cooldown, set_cooldown, check_cooldown, revoke_lawyer, get_lawyer)

class JailCog(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @app_commands.command(name="jailstatus", description="⛓️ View your jail status.")
    async def jailstatus(self, interaction: discord.Interaction):
        gid = interaction.guild.id; uid = interaction.user.id
        jail = await get_active_jail(uid, gid)
        if not jail:
            return await interaction.response.send_message(embed=discord.Embed(
                title="✅ Thou Art Free!", description="No chains bind thee, citizen!", color=0x2ECC71), ephemeral=True)
        jailed_at = datetime.fromisoformat(jail["jailed_at"])
        remaining = (jail["sentence_hours"] * 3600) - (datetime.utcnow() - jailed_at).total_seconds()
        h, rem = divmod(max(0, int(remaining)), 3600); m = rem // 60
        e = discord.Embed(title="⛓️ Dungeon Record", color=0x2C2F33,
            description=f"🏛️ *By order of the Kingdom Court, thou hast been imprisoned!*\n\n"
                        f"⚖️ **Crime:** {jail['crime']}\n"
                        f"⏳ **Sentence:** {jail['sentence_hours']}h\n"
                        f"⏳ **Remaining:** {h}h {m}m\n"
                        f"💰 **Fine:** `{jail['fine_amount']}` 🪙\n"
                        f"🔓 **Bail:** `{jail['bail_amount']}` 🪙\n\n"
                        f"*Use `/fine` to pay thy debt to the Crown, or beseech an ally to `/bail` thee out!*")
        e.set_footer(text="⚔️ Kingdom Court • Justice is swift and merciless")
        await interaction.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(name="fine", description="💰 Pay your fine to be released!")
    async def fine(self, interaction: discord.Interaction):
        gid = interaction.guild.id; uid = interaction.user.id
        jail = await get_active_jail(uid, gid)
        if not jail:
            return await interaction.response.send_message(embed=discord.Embed(
                title="✅", description="Thou art not imprisoned!", color=0x2ECC71), ephemeral=True)
        char = await get_character(uid, gid)
        if not char or char["coins"] < jail["fine_amount"]:
            return await interaction.response.send_message(embed=discord.Embed(
                title="💸 Insufficient Coin!", description=f"Thy coffers hold but `{char['coins'] if char else 0}` 🪙.\n"
                f"The fine demands `{jail['fine_amount']}` 🪙!\n*Thou must toil harder, knave!*", color=0xE74C3C), ephemeral=True)
        await add_coins(uid, gid, -jail["fine_amount"])
        # Fine goes to treasury
        k = await get_kingdom(gid)
        if k: await update_kingdom(gid, treasury=k["treasury"] + jail["fine_amount"])
        await release_prisoner(uid, gid)
        e = discord.Embed(title="🔓 Freedom!", color=0x2ECC71,
            description=f"⚖️ *The dungeon gates creak open!*\n\n"
                        f"**{interaction.user.display_name}** has paid the fine of `{jail['fine_amount']}` 🪙!\n"
                        f"*Go forth and sin no more, lest the Crown's wrath find thee again!* 👑")
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="bail", description="🔓 Pay bail to free a prisoner (1.5× fine)!")
    @app_commands.describe(prisoner="The imprisoned soul")
    async def bail(self, interaction: discord.Interaction, prisoner: discord.Member):
        gid = interaction.guild.id; uid = interaction.user.id
        jail = await get_active_jail(prisoner.id, gid)
        if not jail:
            return await interaction.response.send_message(embed=discord.Embed(
                title="❌", description="That soul walks free already!", color=0xE74C3C), ephemeral=True)
        if uid == prisoner.id:
            return await interaction.response.send_message(embed=discord.Embed(
                title="❌", description="Thou canst not bail thyself! Use `/fine` instead.", color=0xE74C3C), ephemeral=True)
        char = await get_character(uid, gid)
        bail_cost = jail["bail_amount"]
        if not char or char["coins"] < bail_cost:
            return await interaction.response.send_message(embed=discord.Embed(
                title="💸", description=f"Need `{bail_cost}` 🪙 for bail!", color=0xE74C3C), ephemeral=True)
        await add_coins(uid, gid, -bail_cost)
        k = await get_kingdom(gid)
        if k: await update_kingdom(gid, treasury=k["treasury"] + bail_cost)
        await release_prisoner(prisoner.id, gid)
        e = discord.Embed(title="🔓 Bail Posted!", color=0x2ECC71,
            description=f"⚖️ *A noble deed!*\n\n**{interaction.user.display_name}** has posted `{bail_cost}` 🪙 bail "
                        f"to free **{prisoner.display_name}** from the dungeon!\n"
                        f"*The Crown thanks thee for thy generous contribution to the treasury!* 👑")
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="pardon", description="👑 (King only) Pardon a prisoner!")
    @app_commands.describe(target="Prisoner to pardon")
    async def pardon(self, interaction: discord.Interaction, target: discord.Member):
        gid = interaction.guild.id
        if not await is_king(gid, interaction.user.id):
            return await interaction.response.send_message(embed=discord.Embed(
                title="❌", description="Only the King may grant royal pardons!", color=0xE74C3C), ephemeral=True)
        jail = await get_active_jail(target.id, gid)
        if not jail:
            return await interaction.response.send_message(embed=discord.Embed(
                title="❌", description="That person is not imprisoned!", color=0xE74C3C), ephemeral=True)
        await release_prisoner(target.id, gid)
        e = discord.Embed(title="👑 ROYAL PARDON!", color=0xFFD700,
            description=f"📜 *Hear ye, hear ye!*\n\n"
                        f"By royal decree, His Majesty **{interaction.user.display_name}** "
                        f"has pardoned **{target.display_name}**!\n\n"
                        f"⚖️ Crime: *{jail['crime']}*\n"
                        f"All charges are hereby **DROPPED**. The prisoner walks free!\n\n"
                        f"*Let this act of mercy be remembered throughout the realm!* 🏰")
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="jail", description="⛓️ View all current prisoners.")
    async def jail_list(self, interaction: discord.Interaction):
        gid = interaction.guild.id
        prisoners = await get_all_prisoners(gid)
        prisoners = [p for p in prisoners if
            (datetime.utcnow() - datetime.fromisoformat(p["jailed_at"])).total_seconds() < p["sentence_hours"] * 3600]
        if not prisoners:
            return await interaction.response.send_message(embed=discord.Embed(
                title="⛓️ The Dungeon Stands Empty", description="*No wretched souls languish in the dark today!*\n"
                "All citizens walk free... for now. ⚖️", color=0x2C2F33))
        e = discord.Embed(title="⛓️ Kingdom Dungeon — Current Prisoners", color=0x2C2F33,
            description="*These poor souls rot behind bars!*\n")
        for p in prisoners:
            remaining = (p["sentence_hours"] * 3600) - (datetime.utcnow() - datetime.fromisoformat(p["jailed_at"])).total_seconds()
            h, rem = divmod(max(0, int(remaining)), 3600); m = rem // 60
            e.add_field(name=f"⛓️ {p['username']}",
                value=f"⚖️ {p['crime']}\n⏳ {h}h {m}m remaining\n💰 Fine: `{p['fine_amount']}`🪙 • Bail: `{p['bail_amount']}`🪙",
                inline=False)
        e.set_footer(text=f"⚔️ Kingdom Court • {len(prisoners)} prisoner(s)")
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="crimelog", description="📜 View crime history.")
    @app_commands.describe(target="Player (leave empty for yourself)")
    async def crimelog(self, interaction: discord.Interaction, target: discord.Member = None):
        gid = interaction.guild.id; uid = interaction.user.id
        t = target or interaction.user
        # Only King/Soldiers can view others
        if t.id != uid:
            if not (await is_king(gid, uid) or await is_royal_soldier(gid, uid)):
                return await interaction.response.send_message(embed=discord.Embed(
                    title="❌", description="Only the King and Royal Soldiers may inspect others' records!", color=0xE74C3C), ephemeral=True)
        log = await get_crime_log(t.id, gid)
        if not log:
            return await interaction.response.send_message(embed=discord.Embed(
                title=f"📜 {t.display_name}'s Record", description="*A spotless record! This citizen is beyond reproach.*", color=0x2ECC71))
        e = discord.Embed(title=f"📜 {t.display_name}'s Crime Record", color=0x2C2F33)
        for c in log[:15]:
            ts = c["timestamp"][:16] if c["timestamp"] else "Unknown"
            e.add_field(name=f"⚖️ {c['crime']}", value=f"📅 {ts} • Outcome: {c['outcome']}", inline=False)
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="patrol", description="⚔️ (Royal Soldier) Patrol for criminals! 2hr CD.")
    async def patrol(self, interaction: discord.Interaction):
        gid = interaction.guild.id; uid = interaction.user.id
        if not await is_royal_soldier(gid, uid):
            return await interaction.response.send_message(embed=discord.Embed(
                title="❌", description="Only Royal Soldiers can patrol!", color=0xE74C3C), ephemeral=True)
        # Check if soldier is jailed
        sj = await get_active_jail(uid, gid)
        if sj:
            await remove_royal_soldier(gid, uid)
            return await interaction.response.send_message(embed=discord.Embed(
                title="⛓️ Dishonored!", description="Thou art imprisoned! Thy Soldier rank has been **stripped**!", color=0xE74C3C))
        last = await get_cooldown(uid, gid, "patrol"); ready, rem = check_cooldown(last, 7200)
        if not ready:
            m, s = divmod(rem, 60); return await interaction.response.send_message(embed=discord.Embed(
                title="⏳", description=f"Next patrol in **{m}m**.", color=0xF39C12), ephemeral=True)
        await set_cooldown(uid, gid, "patrol")
        if random.random() < 0.4:
            crimes = ["pickpocketing a merchant", "defacing the royal banner", "smuggling contraband",
                      "disturbing the King's peace", "trespassing in the royal gardens"]
            crime = random.choice(crimes)
            await add_coins(uid, gid, 200); await add_xp(uid, gid, 50)
            e = discord.Embed(title="🚨 Criminal Caught!", color=0x2ECC71,
                description=f"⚔️ *Whilst on patrol, Soldier **{interaction.user.display_name}** caught a scoundrel!*\n\n"
                            f"⚖️ Crime: *{crime}*\n"
                            f"💰 Reward: **+200** 🪙\n✨ **+50** XP\n\n"
                            f"*The realm is safer thanks to thy vigilance!*")
        else:
            e = discord.Embed(title="🛡️ Patrol Complete", color=0x3498DB,
                description=f"⚔️ *Soldier **{interaction.user.display_name}** patrolled the realm.*\n\n"
                            f"No criminals found. The streets are quiet tonight.\n"
                            f"*Remain vigilant, Soldier!*")
        await interaction.response.send_message(embed=e)

async def setup(bot): await bot.add_cog(JailCog(bot))
