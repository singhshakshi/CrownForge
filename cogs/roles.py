"""cogs/roles.py — Role commands with luck-based stealing, /reporttheft, /lockwallet."""
import random, discord
from discord import app_commands
from discord.ext import commands
from database import (get_character, update_character, add_coins, set_mood, get_cooldown, set_cooldown,
    check_cooldown, add_hunt_trophy, is_king, is_queen, increment_rival_plots, get_rival_plots,
    add_player_item, has_player_item, remove_player_item, jail_player, reset_rival_plots,
    get_kingdom, update_kingdom, is_wallet_locked, set_wallet_lock, log_steal,
    get_recent_steal, mark_steal_reported, log_report, count_false_reports,
    get_random_inventory_item, transfer_inventory_item, get_active_jail,
    release_prisoner, add_item_to_inventory, mark_steal_reimbursed,
    is_kingsguard, is_royal_soldier)
from cogs.character import ROLE_DATA, get_pronouns
from helpers import check_jail

HUNT_ANIMALS = {
    "common":[{"name":"Rabbit","emoji":"🐇","coins":15},{"name":"Deer","emoji":"🦌","coins":25},{"name":"Boar","emoji":"🐗","coins":20}],
    "rare":[{"name":"Wolf","emoji":"🐺","coins":50},{"name":"Bear","emoji":"🐻","coins":70},{"name":"Lion","emoji":"🦁","coins":60}],
    "premium":[{"name":"Dragon","emoji":"🐉","coins":200},{"name":"Phoenix","emoji":"🐦‍🔥","coins":250},{"name":"White Tiger","emoji":"🐅","coins":180}],
}
CRAFT_RECIPES = {
    "Health Potion":{"ingredients":{"Magic Herb":2},"sell_price":150,"desc":"Restores 80 HP"},
    "Attack Elixir":{"ingredients":{"Magic Herb":1,"Tomato":2},"sell_price":200,"desc":"+20 ATK 1hr"},
    "Defense Brew":{"ingredients":{"Magic Herb":1,"Potato":2},"sell_price":200,"desc":"+20 DEF 1hr"},
}
CHAOS=["💸 Tax Surge! All lose 50🪙!","👹 Monster Invasion!","🌑 Dark Curse on the King!","🎪 Festival! Random bonus!","🔥 Market Fire!"]

# ═══ STEAL FLAVOR TEXT ═══
EPIC_FAIL_MSGS = [
    "👢 **{thief}** tripped over a loose cobblestone and landed face-first in front of the Royal Guard. The guard didn't even need to chase — he just stood there, arms crossed, shaking his head.",
    "🐔 **{thief}** snuck up behind **{victim}** but accidentally stepped on a chicken. The chicken squawked so loud the entire marketplace turned to stare. Guards were already on the way.",
    "💨 **{thief}** reached for **{victim}**'s coin purse but grabbed their own belt instead, yanking their pants down in the town square. The guards arrested him — for indecency AND theft.",
    "🏺 **{thief}** tried to make a dramatic getaway but crashed into a pottery cart. Covered in clay shards and shame, the Royal Guard found him whimpering under a broken vase.",
    "🪤 **{thief}** picked the wrong mark — **{victim}** had a mousetrap in their pocket. The scream echoed across three districts. Guards didn't even need directions.",
]
CLOSE_CALL_MSGS = [
    "👁️ **{thief}** got *this* close to **{victim}**'s coins but a guard turned the corner at the worst possible moment. He vanished into the shadows empty-handed, heart pounding.",
    "🌫️ **{thief}** blended into the crowd like smoke — almost had it — but a street vendor shouted 'THIEF!' at someone else entirely. Panicking, he bolted. No coins, no charges.",
    "🐈 **{thief}** was about to make the grab when a stray cat jumped on his face. By the time he peeled it off, **{victim}** had moved on. The cat stared at him judgmentally.",
    "🔔 **{thief}** brushed against **{victim}**'s coin pouch and it jingled. They locked eyes. Time froze. Then **{thief}** pretended to be adjusting their cloak and walked away whistling badly.",
]
SUCCESS_LOW_MSGS = [
    "🌑 Like a shadow in the night, **{thief}** vanished with **{amount}** 🪙 before **{victim}** even blinked. A clean, if modest, heist.",
    "🤫 **{thief}** slipped his fingers into **{victim}**'s coin purse smooth as butter. **{amount}** 🪙 lighter, **{victim}** won't notice until they try to buy bread.",
    "🎭 '**Pardon me, good citizen**,' whispered **{thief}**, bumping into **{victim}**. By the time **{victim}** said '*No worries*,' they were already **{amount}** 🪙 poorer.",
]
SUCCESS_MED_MSGS = [
    "🦊 **{thief}** pulled off a masterful distraction — pointed at the sky and yelled 'DRAGON!' While **{victim}** looked up, **{amount}** 🪙 vanished from their belt.",
    "💃 One elegant twirl, one strategic bump, and **{thief}** waltzed away with **{amount}** 🪙 from **{victim}**. They didn't feel a thing. *Art.*",
    "🌙 Under moonlight, **{thief}** moved like liquid silk. **{victim}**'s coin pouch was sliced clean. **{amount}** 🪙 — gone before the breeze settled.",
]
SUCCESS_HIGH_MSGS = [
    "⚡ In a blur of hands and confidence, **{thief}** lifted **{amount}** 🪙 off **{victim}** with surgical precision. Even the guards were impressed (quietly).",
    "🎪 **{thief}** put on an entire street performance as a distraction. By the finale, **{victim}** was applauding — and **{amount}** 🪙 lighter. Standing ovation... of theft.",
    "🐍 Serpent-like, **{thief}** slithered through the crowd and extracted **{amount}** 🪙 from **{victim}** without disturbing a single thread on their outfit. *Perfection.*",
]
LEGENDARY_MSGS = [
    "👑💀 **THE HEIST OF THE CENTURY!** **{thief}** didn't just steal coins — he stole **{victim}**'s dignity. **{amount}** 🪙 AND their precious **{item}** vanished in a flash of pure criminal genius. Bards will sing of this betrayal for generations.",
    "🔥🎭 **LEGENDARY HEIST!** Time seemed to slow as **{thief}** executed the most audacious theft the kingdom has ever witnessed. **{amount}** 🪙 AND **{item}** — plucked from **{victim}** like fruit from a sleeping dragon's hoard.",
]

class RolesCog(commands.Cog):
    def __init__(self,bot): self.bot=bot

    @app_commands.command(name="switchrole",description="🔄 Switch role (Lvl 5+, 200🪙).")
    @app_commands.describe(role="New role")
    @app_commands.choices(role=[app_commands.Choice(name=n,value=n) for n in ["Warrior","Mage","Thief","Worker","Rival","Commoner"]])
    async def switchrole(self,interaction:discord.Interaction,role:app_commands.Choice[str]):
        gid=interaction.guild.id; uid=interaction.user.id
        if await check_jail(interaction): return
        char=await get_character(uid,gid)
        if not char: return await interaction.response.send_message(embed=discord.Embed(title="❌",description="Use `/start`!",color=0xE74C3C),ephemeral=True)
        if char["level"]<5: return await interaction.response.send_message(embed=discord.Embed(title="❌",description="Need Lvl 5!",color=0xE74C3C),ephemeral=True)
        if char["coins"]<200: return await interaction.response.send_message(embed=discord.Embed(title="💸",description="Need 200🪙!",color=0xE74C3C),ephemeral=True)
        rv=role.value; rd=ROLE_DATA.get(rv)
        await add_coins(uid,gid,-200); await update_character(uid,gid,**{"class":rv})
        await interaction.response.send_message(embed=discord.Embed(title=f"{rd['emoji']} Now a {rv}!",color=rd["color"]))

    @app_commands.command(name="steal",description="🗡️ (Thief) Steal coins with style! 30min CD per target.")
    @app_commands.describe(target="Victim to pickpocket")
    async def steal(self,interaction:discord.Interaction,target:discord.Member):
        gid=interaction.guild.id; uid=interaction.user.id
        if await check_jail(interaction): return
        char=await get_character(uid,gid)
        if not char: return await interaction.response.send_message(embed=discord.Embed(title="❌",description="Use `/start`!",color=0xE74C3C),ephemeral=True)
        if char["class"]!="Thief": return await interaction.response.send_message(embed=discord.Embed(title="❌",description="Only the nimble fingers of a **Thief** may attempt this!",color=0xE74C3C),ephemeral=True)
        if target.id==uid or target.bot: return await interaction.response.send_message(embed=discord.Embed(title="❌",description="Invalid target!",color=0xE74C3C),ephemeral=True)
        tc=await get_character(target.id,gid)
        if not tc: return await interaction.response.send_message(embed=discord.Embed(title="❌",description="Target has no character!",color=0xE74C3C),ephemeral=True)

        tn, vn = interaction.user.display_name, target.display_name

        # ═══ KING — COMPLETELY IMPOSSIBLE ═══
        if await is_king(gid, target.id):
            await jail_player(uid, gid, "Attempted theft from the King", 2, 300, 450, target.id)
            await add_coins(uid, gid, -300)
            await interaction.response.send_message(embed=discord.Embed(title="👑 YOU DARE STEAL FROM THE KING?!",
                description=f"*You reached for the royal coin purse — and the Royal Guard spotted you instantly.*\n\n"
                f"⛓️ **JAILED for 2 hours!**\n💰 Fine: **300** 🪙 • Bail: **450** 🪙\n\n"
                f"*The audacity. The sheer, breathtaking audacity.* 👑",
                color=0xE74C3C), ephemeral=True)
            # Notify King
            try:
                king_member = interaction.guild.get_member(target.id)
                if king_member:
                    await king_member.send(embed=discord.Embed(title="🚨 Theft Attempt on the Crown!",
                        description=f"**{tn}** attempted to steal from you, Your Majesty!\n"
                        f"He has been thrown in the dungeon for his audacity. 👑", color=0xFFD700))
            except: pass
            return

        # Per-target 30min cooldown
        cd_key=f"steal_{target.id}"
        last=await get_cooldown(uid,gid,cd_key); ready,rem=check_cooldown(last,1800)
        if not ready:
            m,s=divmod(rem,60)
            return await interaction.response.send_message(embed=discord.Embed(title="⏳ Patience, Thief",description=f"**{target.display_name}** is on alert! Steal again in **{m}m {s}s**.\n*A wise thief never strikes the same mark twice in a row.*",color=0xF39C12),ephemeral=True)

        # General cooldown from close calls (10 min after a close call)
        glast=await get_cooldown(uid,gid,"steal_close_call"); gready,grem=check_cooldown(glast,600)
        if not gready:
            m,s=divmod(grem,60)
            return await interaction.response.send_message(embed=discord.Embed(title="⏳ Lay Low",description=f"The guards are still suspicious! Wait **{m}m {s}s**.\n*After that close call, best to lay low for a while.*",color=0xF39C12),ephemeral=True)

        # ═══ WALLET LOCK CHECK ═══
        if await is_wallet_locked(target.id, gid):
            await interaction.response.send_message(embed=discord.Embed(title="🔒 Impenetrable!",
                description=f"*You eyed **{vn}**'s coin purse... only to discover it's locked with a mechanism forged by the Kingdom's finest blacksmith.*\n\n"
                f"🔒 The lock laughed at you. Yes, the lock. It has a face. It's smirking.\n\n"
                f"*Perhaps try a less... prepared target?*",color=0xF1C40F), ephemeral=True)
            # Notify victim
            try:
                await target.send(embed=discord.Embed(title="🔒 Someone Tried to Steal From You!",
                    description=f"A thief attempted to pickpocket your wallet, but your **wallet lock** held strong! 🛡️\n\n"
                    f"*Your coins are safe. The lock does its job well.*",color=0x2ECC71))
            except: pass
            return

        # ═══ AUTHORITY-BASED DIFFICULTY ═══
        difficulty_bonus = 0
        difficulty_label = ""
        target_is_queen = await is_queen(gid, target.id)
        target_is_guard = await is_kingsguard(gid, target.id)
        target_is_soldier = await is_royal_soldier(gid, target.id)
        target_role = tc["class"]

        if target_is_queen:
            difficulty_bonus = 40; difficulty_label = "👑 Queen — Extreme difficulty (+40)"
        elif target_is_guard:
            difficulty_bonus = 30; difficulty_label = "🛡️ Kingsguard — Very hard (+30)"
        elif target_is_soldier:
            difficulty_bonus = 20; difficulty_label = "⚔️ Royal Soldier — Hard (+20)"
        elif target_role in ("Warrior", "Mage"):
            difficulty_bonus = 10; difficulty_label = f"{'⚔️' if target_role == 'Warrior' else '🔮'} {target_role} — Challenging (+10)"

        # ═══ ROLL THE DICE ═══
        roll = random.randint(1, 100)
        fail_threshold = 20 + difficulty_bonus  # base: 1-20 fail, adjusted by authority

        # Set per-target cooldown regardless of outcome
        await set_cooldown(uid, gid, cd_key)

        # ═══ EPIC FAIL (roll 1-10, always) ═══
        if roll <= 10:
            penalty=max(1,int(char["coins"]*0.15))
            await add_coins(uid,gid,-penalty)
            await jail_player(uid,gid,"Caught stealing red-handed",2,300,450,target.id)
            msg = random.choice(EPIC_FAIL_MSGS).format(thief=tn, victim=vn)
            e = discord.Embed(title="💀 EPIC FAIL! 💀", color=0xE74C3C,
                description=f"{msg}\n\n"
                f"⛓️ **JAILED for 2 hours!**\n"
                f"💰 Fine: **300** 🪙 • Bail: **450** 🪙\n"
                f"💸 Dropped **{penalty}** 🪙 while fleeing!\n"
                f"🎲 Roll: `{roll}`/100")
            if difficulty_label: e.add_field(name="📊 Target Difficulty", value=difficulty_label, inline=False)
            e.set_footer(text="⚔️ RPG Bot • Crime doesn't always pay")
            await interaction.response.send_message(embed=e)
            try:
                await target.send(embed=discord.Embed(title="🚨 Thief Caught!",color=0x2ECC71,
                    description=f"**{tn}** tried to steal from you and was caught by the Royal Guard!\n"
                    f"He has been thrown in the dungeon for 2 hours. Your coins are safe! 🛡️"))
            except: pass
            # If Queen → auto-report to King
            if target_is_queen:
                k = await get_kingdom(gid)
                if k and k.get("king_id"):
                    try:
                        km = interaction.guild.get_member(k["king_id"])
                        if km: await km.send(embed=discord.Embed(title="🚨 Someone Targeted the Queen!",
                            description=f"**{tn}** attempted to steal from the Queen and was caught!\nHe is now in the dungeon. 👑",color=0xFFD700))
                    except: pass
            return

        # ═══ AUTHORITY FAIL (roll 11 to fail_threshold) ═══
        if roll <= fail_threshold:
            if roll <= 20:
                # Close call (base range 11-20)
                await set_cooldown(uid, gid, "steal_close_call")
                msg = random.choice(CLOSE_CALL_MSGS).format(thief=tn, victim=vn)
                e = discord.Embed(title="😰 Close Call!", color=0xF39C12,
                    description=f"{msg}\n\n"
                    f"💨 Escaped with **nothing**. No coins gained.\n"
                    f"⏳ **10 minute cooldown** applied — the guards are on alert.\n"
                    f"🎲 Roll: `{roll}`/100")
            else:
                # Authority-blocked (roll 21 to fail_threshold)
                e = discord.Embed(title="🛡️ Authority Blocked!", color=0xF39C12,
                    description=f"*You crept toward **{vn}**, but their authority and protection made it impossible.*\n\n"
                    f"💨 Escaped with **nothing**. The target's rank made this steal too risky.\n"
                    f"🎲 Roll: `{roll}`/100 (needed >`{fail_threshold}` to succeed)")
            if difficulty_label: e.add_field(name="📊 Target Difficulty", value=difficulty_label, inline=False)
            e.set_footer(text="⚔️ RPG Bot • Know thy target's rank")
            await interaction.response.send_message(embed=e)
            # Silent victim alert for close calls
            if roll <= 20:
                try:
                    await target.send(embed=discord.Embed(title="🔍 Suspicious Activity!",color=0xF39C12,
                        description="Someone was lurking near your coin purse but fled before they could grab anything.\n"
                        "Your coins are safe... *for now.* 👀\nConsider `/lockwallet` for protection!"))
                except: pass
            # If Queen → auto-report to King on ANY fail
            if target_is_queen:
                k = await get_kingdom(gid)
                if k and k.get("king_id"):
                    try:
                        km = interaction.guild.get_member(k["king_id"])
                        if km: await km.send(embed=discord.Embed(title="⚠️ Suspicious Activity Near the Queen",
                            description=f"Someone attempted to steal from the Queen but failed.\n*The Royal Guard is on high alert.* 👑",color=0xF39C12))
                    except: pass
            return

        # ═══ ROLL 21-100: SUCCESSFUL STEAL ═══
        wallet = tc["coins"]
        if wallet <= 0:
            return await interaction.response.send_message(embed=discord.Embed(title="💸 Empty Pockets",
                description=f"**{vn}** has no coins! Even the most skilled thief can't steal what doesn't exist.",color=0x95A5A6))

        item_stolen = None
        item_name = None

        if roll <= 50:
            # 8-12% of wallet
            pct = random.randint(8, 12) / 100
            stolen = max(1, int(wallet * pct))
            msgs = SUCCESS_LOW_MSGS
            reimburse_pct = 0.20
            tier = "low"
        elif roll <= 80:
            # 13-20% of wallet
            pct = random.randint(13, 20) / 100
            stolen = max(1, int(wallet * pct))
            msgs = SUCCESS_MED_MSGS
            reimburse_pct = 0.20
            tier = "medium"
        elif roll <= 99:
            # 21-30% of wallet
            pct = random.randint(21, 30) / 100
            stolen = max(1, int(wallet * pct))
            msgs = SUCCESS_HIGH_MSGS
            reimburse_pct = 0.30
            tier = "high"
        else:
            # ROLL 100: LEGENDARY — 35% + random item
            pct = 0.35
            stolen = max(1, int(wallet * pct))
            msgs = LEGENDARY_MSGS
            reimburse_pct = 0.40
            tier = "legendary"
            # Steal a random gear item
            item_stolen = await get_random_inventory_item(target.id, gid)
            if item_stolen:
                item_name = item_stolen["item_name"]
                await transfer_inventory_item(item_stolen["id"], uid, gid)

        # Transfer coins
        await add_coins(target.id, gid, -stolen)
        await add_coins(uid, gid, stolen)
        await set_mood(target.id, gid, "sad")
        await set_mood(uid, gid, "happy")

        # Log the steal
        await log_steal(gid, uid, target.id, stolen, item_name)

        # Kingdom reimbursement
        reimburse_amount = int(stolen * reimburse_pct)
        k = await get_kingdom(gid)
        reimbursed = False
        if k and k["treasury"] >= reimburse_amount and reimburse_amount > 0:
            await update_kingdom(gid, treasury=k["treasury"] - reimburse_amount)
            await add_coins(target.id, gid, reimburse_amount)
            reimbursed = True

        # Build embed
        if tier == "legendary" and item_name:
            msg = random.choice(msgs).format(thief=tn, victim=vn, amount=stolen, item=item_name)
        else:
            msg = random.choice(msgs).format(thief=tn, victim=vn, amount=stolen)

        color = {
            "low": 0x2ECC71, "medium": 0x3498DB, "high": 0x9B59B6, "legendary": 0xFFD700
        }[tier]
        title = {
            "low": "🗡️ Pickpocket!", "medium": "🦊 Smooth Steal!",
            "high": "⚡ Master Thief!", "legendary": "💎✨ LEGENDARY HEIST! ✨💎"
        }[tier]

        e = discord.Embed(title=title, color=color, description=f"{msg}")
        e.add_field(name="💰 Stolen", value=f"**{stolen}** 🪙", inline=True)
        if item_name:
            e.add_field(name="📦 Item Stolen!", value=f"**{item_name}**", inline=True)
        e.add_field(name="🎲 Roll", value=f"`{roll}`/100 ({int(pct*100)}%)", inline=True)

        if reimbursed:
            e.add_field(name="🏛️ Kingdom Reimbursement", value=f"**{vn}** will be reimbursed **{reimburse_amount}** 🪙 from the treasury.", inline=False)
        elif reimburse_amount > 0:
            e.add_field(name="🏛️ Treasury Empty", value=f"The kingdom treasury is empty — no reimbursement for **{vn}**.", inline=False)

        e.add_field(name="⚖️ Justice", value=f"**{vn}** has 30 seconds to use `/reporttheft @{tn}` to report this crime!", inline=False)
        if difficulty_label: e.add_field(name="📊 Target Difficulty", value=difficulty_label, inline=False)
        e.set_footer(text="⚔️ RPG Bot • /reporttheft within 30s to catch the thief!")
        await interaction.response.send_message(embed=e)

        # DM victim
        try:
            ve = discord.Embed(title="🚨 You've Been Robbed!", color=0xE74C3C,
                description=f"A thief has stolen **{stolen}** 🪙 from your coin purse!\n"
                + (f"They also took your **{item_name}**!\n" if item_name else "")
                + (f"\n🏛️ The kingdom reimbursed you **{reimburse_amount}** 🪙.\n" if reimbursed else "")
                + f"\n⚖️ **You have 30 SECONDS** to use `/reporttheft @{tn}` in the server to catch the thief and get your coins back!")
            await target.send(embed=ve)
        except: pass

    @app_commands.command(name="reporttheft",description="⚖️ Report a thief! Must use within 30s of being robbed.")
    @app_commands.describe(thief="The scoundrel who robbed you")
    async def reporttheft(self,interaction:discord.Interaction,thief:discord.Member):
        gid=interaction.guild.id; uid=interaction.user.id

        # Jailed players can't report
        if await get_active_jail(uid, gid):
            return await interaction.response.send_message(embed=discord.Embed(title="⛓️",
                description="Thou canst not report from the dungeon!", color=0x2C2F33), ephemeral=True)

        if thief.id == uid:
            return await interaction.response.send_message(embed=discord.Embed(title="❌",
                description="You can't report yourself, you fool.", color=0xE74C3C), ephemeral=True)

        # Check for a valid recent steal (within 30 seconds, unreported)
        steal = await get_recent_steal(gid, thief.id, uid, seconds=30)

        if not steal:
            # Check if there WAS a steal but it's too late
            old_steal = await get_recent_steal(gid, thief.id, uid, seconds=86400)
            if old_steal:
                # There was a steal but >30 seconds ago
                await interaction.response.send_message(embed=discord.Embed(title="⏰ Too Late!",
                    description="*The moment has passed. The kingdom's attention has moved on.*\n\n"
                    "The 30-second window to report has closed. The thief walks free... this time.\n"
                    "*Perhaps next time, react faster.*",color=0x95A5A6), ephemeral=True)
                return

            # No steal found at all → false report
            false_count = await count_false_reports(uid, gid) + 1
            await log_report(gid, uid, thief.id, "", "false")

            if false_count >= 3 and false_count % 3 == 0:
                # Fine for repeated false reports
                await add_coins(uid, gid, -100)
                e = discord.Embed(title="🙄 Enough Is Enough!", color=0xE74C3C,
                    description=f"*The Royal Court has NO time for thy baseless accusations!*\n\n"
                    f"This is thy **{false_count}th** false report. **100** 🪙 has been seized as a **nuisance tax**.\n\n"
                    f"*'Perhaps if thou spent less time pointing fingers and more time earning coin, "
                    f"thy purse wouldn't be so light.'* — The Royal Judge 👨‍⚖️")
            else:
                e = discord.Embed(title="⚠️ False Report!", color=0xF39C12,
                    description=f"*The Court finds no evidence of theft by **{thief.display_name}**.*\n\n"
                    f"False reports: **{false_count}**/3 before a fine is imposed.\n"
                    f"*Do not waste the Crown's time with unfounded accusations, citizen!*")
            await interaction.response.send_message(embed=e, ephemeral=True)
            return

        # ═══ VALID REPORT ═══
        await mark_steal_reported(steal["id"])
        await log_report(gid, uid, thief.id, steal["timestamp"], "valid")

        # Jail the thief — 2 hours, 300 fine
        await jail_player(thief.id, gid, "Caught by victim's report after theft", 2, 300, 450, uid)

        # Return FULL stolen amount to victim (on top of any reimbursement already received)
        await add_coins(uid, gid, steal["amount"])
        await add_coins(thief.id, gid, -steal["amount"])

        # Return stolen item if any
        item_msg = ""
        if steal.get("item_stolen"):
            # Transfer item back
            item_msg = f"\n📦 The stolen **{steal['item_stolen']}** has been recovered!"

        # Civic reward
        await add_coins(uid, gid, 50)

        # Server announcement
        e = discord.Embed(title="⚖️ JUSTICE SERVED! ⚖️", color=0xFFD700,
            description=f"📜 *Hear ye, hear ye!*\n\n"
            f"⚖️ Justice moves fast in this kingdom! **{thief.display_name}** was caught **red-handed** "
            f"and dragged to the dungeons!\n\n"
            f"💰 **{steal['amount']}** 🪙 returned to **{interaction.user.display_name}**{item_msg}\n"
            f"🏆 **{interaction.user.display_name}** receives **50** 🪙 civic reward for swift justice!\n"
            f"⛓️ **{thief.display_name}** — **2 hours** in the dungeon, **300** 🪙 fine!\n\n"
            f"*Let this be a lesson to all who would steal from their fellow citizens!* 🏰")
        e.set_footer(text="⚔️ RPG Bot • Crime never pays... when victims fight back!")
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="lockwallet",description="🔒 Lock/unlock your wallet from thieves!")
    async def lockwallet(self,interaction:discord.Interaction):
        gid=interaction.guild.id; uid=interaction.user.id
        if await check_jail(interaction): return
        currently_locked = await is_wallet_locked(uid, gid)
        if currently_locked:
            await set_wallet_lock(uid, gid, False)
            await interaction.response.send_message(embed=discord.Embed(title="🔓 Wallet Unlocked!",
                description="*Thy coin purse is now accessible — and vulnerable.*\n"
                "Thieves can once again target thee. Live dangerously, citizen! ⚔️",color=0xF39C12))
        else:
            await set_wallet_lock(uid, gid, True)
            await interaction.response.send_message(embed=discord.Embed(title="🔒 Wallet Locked!",
                description="*Thy coin purse has been sealed with the finest Kingdom-grade lock!*\n"
                "No Thief can touch thy coins while locked. 🛡️\n\n"
                "*Use `/lockwallet` again to unlock.*",color=0x2ECC71))

    @app_commands.command(name="work",description="⛏️ (Worker) Work for coins. 2hr CD.")
    async def work(self,interaction:discord.Interaction):
        gid=interaction.guild.id; uid=interaction.user.id
        if await check_jail(interaction): return
        char=await get_character(uid,gid)
        if not char: return await interaction.response.send_message(embed=discord.Embed(title="❌",description="Use `/start`!",color=0xE74C3C),ephemeral=True)
        if char["class"]!="Worker": return await interaction.response.send_message(embed=discord.Embed(title="❌",description="Workers only!",color=0xE74C3C),ephemeral=True)
        last=await get_cooldown(uid,gid,"work"); ready,rem=check_cooldown(last,7200)
        if not ready: m,s=divmod(rem,60); return await interaction.response.send_message(embed=discord.Embed(title="⏳",description=f"Wait **{m}m**",color=0xF39C12),ephemeral=True)
        await set_cooldown(uid,gid,"work"); earnings=30+char["level"]*10+random.randint(0,20)
        await add_coins(uid,gid,earnings)
        await interaction.response.send_message(embed=discord.Embed(title="⛏️ Work Done!",description=f"Earned **{earnings}**🪙!",color=0xF39C12))

    @app_commands.command(name="craft",description="🔨 (Worker) Craft items.")
    @app_commands.describe(item="Item")
    @app_commands.choices(item=[app_commands.Choice(name=n,value=n) for n in CRAFT_RECIPES])
    async def craft(self,interaction:discord.Interaction,item:app_commands.Choice[str]):
        gid=interaction.guild.id; uid=interaction.user.id
        if await check_jail(interaction): return
        char=await get_character(uid,gid)
        if not char or char["class"]!="Worker": return await interaction.response.send_message(embed=discord.Embed(title="❌",description="Workers only!",color=0xE74C3C),ephemeral=True)
        r=CRAFT_RECIPES[item.value]
        for ing,qty in r["ingredients"].items():
            if not await has_player_item(uid,gid,ing,qty): return await interaction.response.send_message(embed=discord.Embed(title="❌",description=f"Need {qty}x {ing}!",color=0xE74C3C),ephemeral=True)
        for ing,qty in r["ingredients"].items(): await remove_player_item(uid,gid,ing,qty)
        await add_player_item(uid,gid,item.value,"crafted")
        await interaction.response.send_message(embed=discord.Embed(title=f"🔨 Crafted {item.value}!",description=r["desc"],color=0x2ECC71))

    @app_commands.command(name="hunt",description="🏹 (Warrior/King) Hunt! 30min CD.")
    async def hunt(self,interaction:discord.Interaction):
        gid=interaction.guild.id; uid=interaction.user.id
        if await check_jail(interaction): return
        char=await get_character(uid,gid)
        if not char: return await interaction.response.send_message(embed=discord.Embed(title="❌",description="Use `/start`!",color=0xE74C3C),ephemeral=True)
        ik=await is_king(gid,uid)
        if char["class"]!="Warrior" and not ik: return await interaction.response.send_message(embed=discord.Embed(title="❌",description="Warriors/King only!",color=0xE74C3C),ephemeral=True)
        last=await get_cooldown(uid,gid,"hunt"); ready,rem=check_cooldown(last,1800)
        if not ready: m,s=divmod(rem,60); return await interaction.response.send_message(embed=discord.Embed(title="⏳",description=f"Wait **{m}m**",color=0xF39C12),ephemeral=True)
        await set_cooldown(uid,gid,"hunt"); roll=random.random()
        if roll<0.05: e=discord.Embed(title="🏹 Empty Handed",color=0x95A5A6)
        elif roll<0.20:
            a=random.choice(HUNT_ANIMALS["premium"]); coins=a["coins"]+char["level"]*5
            await add_coins(uid,gid,coins); await add_hunt_trophy(uid,gid,a["name"])
            e=discord.Embed(title=f"🏆 {a['emoji']} {a['name']}!",description=f"+**{coins}**🪙 + Trophy!",color=0xFFD700)
        elif roll<0.50:
            a=random.choice(HUNT_ANIMALS["rare"]); coins=a["coins"]+char["level"]*3; await add_coins(uid,gid,coins)
            e=discord.Embed(title=f"✨ {a['emoji']} {a['name']}",description=f"+**{coins}**🪙",color=0x9B59B6)
        else:
            a=random.choice(HUNT_ANIMALS["common"]); coins=a["coins"]+char["level"]*2; await add_coins(uid,gid,coins)
            e=discord.Embed(title=f"🏹 {a['emoji']} {a['name']}",description=f"+**{coins}**🪙",color=0x2ECC71)
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="plot",description="😈 (Rival) Cause chaos! Daily CD.")
    async def plot(self,interaction:discord.Interaction):
        gid=interaction.guild.id; uid=interaction.user.id
        if await check_jail(interaction): return
        # Block during tournament
        from database import get_active_tournament
        t = await get_active_tournament(gid)
        if t:
            return await interaction.response.send_message(embed=discord.Embed(title="🏆 Tournament Active",
                description="👀 *The throne sits empty. Wait for a King to be crowned before plotting your takeover.*",
                color=0xF39C12),ephemeral=True)
        char=await get_character(uid,gid)
        if not char or char["class"]!="Rival": return await interaction.response.send_message(embed=discord.Embed(title="❌",description="Rivals only!",color=0xE74C3C),ephemeral=True)
        last=await get_cooldown(uid,gid,"plot"); ready,rem=check_cooldown(last,86400)
        if not ready: h,r=divmod(rem,3600); return await interaction.response.send_message(embed=discord.Embed(title="⏳",description=f"Wait **{h}h**",color=0xF39C12),ephemeral=True)
        await set_cooldown(uid,gid,"plot"); await increment_rival_plots(uid,gid)
        rp=await get_rival_plots(uid,gid); event=random.choice(CHAOS)
        e=discord.Embed(title="😈 The Rival Plots!",description=event,color=0xE91E63)
        if rp and rp["consecutive_plots"]>=3:
            e.add_field(name="⚠️ King Dethroned!",value="3 plots! Crown falls! ⚔️ A tournament will decide the new King!",inline=False)
            k=await get_kingdom(gid)
            old_king_name = None
            if k and k["king_id"]:
                kc = await get_character(k["king_id"], gid)
                old_king_name = kc["username"] if kc else "the King"
                await update_character(k["king_id"],gid,**{"class":"Warrior"})
                await update_kingdom(gid,king_id=None,queen_id=None)
            await reset_rival_plots(uid,gid)
            # Trigger tournament
            tc = self.bot.get_cog("TournamentCog")
            ch = interaction.channel
            if tc and ch:
                await tc.trigger_tournament(gid, ch,
                    f"The Rival's plots have toppled {old_king_name or 'the King'}! The realm needs a new ruler!")
        if rp and rp["consecutive_plots"]>3:
            await jail_player(uid,gid,"Excessive plotting (>3 in 24hrs)",4,500,750)
            e.add_field(name="⛓️ JAILED!",value="4 hours, 500🪙 fine!",inline=False)
        e.set_footer(text=f"Plots: {rp['consecutive_plots'] if rp else 1}")
        await interaction.response.send_message(embed=e)

async def setup(bot): await bot.add_cog(RolesCog(bot))

