"""cogs/kingdom.py — Kingdom hierarchy, /leavekingdom, /exiles, /challengeking."""
import discord, json, asyncio, random
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from database import (get_character, get_kingdom, ensure_kingdom, update_kingdom,
    add_kingsguard, remove_kingsguard, is_king, is_queen,
    get_kingsguard_list, add_royal_soldier, remove_royal_soldier, get_royal_soldiers,
    add_coins, wipe_player_data, log_leave, get_leave_log, get_active_jail,
    get_active_tournament, is_kingsguard, is_royal_soldier, get_lawyer,
    get_all_lawyers, get_total_players, get_richest_player, get_most_wanted,
    get_effective_stats, get_cooldown, set_cooldown, check_cooldown, set_mood,
    add_xp, add_player_item, update_character)
from helpers import check_jail

# ═══ LEAVE CONFIRMATION VIEW ═══
class LeaveConfirmView(discord.ui.View):
    def __init__(self, uid, gid, bot):
        super().__init__(timeout=60)
        self.uid, self.gid, self.bot = uid, gid, bot
        self.confirmed = False

    async def interaction_check(self, i):
        return i.user.id == self.uid

    @discord.ui.button(label="Confirm 🚪", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button):
        if self.confirmed: return
        self.confirmed = True; self.stop()
        gid, uid = self.gid, self.uid
        char = await get_character(uid, gid)
        if not char:
            return await interaction.response.edit_message(embed=discord.Embed(title="❌", description="No character found.", color=0xE74C3C), view=None)
        role, level, coins, name = char["class"], char["level"], char["coins"], char["username"]
        was_king = await is_king(gid, uid); was_queen = await is_queen(gid, uid)
        await log_leave(gid, uid, name, role, level, coins)
        if was_queen:
            k = await get_kingdom(gid)
            if k and k.get("king_id"):
                guild = interaction.guild
                if guild:
                    km = guild.get_member(k["king_id"])
                    if km:
                        try: await km.send(embed=discord.Embed(title="👑 The Queen Has Left!", description=f"**{name}** has abandoned the kingdom.", color=0xE74C3C))
                        except: pass
        await wipe_player_data(uid, gid)
        guild = interaction.guild; server_name = guild.name if guild else "the Kingdom"
        ch = guild.system_channel or (guild.text_channels[0] if guild and guild.text_channels else None)
        if ch:
            try: await ch.send(embed=discord.Embed(title="👋 A Soul Departs the Kingdom",
                description=f"👋 **{name}** the **{role}** has abandoned the kingdom of **{server_name}**.\n\n"
                f"Their lands have been seized, their coins scattered to the wind, and their name struck from the records.\n\n*May they find their path elsewhere.* 🍃", color=0x95A5A6))
            except: pass
        await interaction.response.edit_message(embed=discord.Embed(title="🌱 A New Beginning",
            description="You have left everything behind and returned to the kingdom as a stranger.\n\nType `/start` to begin your journey again from nothing.\n\n*Every legend starts somewhere.* ⚔️", color=0x2ECC71), view=None)
        if was_king:
            tc = self.bot.get_cog("TournamentCog")
            if tc and ch: await tc.trigger_tournament(gid, ch, f"King {name} has abandoned the throne! The kingdom needs a new ruler!")

    @discord.ui.button(label="Cancel ❌", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button):
        self.stop()
        await interaction.response.edit_message(embed=discord.Embed(title="❌ Cancelled", description="*You remain in the kingdom. Wise choice, citizen.*", color=0x95A5A6), view=None)

class QueenProposalView(discord.ui.View):
    def __init__(self, kid, tid, gid):
        super().__init__(timeout=120); self.kid, self.tid, self.gid = kid, tid, gid
    async def interaction_check(self, i):
        if i.user.id != self.tid: await i.response.send_message("❌", ephemeral=True); return False
        return True
    @discord.ui.button(label="Accept 👑", style=discord.ButtonStyle.success)
    async def accept(self, i, b):
        await update_kingdom(self.gid, queen_id=self.tid); self.stop()
        await i.response.edit_message(embed=discord.Embed(title="👑 A New Queen Is Crowned!",
            description=f"**{i.user.display_name}** is now Queen!", color=0xFFD700), view=None)
    @discord.ui.button(label="Decline ❌", style=discord.ButtonStyle.danger)
    async def decline(self, i, b):
        self.stop(); await i.response.edit_message(embed=discord.Embed(title="❌ Declined", color=0xE74C3C), view=None)

# ═══ CHALLENGE KING SYSTEM ═══
def _hp_bar(c, m, l=10):
    f = max(0, int((c / m) * l)) if m > 0 else 0; return "❤️" * f + "🖤" * (l - f)

class ChallengeAcceptView(discord.ui.View):
    """King sees this in DM. Accept or Decline the challenge."""
    def __init__(self, king_id, callback):
        super().__init__(timeout=600)  # 10 min
        self.king_id, self.callback, self.responded = king_id, callback, False
    async def interaction_check(self, i): return i.user.id == self.king_id
    @discord.ui.button(label="Accept ⚔️", style=discord.ButtonStyle.danger)
    async def accept(self, interaction, button):
        if self.responded: return
        self.responded = True; self.stop()
        await interaction.response.edit_message(embed=discord.Embed(title="⚔️ Challenge Accepted!",
            description="*Prepare thy blade! The duel for the Crown begins!*", color=0xE74C3C), view=None)
        await self.callback(True)
    @discord.ui.button(label="Decline 🏳️", style=discord.ButtonStyle.secondary)
    async def decline(self, interaction, button):
        if self.responded: return
        self.responded = True; self.stop()
        await interaction.response.edit_message(embed=discord.Embed(title="🏳️ Challenge Declined",
            description="*The crowd murmurs...*", color=0x95A5A6), view=None)
        await self.callback(False)
    async def on_timeout(self):
        if not self.responded: await self.callback(False)

class ChallengeDuelView(discord.ui.View):
    """1v1 tournament-style duel for the crown."""
    def __init__(self, p1id, p2id, p1s, p2s, p1n, p2n, result_future, phase="normal"):
        super().__init__(timeout=900)
        self.p1id, self.p2id = p1id, p2id
        self.p1s, self.p2s = p1s, p2s
        self.p1n, self.p2n = p1n, p2n
        self.result_future, self.phase = result_future, phase
        if phase == "normal":
            self.p1hp, self.p2hp = p1s["effective_max_hp"], p2s["effective_max_hp"]
        elif phase == "sudden_death":
            self.p1hp, self.p2hp = p1s["effective_max_hp"] // 2, p2s["effective_max_hp"] // 2
        else:
            self.p1hp, self.p2hp = p1s["effective_max_hp"] // 4, p2s["effective_max_hp"] // 4
        self.p1mx, self.p2mx = p1s["effective_max_hp"], p2s["effective_max_hp"]
        self.turn, self.tnum, self.log, self.ended = p1id, 1, [], False
        self.dmg_mult = 2.0 if phase == "lightning" else 1.0

    async def interaction_check(self, i):
        if i.user.id != self.turn:
            await i.response.send_message("❌ Not your turn!", ephemeral=True); return False
        return True
    def _embed(self):
        lbl = {"normal": "⚔️ Crown Challenge", "sudden_death": "⚡ Sudden Death!", "lightning": "🔥⚡ LIGHTNING ROUND ⚡🔥"}[self.phase]
        tn = self.p1n if self.turn == self.p1id else self.p2n
        e = discord.Embed(title=f"{lbl} — Turn {self.tnum}", description=f"**{tn}**'s turn!", color=0xFF6B35)
        e.add_field(name=f"🔴 {self.p1n}", value=f"`{max(0,self.p1hp)}`/`{self.p1mx}`\n{_hp_bar(self.p1hp, self.p1mx)}", inline=True)
        e.add_field(name=f"🔵 {self.p2n}", value=f"`{max(0,self.p2hp)}`/`{self.p2mx}`\n{_hp_bar(self.p2hp, self.p2mx)}", inline=True)
        if self.log: e.add_field(name="📜", value="\n".join(self.log[-6:]), inline=False)
        return e
    async def _attack(self, interaction, special):
        if self.ended: return
        an = self.p1n if self.turn == self.p1id else self.p2n
        a_s = self.p1s if self.turn == self.p1id else self.p2s
        d_def = (self.p2s if self.turn == self.p1id else self.p1s)["effective_defense"]
        if self.phase == "lightning" and special:
            return await interaction.response.send_message("⚡ No specials in Lightning!", ephemeral=True)
        if special and random.random() < 0.4:
            self.log.append(f"💨 **{an}** MISSED!"); self.turn = self.p2id if self.turn == self.p1id else self.p1id; self.tnum += 1
            return await interaction.response.edit_message(embed=self._embed(), view=self)
        dmg = max(1, a_s["effective_attack"] - d_def // 2 + random.randint(-2, 4))
        dmg = int(dmg * self.dmg_mult)
        if special: dmg *= 2
        if random.random() < a_s["crit_chance"]: dmg = int(dmg * 1.5); self.log.append(f"⚔️ **{an}** {'Special' if special else 'ATK'} `{dmg}` **CRIT!**")
        else: self.log.append(f"⚔️ **{an}** {'Special' if special else 'ATK'} `{dmg}`")
        if self.turn == self.p1id: self.p2hp -= dmg
        else: self.p1hp -= dmg
        if self.p1hp <= 0 or self.p2hp <= 0:
            self.ended = True
            if self.p1hp <= 0 and self.p2hp <= 0:
                self.stop()
                if not self.result_future.done(): self.result_future.set_result(("tie", None))
                return await interaction.response.edit_message(embed=discord.Embed(title="⚡ A TIE!", color=0xF39C12), view=None)
            wid = self.p1id if self.p2hp <= 0 else self.p2id
            wn = self.p1n if self.p2hp <= 0 else self.p2n
            self.stop()
            if not self.result_future.done(): self.result_future.set_result(("winner", wid))
            return await interaction.response.edit_message(embed=discord.Embed(title=f"🏆 {wn} Triumphs!",
                description=f"*The clash of steel falls silent. **{wn}** stands victorious!* 🔥",
                color=0xFFD700), view=None)
        max_t = {"normal": 30, "sudden_death": 15, "lightning": 10}[self.phase]
        if self.tnum >= max_t:
            self.ended = True; self.stop()
            if not self.result_future.done(): self.result_future.set_result(("tie", None))
            return await interaction.response.edit_message(embed=discord.Embed(title="⚡ TIE!", color=0xF39C12), view=None)
        self.turn = self.p2id if self.turn == self.p1id else self.p1id; self.tnum += 1
        await interaction.response.edit_message(embed=self._embed(), view=self)
    @discord.ui.button(label="⚔️ Attack", style=discord.ButtonStyle.primary)
    async def atk(self, i, b): await self._attack(i, False)
    @discord.ui.button(label="💥 Special", style=discord.ButtonStyle.danger)
    async def spc(self, i, b): await self._attack(i, True)
    @discord.ui.button(label="🏳️ Forfeit", style=discord.ButtonStyle.secondary)
    async def forfeit(self, i, b):
        if self.ended: return
        if i.user.id != self.turn: return await i.response.send_message("❌", ephemeral=True)
        self.ended = True; wid = self.p2id if i.user.id == self.p1id else self.p1id
        wn = self.p2n if i.user.id == self.p1id else self.p1n
        self.stop()
        if not self.result_future.done(): self.result_future.set_result(("winner", wid))
        await i.response.edit_message(embed=discord.Embed(title=f"🏳️ Forfeit! {wn} wins!", color=0x95A5A6), view=None)
    async def on_timeout(self):
        if not self.ended and not self.result_future.done(): self.result_future.set_result(("timeout", None))


class KingdomCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ═══ /kingdom ═══
    @app_commands.command(name="kingdom", description="👑 View the full kingdom status!")
    async def kingdom(self, interaction: discord.Interaction):
        gid = interaction.guild.id if interaction.guild else None
        if not gid: return
        await ensure_kingdom(gid); k = await get_kingdom(gid); server_name = interaction.guild.name
        e = discord.Embed(title=f"🏰 The Kingdom of {server_name}", color=0xFFD700)
        if k and k.get("king_id"):
            kc = await get_character(k["king_id"], gid)
            if kc:
                ks = await get_effective_stats(k["king_id"], gid)
                total_stats = (ks["effective_attack"] + ks["effective_defense"] + ks["effective_max_hp"]) if ks else 0
                reign_text = ""
                crowned_at = k.get("king_crowned_at")
                if crowned_at:
                    try:
                        dt = datetime.fromisoformat(crowned_at); delta = datetime.utcnow() - dt
                        if delta.days > 0: reign_text = f"\n⏳ Ruling for **{delta.days}d {delta.seconds//3600}h**"
                        else: reign_text = f"\n⏳ Ruling for **{delta.seconds//3600}h {(delta.seconds%3600)//60}m**"
                    except: pass
                e.add_field(name="👑 King", value=f"**{kc['username']}**\n📊 Level **{kc['level']}** {kc['class']}\n⚔️ Stats: `{total_stats}`{reign_text}", inline=True)
            else: e.add_field(name="👑 King", value="*Data unavailable*", inline=True)
        else: e.add_field(name="👑 King", value="⚔️ *The throne is empty.*\nA Royal Tournament will begin\nonce enough Warriors are ready.", inline=True)
        if k and k.get("queen_id"):
            qc = await get_character(k["queen_id"], gid)
            if qc: e.add_field(name="👑 Queen", value=f"**{qc['username']}**\n📊 Level **{qc['level']}** {qc['class']}", inline=True)
            else: e.add_field(name="👑 Queen", value="*Data unavailable*", inline=True)
        else: e.add_field(name="👑 Queen", value="*The throne awaits its Queen* 👸", inline=True)
        e.add_field(name="\u200b", value="\u200b", inline=True)
        guards = await get_kingsguard_list(gid)
        if guards: e.add_field(name=f"🛡️ Kingsguard ({len(guards)})", value="\n".join(f"🛡️ **{g['username']}** — Lvl `{g['level']}`" for g in guards[:8]), inline=False)
        else: e.add_field(name="🛡️ Kingsguard", value="*No Kingsguard appointed yet* ⚔️", inline=False)
        soldiers = await get_royal_soldiers(gid)
        if soldiers: e.add_field(name=f"⚔️ Royal Soldiers ({len(soldiers)})", value=", ".join(f"**{s['username']}**" for s in soldiers[:10]), inline=True)
        else: e.add_field(name="⚔️ Royal Soldiers", value="*No soldiers recruited yet*", inline=True)
        lawyers = await get_all_lawyers(gid)
        if lawyers: e.add_field(name=f"⚖️ Royal Lawyers ({len(lawyers)})", value=", ".join(f"**{l['username']}**" for l in lawyers[:10]), inline=True)
        else: e.add_field(name="⚖️ Royal Lawyers", value="*No lawyers in the kingdom*", inline=True)
        treasury_val = k["treasury"] if k else 0; tax_pct = int(k["tax_rate"] * 100) if k and k.get("tax_rate") else 0
        e.add_field(name="🏦 Treasury", value=f"**{treasury_val:,}** 🪙", inline=True)
        e.add_field(name="📊 Tax Rate", value=f"**{tax_pct}%** on marketplace", inline=True)
        if k and k.get("last_event"):
            try:
                from datetime import timedelta
                event_dt = datetime.fromisoformat(k["last_event"]); event_end = event_dt + timedelta(hours=24)
                if datetime.utcnow() < event_end:
                    rem = event_end - datetime.utcnow()
                    e.add_field(name="🎪 Active Event", value=f"⚔️ **Kingdom Challenge Event**\n⏳ `{rem.seconds//3600}h {(rem.seconds%3600)//60}m` remaining", inline=False)
                else: e.add_field(name="🎪 Festival", value="*No festival active* 🎪", inline=False)
            except: e.add_field(name="🎪 Festival", value="*No festival active* 🎪", inline=False)
        else: e.add_field(name="🎪 Festival", value="*No festival active* 🎪", inline=False)
        t = await get_active_tournament(gid)
        if t:
            bracket = json.loads(t["bracket"]) if t.get("bracket") else []
            remaining = sum(1 for rd in bracket for m in rd.get("matches", []) if m.get("status") in ("pending", "active", "waiting"))
            e.add_field(name="🏆 TOURNAMENT ACTIVE!", value=f"Status: **{t.get('status','?').upper()}** • Round: **{t.get('current_round',0)}**\n⚔️ **{remaining}** match(es) remaining\n*Use `/tournamentstatus` for the full bracket!*", inline=False)
        total_players = await get_total_players(gid); richest = await get_richest_player(gid); most_wanted = await get_most_wanted(gid)
        stats_lines = [f"👥 **{total_players}** citizens in the kingdom"]
        if richest: stats_lines.append(f"💰 Richest: **{richest['username']}** ({richest['coins']:,} 🪙)")
        if most_wanted: stats_lines.append(f"🔴 Most Wanted: **{most_wanted['username']}** ({most_wanted['crime_count']} crimes)")
        e.add_field(name="📋 Kingdom Stats", value="\n".join(stats_lines), inline=False)
        e.set_footer(text=f"Crown Forge — {server_name}")
        await interaction.response.send_message(embed=e)

    # ═══ /challengeking ═══
    @app_commands.command(name="challengeking", description="⚔️ Challenge the King for the Crown!")
    async def challengeking(self, interaction: discord.Interaction):
        gid = interaction.guild.id; uid = interaction.user.id
        if await check_jail(interaction): return
        t = await get_active_tournament(gid)
        if t:
            return await interaction.response.send_message(embed=discord.Embed(title="🏆 Tournament Active",
                description="👀 *A tournament is already deciding the next King. Wait for it to conclude.*", color=0xF39C12), ephemeral=True)
        char = await get_character(uid, gid)
        if not char: return await interaction.response.send_message(embed=discord.Embed(title="❌", description="Use `/start`!", color=0xE74C3C), ephemeral=True)
        if char["class"] != "Warrior":
            return await interaction.response.send_message(embed=discord.Embed(title="❌", description="Only **Warriors** can challenge for the Crown!", color=0xE74C3C), ephemeral=True)
        await ensure_kingdom(gid); k = await get_kingdom(gid)
        if not k or not k.get("king_id"):
            return await interaction.response.send_message(embed=discord.Embed(title="❌", description="There is no King to challenge! A tournament will crown one.", color=0xE74C3C), ephemeral=True)
        if k["king_id"] == uid:
            return await interaction.response.send_message(embed=discord.Embed(title="❌", description="You ARE the King!", color=0xE74C3C), ephemeral=True)
        # 48hr cooldown
        last = await get_cooldown(uid, gid, "challenge_king"); ready, rem = check_cooldown(last, 48*3600)
        if not ready:
            h = rem // 3600; m = (rem % 3600) // 60
            return await interaction.response.send_message(embed=discord.Embed(title="🛡️ Cooldown",
                description=f"The King has defended his throne. You may challenge again in **{h}h {m}m**.\n*Train harder.* ⚔️", color=0xF39C12), ephemeral=True)
        # Stats comparison
        c_stats = await get_effective_stats(uid, gid)
        k_stats = await get_effective_stats(k["king_id"], gid)
        if not c_stats or not k_stats: return
        c_total = c_stats["hp"] + c_stats["effective_attack"] + c_stats["effective_defense"] + c_stats["level"]
        k_total = k_stats["hp"] + k_stats["effective_attack"] + k_stats["effective_defense"] + k_stats["level"]
        if c_total <= k_total:
            return await interaction.response.send_message(embed=discord.Embed(title="❌ Not Strong Enough",
                description=f"Your total stats (`{c_total}`) must exceed the King's (`{k_total}`) to challenge.\n*Level up, gear up, and try again!* ⚔️", color=0xE74C3C), ephemeral=True)

        guild = interaction.guild; king_member = guild.get_member(k["king_id"])
        challenger_name = interaction.user.display_name
        king_name = king_member.display_name if king_member else "the King"

        await interaction.response.send_message(embed=discord.Embed(title="⚔️ War Declaration Sent!",
            description=f"Your challenge has been sent to **{king_name}**.\n"
            f"He has **10 minutes** to accept or decline.\n\n*The kingdom holds its breath...* 👑",
            color=0xFF6B35))

        # Send challenge to King
        accepted_event = asyncio.Event()
        king_accepted = [None]  # Use list for mutability in closure

        async def on_response(did_accept):
            king_accepted[0] = did_accept
            accepted_event.set()

        if king_member:
            try:
                view = ChallengeAcceptView(k["king_id"], on_response)
                await king_member.send(embed=discord.Embed(title="⚔️ WAR HAS BEEN DECLARED!",
                    description=f"⚔️ **{challenger_name}** has declared war on the throne!\n\n"
                    f"Your crown is being challenged. You have **10 minutes** to Accept ⚔️ or Decline 🏳️.\n\n"
                    f"📊 Challenger stats: `{c_total}` vs Your stats: `{k_total}`\n\n"
                    f"*Will you defend your honor?*", color=0xE74C3C), view=view)
            except:
                king_accepted[0] = False; accepted_event.set()
        else:
            king_accepted[0] = False; accepted_event.set()

        try: await asyncio.wait_for(accepted_event.wait(), timeout=600)
        except asyncio.TimeoutError: king_accepted[0] = False

        ch = interaction.channel

        if not king_accepted[0]:
            # KING IS A COWARD
            await add_coins(k["king_id"], gid, -500)
            await ch.send(embed=discord.Embed(title="🐔 The King Refused to Fight!",
                description=f"🐔 **{king_name}** refused to defend his crown!\n\n"
                f"He loses **500 🪙** for cowardice.\n"
                f"*The challenge stands — a Royal Tournament will now be called!* ⚔️",
                color=0xE74C3C))
            await update_kingdom(gid, king_id=None, queen_id=None)
            tc = self.bot.get_cog("TournamentCog")
            if tc:
                await tc.trigger_tournament(gid, ch,
                    f"King {king_name} refused to fight! The crown is up for grabs!")
            return

        # KING ACCEPTED — RUN THE DUEL
        await ch.send(embed=discord.Embed(title="⚔️🔥 THE KING ACCEPTS THE CHALLENGE! 🔥⚔️",
            description=f"**{challenger_name}** vs **{king_name}**\n\n*The duel for the Crown begins NOW!*",
            color=0xFF6B35))

        winner_uid = await self._run_challenge_duel(ch, uid, k["king_id"], c_stats, k_stats,
            challenger_name, king_name)

        if winner_uid == uid:
            # Challenger wins → crowned King
            await update_character(k["king_id"], gid, **{"class": "Warrior"})
            await update_kingdom(gid, king_id=uid, queen_id=None, king_crowned_at=datetime.utcnow().isoformat())
            await add_xp(uid, gid, 200); await add_coins(uid, gid, 500)
            await set_mood(uid, gid, "happy"); await add_player_item(uid, gid, "King Trophy", "trophy")
            await ch.send(embed=discord.Embed(title="👑🔥 ALL HAIL THE NEW KING! 🔥👑",
                description=f"*The dust settles. The blood dries.*\n\n"
                f"**{challenger_name}** stands alone atop the throne of **{guild.name}**!\n\n"
                f"All hail the new King! ⚔️🔥\n\n💰 +500 🪙 • 🏆 King Trophy",
                color=0xFFD700))
        elif winner_uid == k["king_id"]:
            # King wins → challenger gets 48hr cooldown
            await set_cooldown(uid, gid, "challenge_king")
            await set_mood(uid, gid, "sad")
            try:
                await interaction.user.send(embed=discord.Embed(title="🛡️ The King Has Defended His Throne",
                    description="You may challenge again in **48 hours**.\n*Train harder.* ⚔️", color=0x3498DB))
            except: pass
            await ch.send(embed=discord.Embed(title=f"🛡️ {king_name} Defends the Crown!",
                description=f"**{king_name}** has defeated **{challenger_name}** and retains the throne!\n"
                f"*The King's blade is sharp. The challengers will think twice.* 👑", color=0x3498DB))
        else:
            # Timeout/error → tournament
            await update_kingdom(gid, king_id=None, queen_id=None)
            tc = self.bot.get_cog("TournamentCog")
            if tc: await tc.trigger_tournament(gid, ch, "The challenge duel was inconclusive! A tournament will decide!")

    async def _run_challenge_duel(self, channel, p1_uid, p2_uid, p1s, p2s, p1n, p2n):
        """Run challenge duel with tiebreaker. Returns winner_uid or None."""
        for phase in ["normal", "sudden_death", "lightning"]:
            if phase != "normal":
                phase_title = "⚡ SUDDEN DEATH!" if phase == "sudden_death" else "🔥⚡ LIGHTNING ROUND ⚡🔥"
                await channel.send(embed=discord.Embed(title=phase_title,
                    description="Neither warrior fell! The fight continues!", color=0xF39C12))
            loop = asyncio.get_event_loop()
            result_future = loop.create_future()
            view = ChallengeDuelView(p1_uid, p2_uid, p1s, p2s, p1n, p2n, result_future, phase)
            await channel.send(embed=view._embed(), view=view)
            try: result = await asyncio.wait_for(result_future, timeout=900)
            except asyncio.TimeoutError: view.stop(); return None
            if isinstance(result, tuple):
                result_type, winner_uid = result
            else: result_type, winner_uid = "winner", result
            if result_type == "winner" and winner_uid: return winner_uid
            if result_type == "timeout": return None
        return p1_uid  # Seed advantage after all tiebreakers

    # ═══ /leavekingdom ═══
    @app_commands.command(name="leavekingdom", description="🚪 Leave the kingdom. Loses everything!")
    async def leavekingdom(self, interaction: discord.Interaction):
        gid = interaction.guild.id; uid = interaction.user.id
        if await get_active_jail(uid, gid):
            return await interaction.response.send_message(embed=discord.Embed(title="⛓️ The Dungeon Doors Won't Open",
                description="*Serve your time or pay your fine before leaving.* ⛓️", color=0x2C2F33), ephemeral=True)
        char = await get_character(uid, gid)
        if not char: return await interaction.response.send_message(embed=discord.Embed(title="❌", description="No character! `/start`", color=0xE74C3C), ephemeral=True)
        is_k = await is_king(gid, uid); extra = "\n\n👑 **You are the KING!** Leaving triggers a Tournament!" if is_k else ""
        e = discord.Embed(title="🚪 Leave the Kingdom?", color=0xE74C3C,
            description=f"⚠️ **Are you sure?** Leaving means losing **everything** on this server — "
            f"coins, gear, rank, bank, farm, friends, and title.\n\n"
            f"📊 **What you'll lose:**\n• Level: **{char['level']}** (⚠️ *global stats kept across servers*)\n"
            f"• Coins: **{char['coins']}** 🪙\n• Class: **{char['class']}**\n"
            f"• All server-specific data{extra}\n\n*This action is irreversible.*")
        await interaction.response.send_message(embed=e, view=LeaveConfirmView(uid, gid, self.bot), ephemeral=True)

    # ═══ /exiles ═══
    @app_commands.command(name="exiles", description="👑 (King) View all who abandoned the kingdom.")
    async def exiles(self, interaction: discord.Interaction):
        gid = interaction.guild.id
        if not await is_king(gid, interaction.user.id):
            return await interaction.response.send_message(embed=discord.Embed(title="❌", description="Only the King!", color=0xE74C3C), ephemeral=True)
        log = await get_leave_log(gid)
        if not log: return await interaction.response.send_message(embed=discord.Embed(title="📜 Exile Records", description="*No one has ever abandoned this kingdom!*", color=0x95A5A6))
        e = discord.Embed(title="📜 Exile Records", color=0x2C2F33)
        for entry in log[:15]:
            ts = entry["left_at"][:10] if entry.get("left_at") else "?"
            e.add_field(name=f"👋 {entry['username']} the {entry['role_at_leaving']}", value=f"Lvl `{entry['level_at_leaving']}` • `{entry['coins_at_leaving']}`🪙 • {ts}", inline=False)
        e.set_footer(text=f"⚔️ {len(log)} exile(s) total")
        await interaction.response.send_message(embed=e)

    # ═══ Other King Commands ═══
    @app_commands.command(name="choosequeen", description="👑 (King) Propose Queen.")
    @app_commands.describe(target="Player")
    async def choosequeen(self, interaction: discord.Interaction, target: discord.Member):
        gid = interaction.guild.id
        if not await is_king(gid, interaction.user.id): return await interaction.response.send_message(embed=discord.Embed(title="❌", description="Only the King!", color=0xE74C3C), ephemeral=True)
        if not await get_character(target.id, gid): return await interaction.response.send_message(embed=discord.Embed(title="❌", description="No character!", color=0xE74C3C), ephemeral=True)
        await interaction.response.send_message(embed=discord.Embed(title="👑 Royal Proposal!", description=f"The King proposes **{target.display_name}** as Queen!", color=0xFFD700),
            view=QueenProposalView(interaction.user.id, target.id, gid))

    @app_commands.command(name="appoint", description="🛡️ (King) Appoint Kingsguard.")
    @app_commands.describe(target="Player")
    async def appoint(self, interaction: discord.Interaction, target: discord.Member):
        gid = interaction.guild.id
        if not await is_king(gid, interaction.user.id): return await interaction.response.send_message(embed=discord.Embed(title="❌", description="Only the King!", color=0xE74C3C), ephemeral=True)
        if not await get_character(target.id, gid): return await interaction.response.send_message(embed=discord.Embed(title="❌", description="No character!", color=0xE74C3C), ephemeral=True)
        await add_kingsguard(gid, target.id)
        await interaction.response.send_message(embed=discord.Embed(title="🛡️ Kingsguard Appointed!", description=f"**{target.display_name}** joins the Kingsguard!", color=0x3498DB))

    @app_commands.command(name="dismiss", description="🛡️ (King) Dismiss Kingsguard.")
    @app_commands.describe(target="Player")
    async def dismiss(self, interaction: discord.Interaction, target: discord.Member):
        gid = interaction.guild.id
        if not await is_king(gid, interaction.user.id): return await interaction.response.send_message(embed=discord.Embed(title="❌", description="Only the King!", color=0xE74C3C), ephemeral=True)
        await remove_kingsguard(gid, target.id)
        await interaction.response.send_message(embed=discord.Embed(title="🛡️ Dismissed", color=0xE74C3C))

    @app_commands.command(name="recruit", description="⚔️ (King) Recruit Royal Soldier.")
    @app_commands.describe(target="Player")
    async def recruit(self, interaction: discord.Interaction, target: discord.Member):
        gid = interaction.guild.id
        if not await is_king(gid, interaction.user.id): return await interaction.response.send_message(embed=discord.Embed(title="❌", description="Only the King!", color=0xE74C3C), ephemeral=True)
        await add_royal_soldier(gid, target.id)
        await interaction.response.send_message(embed=discord.Embed(title="⚔️ Soldier Recruited!", description=f"**{target.display_name}** is now a Royal Soldier!", color=0x3498DB))

    @app_commands.command(name="taxrate", description="👑 (King) Set tax rate (0-20%).")
    @app_commands.describe(percentage="Tax %")
    async def taxrate(self, interaction: discord.Interaction, percentage: int):
        gid = interaction.guild.id
        if not await is_king(gid, interaction.user.id): return await interaction.response.send_message(embed=discord.Embed(title="❌", description="Only the King!", color=0xE74C3C), ephemeral=True)
        pct = max(0, min(20, percentage))
        await update_kingdom(gid, tax_rate=pct / 100)
        await interaction.response.send_message(embed=discord.Embed(title="📊 Tax Updated", description=f"Tax set to **{pct}%**", color=0xF1C40F))

    @app_commands.command(name="treasury", description="🏦 View treasury.")
    async def treasury(self, interaction: discord.Interaction):
        gid = interaction.guild.id; k = await get_kingdom(gid)
        await interaction.response.send_message(embed=discord.Embed(title="🏦 Treasury", description=f"`{k['treasury'] if k else 0}` 🪙", color=0xF1C40F))

    @app_commands.command(name="treasuryspend", description="👑 (King) Distribute treasury.")
    @app_commands.describe(amount="Coins", target="Recipient", reason="Reason")
    async def treasuryspend(self, interaction: discord.Interaction, amount: int, target: discord.Member, reason: str = "Royal reward"):
        gid = interaction.guild.id
        if not await is_king(gid, interaction.user.id): return await interaction.response.send_message(embed=discord.Embed(title="❌", description="Only the King!", color=0xE74C3C), ephemeral=True)
        k = await get_kingdom(gid)
        if not k or k["treasury"] < amount: return await interaction.response.send_message(embed=discord.Embed(title="❌", description="Not enough!", color=0xE74C3C), ephemeral=True)
        await update_kingdom(gid, treasury=k["treasury"] - amount); await add_coins(target.id, gid, amount)
        await interaction.response.send_message(embed=discord.Embed(title="🏦 Disbursement", description=f"**{amount}**🪙 → **{target.display_name}**\n📝 {reason}", color=0x2ECC71))

    @app_commands.command(name="forcetournament", description="👑 (King) Abdicate and trigger tournament.")
    async def forcetournament(self, interaction: discord.Interaction):
        gid = interaction.guild.id
        if not await is_king(gid, interaction.user.id): return await interaction.response.send_message(embed=discord.Embed(title="❌", description="Only the King!", color=0xE74C3C), ephemeral=True)
        t = await get_active_tournament(gid)
        if t: return await interaction.response.send_message(embed=discord.Embed(title="❌", description="Tournament already active!", color=0xE74C3C), ephemeral=True)
        char = await get_character(interaction.user.id, gid); name = char["username"] if char else interaction.user.display_name
        await update_kingdom(gid, king_id=None, queen_id=None)
        await interaction.response.send_message(embed=discord.Embed(title="👑 The King Abdicates!", description=f"**{name}** has relinquished the throne! A tournament will begin!", color=0xFF6B35))
        tc = self.bot.get_cog("TournamentCog")
        if tc: await tc.trigger_tournament(gid, interaction.channel, f"King {name} has abdicated! The realm needs a new ruler!")

async def setup(bot):
    await bot.add_cog(KingdomCog(bot))
