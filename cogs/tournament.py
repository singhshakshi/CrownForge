"""cogs/tournament.py — Royal Tournament system for crowning the King."""
import asyncio, json, random, math, discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
from database import (get_effective_stats, add_xp, add_coins, set_mood, update_character,
    get_kingdom, ensure_kingdom, update_kingdom, get_top_warriors,
    create_tournament_record, get_active_tournament, update_tournament_record,
    get_tournament_history, add_player_item)

# ═══ TOURNAMENT DUEL VIEW ═══
def hp_bar(c, m, l=10):
    f = max(0, int((c / m) * l)) if m > 0 else 0
    return "❤️" * f + "🖤" * (l - f)

class TournamentDuelView(discord.ui.View):
    """Interactive duel for tournament matches. Calls result_future.set_result(winner_id) on finish."""
    def __init__(self, p1id, p2id, p1s, p2s, p1n, p2n, gid, result_future, phase="normal"):
        super().__init__(timeout=900)  # 15 min
        self.p1id, self.p2id = p1id, p2id
        self.p1s, self.p2s = p1s, p2s
        self.p1n, self.p2n = p1n, p2n
        self.gid, self.result_future = gid, result_future
        self.phase = phase  # "normal", "sudden_death", "lightning"
        # HP setup based on phase
        if phase == "normal":
            self.p1hp = p1s["effective_max_hp"]
            self.p2hp = p2s["effective_max_hp"]
            self.p1mx = p1s["effective_max_hp"]
            self.p2mx = p2s["effective_max_hp"]
        elif phase == "sudden_death":
            self.p1hp = p1s["effective_max_hp"] // 2
            self.p2hp = p2s["effective_max_hp"] // 2
            self.p1mx = p1s["effective_max_hp"]
            self.p2mx = p2s["effective_max_hp"]
        else:  # lightning
            self.p1hp = p1s["effective_max_hp"] // 4
            self.p2hp = p2s["effective_max_hp"] // 4
            self.p1mx = p1s["effective_max_hp"]
            self.p2mx = p2s["effective_max_hp"]
        self.turn = p1id
        self.tnum = 1
        self.log = []
        self.ended = False
        self.dmg_mult = 2.0 if phase == "lightning" else 1.0

    def tn(self):
        return self.p1n if self.turn == self.p1id else self.p2n

    async def interaction_check(self, interaction):
        if interaction.user.id != self.turn:
            await interaction.response.send_message("❌ Not your turn, warrior!", ephemeral=True)
            return False
        return True

    def _embed(self):
        phase_label = {"normal": "⚔️ Tournament Match", "sudden_death": "⚡ Sudden Death!",
                       "lightning": "🔥⚡ LIGHTNING ROUND ⚡🔥"}[self.phase]
        e = discord.Embed(title=f"{phase_label} — Turn {self.tnum}",
                          description=f"**{self.tn()}**'s turn to strike!", color=0xFF6B35)
        e.add_field(name=f"🔴 {self.p1n}", inline=True,
                    value=f"`{max(0,self.p1hp)}`/`{self.p1mx}`\n{hp_bar(self.p1hp, self.p1mx)}")
        e.add_field(name=f"🔵 {self.p2n}", inline=True,
                    value=f"`{max(0,self.p2hp)}`/`{self.p2mx}`\n{hp_bar(self.p2hp, self.p2mx)}")
        if self.log:
            e.add_field(name="📜 Battle Log", value="\n".join(self.log[-6:]), inline=False)
        if self.phase != "normal":
            e.set_footer(text=f"🏆 {self.phase.replace('_',' ').title()} • Both warriors fighting for the crown!")
        return e

    async def _attack(self, interaction, special):
        if self.ended:
            return
        an = self.p1n if self.turn == self.p1id else self.p2n
        a_s = self.p1s if self.turn == self.p1id else self.p2s
        d_def = (self.p2s if self.turn == self.p1id else self.p1s)["effective_defense"]

        # Lightning round: no special attacks
        if self.phase == "lightning" and special:
            await interaction.response.send_message("⚡ No special attacks in Lightning Round!", ephemeral=True)
            return

        # Special: 40% miss
        if special and random.random() < 0.4:
            self.log.append(f"💨 **{an}** MISSED Special!")
            self.turn = self.p2id if self.turn == self.p1id else self.p1id
            self.tnum += 1
            return await interaction.response.edit_message(embed=self._embed(), view=self)

        dmg = max(1, a_s["effective_attack"] - d_def // 2 + random.randint(-2, 4))
        dmg = int(dmg * self.dmg_mult)
        if special:
            dmg *= 2
        crit = random.random() < a_s["crit_chance"]
        if crit:
            dmg = int(dmg * 1.5)

        if self.turn == self.p1id:
            self.p2hp -= dmg
        else:
            self.p1hp -= dmg

        ct = " **CRIT!**" if crit else ""
        at = "Special" if special else "Attack"
        self.log.append(f"⚔️ **{an}** {at} `{dmg}`{ct}")

        # Check for end
        if self.p1hp <= 0 or self.p2hp <= 0:
            self.ended = True
            # Both dead simultaneously? (very rare in turn-based)
            if self.p1hp <= 0 and self.p2hp <= 0:
                self.stop()
                if not self.result_future.done():
                    self.result_future.set_result(("tie", None))
                e = discord.Embed(title="⚡ A TIE!", color=0xF39C12,
                    description="Both warriors fell at the same instant! A tiebreaker is needed!")
                return await interaction.response.edit_message(embed=e, view=None)

            wid = self.p1id if self.p2hp <= 0 else self.p2id
            wn = self.p1n if self.p2hp <= 0 else self.p2n
            ln = self.p2n if self.p2hp <= 0 else self.p1n
            self.stop()
            if not self.result_future.done():
                self.result_future.set_result(("winner", wid))
            e = discord.Embed(title=f"🏆 {wn} Triumphs!", color=0xFFD700,
                description=f"⚔️ *The clash of steel falls silent. **{wn}** stands victorious over **{ln}**!*\n\n"
                            f"*The crowd roars! Glory to the champion!* 🔥")
            e.add_field(name="📜 Final Blows", value="\n".join(self.log[-4:]), inline=False)
            return await interaction.response.edit_message(embed=e, view=None)

        # Check for max turns (30 normal, 15 sudden death, 10 lightning)
        max_turns = {"normal": 30, "sudden_death": 15, "lightning": 10}[self.phase]
        if self.tnum >= max_turns:
            self.ended = True
            self.stop()
            if not self.result_future.done():
                self.result_future.set_result(("tie", None))
            e = discord.Embed(title="⚡ A TIE!", color=0xF39C12,
                description=f"After {max_turns} turns, neither warrior has fallen! Tiebreaker required!")
            return await interaction.response.edit_message(embed=e, view=None)

        self.turn = self.p2id if self.turn == self.p1id else self.p1id
        self.tnum += 1
        await interaction.response.edit_message(embed=self._embed(), view=self)

    @discord.ui.button(label="⚔️ Attack", style=discord.ButtonStyle.primary)
    async def atk(self, interaction, button):
        await self._attack(interaction, False)

    @discord.ui.button(label="💥 Special", style=discord.ButtonStyle.danger)
    async def spc(self, interaction, button):
        await self._attack(interaction, True)

    @discord.ui.button(label="🏳️ Forfeit", style=discord.ButtonStyle.secondary)
    async def forfeit(self, interaction, button):
        if self.ended:
            return
        if interaction.user.id != self.turn:
            return await interaction.response.send_message("❌ Not your turn!", ephemeral=True)
        self.ended = True
        wid = self.p2id if interaction.user.id == self.p1id else self.p1id
        wn = self.p2n if interaction.user.id == self.p1id else self.p1n
        self.stop()
        if not self.result_future.done():
            self.result_future.set_result(("winner", wid))
        e = discord.Embed(title=f"🏳️ {interaction.user.display_name} Forfeits!",
            description=f"**{wn}** advances! *A warrior knows when to yield.*", color=0x95A5A6)
        await interaction.response.edit_message(embed=e, view=None)

    async def on_timeout(self):
        if not self.ended and not self.result_future.done():
            self.result_future.set_result(("timeout", None))

# ═══ ACCEPT/DECLINE VIEW ═══
class AcceptView(discord.ui.View):
    def __init__(self, uid, callback):
        super().__init__(timeout=600)  # 10 min
        self.uid = uid
        self.callback = callback
        self.responded = False

    async def interaction_check(self, interaction):
        return interaction.user.id == self.uid

    @discord.ui.button(label="Accept ⚔️", style=discord.ButtonStyle.success)
    async def accept(self, interaction, button):
        if self.responded:
            return
        self.responded = True
        self.stop()
        await interaction.response.edit_message(
            embed=discord.Embed(title="⚔️ Challenge Accepted!",
                description="*Thy blade is sharp and thy heart is ready. Prepare for the Tournament!*",
                color=0x2ECC71), view=None)
        await self.callback(self.uid, True)

    @discord.ui.button(label="Decline 🏳️", style=discord.ButtonStyle.danger)
    async def decline(self, interaction, button):
        if self.responded:
            return
        self.responded = True
        self.stop()
        await interaction.response.edit_message(
            embed=discord.Embed(title="🏳️ Declined",
                description="*Perhaps wisdom lies in knowing thy limits. Another day, warrior.*",
                color=0x95A5A6), view=None)
        await self.callback(self.uid, False)

    async def on_timeout(self):
        if not self.responded:
            await self.callback(self.uid, False)

# ═══ BRACKET BUILDER ═══
def build_bracket(participants):
    """Build single-elimination bracket. participants = list of {uid, name, stats_total}."""
    n = len(participants)
    if n < 2:
        return None

    # Number of first-round matches needed to get to a power of 2
    next_pow2 = 2 ** math.ceil(math.log2(n))
    num_play_in = n - next_pow2 // 2  # Number of players who play in R1
    num_byes = n - num_play_in * 2 if num_play_in > 0 else n

    # Alternative simpler approach: figure out how many need to play in round 1
    # to reduce the field to a power of 2
    target = 2 ** (math.ceil(math.log2(n)) - 1) if n > 2 else 1
    play_in_count = (n - target) * 2  # Number of players who play in R1

    rounds_data = []

    if play_in_count > 0:
        # Round 1: play-in matches
        r1 = []
        bye_players = participants[:n - play_in_count]  # Top seeds get byes
        playing = participants[n - play_in_count:]  # Bottom seeds play
        match_id = 1
        for i in range(0, len(playing), 2):
            if i + 1 < len(playing):
                r1.append({"id": match_id, "p1_uid": playing[i]["uid"], "p2_uid": playing[i + 1]["uid"],
                           "p1_name": playing[i]["name"], "p2_name": playing[i + 1]["name"],
                           "winner_uid": None, "status": "pending"})
            match_id += 1
        # Add byes
        for bp in bye_players:
            r1.append({"id": match_id, "p1_uid": bp["uid"], "p2_uid": None,
                        "p1_name": bp["name"], "p2_name": "BYE",
                        "winner_uid": bp["uid"], "status": "bye"})
            match_id += 1
        rounds_data.append({"round": 1, "matches": r1})
        adv_count = target
    else:
        adv_count = n
        match_id = 1

    # Remaining rounds
    current_count = adv_count
    round_num = len(rounds_data) + 1
    while current_count > 1:
        matches = []
        for i in range(current_count // 2):
            matches.append({"id": match_id, "p1_uid": None, "p2_uid": None,
                            "p1_name": "TBD", "p2_name": "TBD",
                            "winner_uid": None, "status": "waiting"})
            match_id += 1
        rounds_data.append({"round": round_num, "matches": matches})
        current_count //= 2
        round_num += 1

    return rounds_data


def bracket_embed(bracket_data, participants, guild_name, status="active"):
    """Generate a visual bracket embed."""
    round_names = {1: "🏟️ Play-In", 2: "⚔️ Semi-Finals", 3: "👑 GRAND FINALS"}
    e = discord.Embed(title=f"🏆 Royal Tournament — {guild_name}",
                      color=0xFFD700 if status == "active" else 0x2ECC71)
    for rd in bracket_data:
        rnum = rd["round"]
        rname = round_names.get(rnum, f"Round {rnum}")
        if len(bracket_data) == 1:
            rname = "👑 GRAND FINALS"
        elif rnum == len(bracket_data):
            rname = "👑 GRAND FINALS"
        elif rnum == len(bracket_data) - 1:
            rname = "⚔️ Semi-Finals"

        lines = []
        for m in rd["matches"]:
            if m["status"] == "bye":
                lines.append(f"🔹 **{m['p1_name']}** — *bye*")
            elif m["status"] == "complete":
                w = m["p1_name"] if m["winner_uid"] == m["p1_uid"] else m["p2_name"]
                lines.append(f"✅ ~~{m['p1_name']}~~ vs ~~{m['p2_name']}~~ → **{w}** 🏆")
            elif m["status"] == "pending":
                lines.append(f"⚔️ **{m['p1_name']}** vs **{m['p2_name']}** — *awaiting*")
            elif m["status"] == "active":
                lines.append(f"🔥 **{m['p1_name']}** vs **{m['p2_name']}** — *IN PROGRESS*")
            else:
                lines.append(f"⏳ {m['p1_name']} vs {m['p2_name']}")
        e.add_field(name=rname, value="\n".join(lines) or "—", inline=False)
    return e


class TournamentCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_tasks = {}  # guild_id -> asyncio.Task

    async def trigger_tournament(self, gid, channel, reason="The throne is empty."):
        """Called by other cogs to start a tournament."""
        if gid in self.active_tasks:
            return  # Already running
        existing = await get_active_tournament(gid)
        if existing:
            return  # Already one in DB
        task = asyncio.create_task(self._run_tournament(gid, channel, reason))
        self.active_tasks[gid] = task

    async def _run_tournament(self, gid, channel, reason):
        guild = self.bot.get_guild(gid)
        if not guild:
            return
        try:
            # ═══ PHASE 1: RECRUITMENT ═══
            warriors = await get_top_warriors(gid, 15)
            if not warriors:
                await channel.send(embed=discord.Embed(title="🏆 Tournament Cancelled",
                    description="No Warriors exist in this kingdom! The throne remains empty.\n"
                    "*A Warrior must rise before the Crown can be claimed.*", color=0x95A5A6))
                return
            if len(warriors) == 1:
                # Auto crown
                w = warriors[0]
                await ensure_kingdom(gid)
                await update_kingdom(gid, king_id=w["user_id"], king_crowned_at=datetime.utcnow().isoformat())
                await add_coins(w["user_id"], gid, 1000)
                await add_player_item(w["user_id"], gid, "King Trophy", "trophy")
                await channel.send(embed=discord.Embed(title="👑 The Sole Warrior Claims the Throne!",
                    description=f"With no challengers, **{w['username']}** is crowned King by default!\n"
                    f"*All hail the uncontested ruler!* 🏰\n\n💰 +1000 🪙 • 🏆 King Trophy",
                    color=0xFFD700))
                return

            invite_count = min(5, len(warriors))
            invited = warriors[:invite_count]
            waitlist = warriors[invite_count:]

            # Create tournament record
            parts_json = json.dumps([{"uid": w["user_id"], "name": w["username"],
                "stats": w["level"] * 10 + w["attack"] + w["defense"] + w["max_hp"]}
                for w in warriors[:invite_count]])
            tid = await create_tournament_record(gid, parts_json)

            # Server announcement
            warrior_names = ", ".join(f"**{w['username']}**" for w in invited)
            await channel.send(embed=discord.Embed(title="🏆 THE THRONE IS EMPTY!", color=0xFF6B35,
                description=f"📜 *{reason}*\n\n"
                f"⚔️ **The Royal Tournament begins!** The top {invite_count} Warriors have been summoned:\n"
                f"{warrior_names}\n\n"
                f"*Let blood and glory decide who claims the Crown!* 🔥\n"
                f"⏳ Warriors have **10 minutes** to accept the challenge."))

            # Send invites
            responses = {}
            response_event = asyncio.Event()

            async def on_response(uid, accepted):
                responses[uid] = accepted
                if len(responses) >= invite_count:
                    response_event.set()

            for w in invited:
                member = guild.get_member(w["user_id"])
                if member:
                    try:
                        view = AcceptView(w["user_id"], on_response)
                        await member.send(embed=discord.Embed(title="🏆 TOURNAMENT SUMMONS!",
                            description=f"⚔️ *Hear ye, **{w['username']}**!*\n\n"
                            f"The throne of **{guild.name}** stands empty and the realm calls for a King!\n"
                            f"Thou hast been chosen as one of the **top {invite_count} Warriors** "
                            f"to compete in the Royal Tournament.\n\n"
                            f"*Dost thou accept the challenge?* ⚔️",
                            color=0xFF6B35), view=view)
                    except:
                        responses[w["user_id"]] = False  # Can't DM → decline
                else:
                    responses[w["user_id"]] = False

            # Wait for responses (10 min max)
            try:
                await asyncio.wait_for(response_event.wait(), timeout=600)
            except asyncio.TimeoutError:
                pass

            # Collect accepted warriors
            accepted = [w for w in invited if responses.get(w["user_id"], False)]

            # Fill from waitlist
            while len(accepted) < 2 and waitlist:
                replacement = waitlist.pop(0)
                accepted.append({"user_id": replacement["user_id"], "username": replacement["username"],
                    "level": replacement["level"], "attack": replacement["attack"],
                    "defense": replacement["defense"], "max_hp": replacement["max_hp"]})
                member = guild.get_member(replacement["user_id"])
                if member:
                    try:
                        await member.send(embed=discord.Embed(title="⚔️ Called to Arms!",
                            description=f"A spot has opened in the Royal Tournament! You've been called as a replacement.\n"
                            f"*Prepare for battle, warrior!*", color=0xFF6B35))
                    except:
                        pass

            if len(accepted) < 2:
                await update_tournament_record(tid, status="abandoned", ended_at=datetime.utcnow().isoformat())
                await channel.send(embed=discord.Embed(title="🏆 Tournament Abandoned",
                    description="Not enough warriors accepted the challenge. The throne remains empty.\n"
                    "*A new tournament will be called when warriors are ready.*", color=0x95A5A6))
                return

            # ═══ PHASE 2: BUILD BRACKET ═══
            participants = [{"uid": w["user_id"], "name": w["username"],
                "stats": w.get("level", 1) * 10 + w.get("attack", 0) + w.get("defense", 0) + w.get("max_hp", 0)}
                for w in accepted]
            bracket_data = build_bracket(participants)
            if not bracket_data:
                await update_tournament_record(tid, status="abandoned", ended_at=datetime.utcnow().isoformat())
                return

            await update_tournament_record(tid, status="active", bracket=json.dumps(bracket_data),
                participants=json.dumps(participants))

            # Post bracket
            be = bracket_embed(bracket_data, participants, guild.name)
            be.description = f"*{len(accepted)} warriors enter. Only one shall claim the Crown!* ⚔️"
            await channel.send(embed=be)

            # ═══ PHASE 3: RUN MATCHES ═══
            tournament_start = datetime.utcnow()

            for round_idx, round_data in enumerate(bracket_data):
                # Gather previous round winners if needed
                if round_idx > 0:
                    prev_round = bracket_data[round_idx - 1]
                    prev_winners = [m["winner_uid"] for m in prev_round["matches"] if m["winner_uid"]]
                    # Fill in this round's matches
                    for i, match in enumerate(round_data["matches"]):
                        if i * 2 < len(prev_winners):
                            match["p1_uid"] = prev_winners[i * 2]
                            w_data = next((p for p in participants if p["uid"] == prev_winners[i * 2]), None)
                            match["p1_name"] = w_data["name"] if w_data else "TBD"
                        if i * 2 + 1 < len(prev_winners):
                            match["p2_uid"] = prev_winners[i * 2 + 1]
                            w_data = next((p for p in participants if p["uid"] == prev_winners[i * 2 + 1]), None)
                            match["p2_name"] = w_data["name"] if w_data else "TBD"
                        # If only one player, it's a bye
                        if match["p1_uid"] and not match["p2_uid"]:
                            match["winner_uid"] = match["p1_uid"]
                            match["status"] = "bye"
                        elif not match["p1_uid"] and match["p2_uid"]:
                            match["winner_uid"] = match["p2_uid"]
                            match["status"] = "bye"
                        elif match["p1_uid"] and match["p2_uid"]:
                            match["status"] = "pending"

                # Check 2-hour tournament timeout
                if (datetime.utcnow() - tournament_start).total_seconds() > 7200:
                    await update_tournament_record(tid, status="abandoned",
                        ended_at=datetime.utcnow().isoformat(), bracket=json.dumps(bracket_data))
                    await channel.send(embed=discord.Embed(title="⏰ Tournament Abandoned!",
                        description="The tournament has exceeded 2 hours! The throne remains empty.\n"
                        "*A new tournament will be scheduled.*", color=0xE74C3C))
                    return

                round_label = f"Round {round_data['round']}"
                if round_idx == len(bracket_data) - 1:
                    round_label = "👑 GRAND FINALS"

                await channel.send(embed=discord.Embed(title=f"🏆 {round_label} Begins!",
                    description=f"*The warriors take their positions. Steel meets steel!* ⚔️",
                    color=0xFF6B35))

                for match in round_data["matches"]:
                    if match["status"] in ("bye", "complete"):
                        continue
                    if not match["p1_uid"] or not match["p2_uid"]:
                        continue

                    match["status"] = "active"
                    await update_tournament_record(tid, bracket=json.dumps(bracket_data),
                        current_round=round_data["round"])

                    # Run the match with tiebreaker support
                    winner_uid = await self._run_full_match(
                        channel, match, gid, round_label)

                    if winner_uid:
                        match["winner_uid"] = winner_uid
                        match["status"] = "complete"
                        # Consolation prize for loser
                        loser_uid = match["p1_uid"] if winner_uid == match["p2_uid"] else match["p2_uid"]
                        await add_coins(loser_uid, gid, 200)
                        await add_xp(loser_uid, gid, 50)
                    else:
                        # Both disqualified (timeout) — pick the one with more HP or random
                        match["status"] = "complete"
                        match["winner_uid"] = match["p1_uid"]  # Default to seed advantage

                    await update_tournament_record(tid, bracket=json.dumps(bracket_data))

                # Post round results
                re = bracket_embed(bracket_data, participants, guild.name)
                re.description = f"*{round_label} complete!*"
                await channel.send(embed=re)

            # ═══ PHASE 4: CROWN THE WINNER ═══
            final_match = bracket_data[-1]["matches"][-1]
            winner_uid = final_match.get("winner_uid")
            if not winner_uid:
                await channel.send(embed=discord.Embed(title="❌ No Victor",
                    description="The tournament ended without a clear winner. The throne remains empty.",
                    color=0x95A5A6))
                await update_tournament_record(tid, status="abandoned", ended_at=datetime.utcnow().isoformat())
                return

            winner_data = next((p for p in participants if p["uid"] == winner_uid), None)
            winner_name = winner_data["name"] if winner_data else "Unknown"

            # Crown the King!
            await ensure_kingdom(gid)
            await update_kingdom(gid, king_id=winner_uid, king_crowned_at=datetime.utcnow().isoformat())
            await add_coins(winner_uid, gid, 1000)
            await add_player_item(winner_uid, gid, "King Trophy", "trophy")
            await set_mood(winner_uid, gid, "happy")

            await update_tournament_record(tid, status="completed", winner_id=winner_uid,
                ended_at=datetime.utcnow().isoformat(), bracket=json.dumps(bracket_data))

            # MASSIVE announcement
            await channel.send(embed=discord.Embed(
                title="👑🔥 ALL HAIL THE NEW KING! 🔥👑", color=0xFFD700,
                description=f"📜 *The dust settles. The blood dries.*\n\n"
                f"**{winner_name}** stands alone atop the throne of **{guild.name}**!\n\n"
                f"⚔️ All hail the new King! ⚔️🔥\n\n"
                f"💰 **+1000** 🪙 Royal Reward\n"
                f"🏆 **King Trophy** added to profile\n\n"
                f"*May his reign be long and glorious. Or at least longer than the last one.* 👑"))

        except asyncio.CancelledError:
            pass
        except Exception as ex:
            try:
                await channel.send(embed=discord.Embed(title="❌ Tournament Error",
                    description=f"An error occurred: {str(ex)[:200]}", color=0xE74C3C))
            except:
                pass
        finally:
            self.active_tasks.pop(gid, None)

    async def _run_full_match(self, channel, match, gid, round_label):
        """Run a match with tiebreaker support. Returns winner_uid or None."""
        p1_uid, p2_uid = match["p1_uid"], match["p2_uid"]
        p1n, p2n = match["p1_name"], match["p2_name"]

        for phase in ["normal", "sudden_death", "lightning"]:
            p1s = await get_effective_stats(p1_uid, gid)
            p2s = await get_effective_stats(p2_uid, gid)
            if not p1s or not p2s:
                return p1_uid if p1s else p2_uid

            match_embed = discord.Embed(
                title=f"🏆 {round_label} — {p1n} vs {p2n}",
                color=0xFF6B35,
                description=f"⚔️ *Two warriors face each other. Only one advances!*\n\n"
                f"🔴 **{p1n}** — ATK `{p1s['effective_attack']}` DEF `{p1s['effective_defense']}` HP `{p1s['effective_max_hp']}`\n"
                f"🔵 **{p2n}** — ATK `{p2s['effective_attack']}` DEF `{p2s['effective_defense']}` HP `{p2s['effective_max_hp']}`\n\n"
                f"*{p1n} strikes first!* ⚔️")
            if phase != "normal":
                phase_title = "⚡ SUDDEN DEATH!" if phase == "sudden_death" else "🔥⚡ LIGHTNING ROUND ⚡🔥"
                match_embed.title = f"{phase_title} — {p1n} vs {p2n}"
                if phase == "sudden_death":
                    match_embed.description = (
                        f"⚡ *A tie! Neither warrior fell. Both reset to 50% HP!*\n\n"
                        f"*No healing. No mercy. Fight!* ⚔️")
                else:
                    match_embed.description = (
                        f"🔥⚡ *Another tie! The Lightning Round begins!*\n\n"
                        f"**Double damage. No special attacks. First hit decides everything.**\n"
                        f"*One strike. One crown.* ⚔️")
                    await channel.send(embed=discord.Embed(title="⚡ A TIE!",
                        description=f"Neither warrior fell! {phase_title} begins — one strike decides everything!",
                        color=0xF39C12))

            loop = asyncio.get_event_loop()
            result_future = loop.create_future()
            view = TournamentDuelView(p1_uid, p2_uid, p1s, p2s, p1n, p2n, gid, result_future, phase)
            await channel.send(embed=view._embed(), view=view)

            try:
                result = await asyncio.wait_for(result_future, timeout=900)
            except asyncio.TimeoutError:
                view.stop()
                # Both DQ'd
                await channel.send(embed=discord.Embed(title="⏰ Match Timed Out!",
                    description=f"Both **{p1n}** and **{p2n}** failed to complete in time!",
                    color=0xE74C3C))
                return None

            if isinstance(result, tuple):
                result_type, winner_uid = result
            else:
                result_type, winner_uid = "winner", result

            if result_type == "winner" and winner_uid:
                return winner_uid
            elif result_type == "tie":
                # Move to next phase
                continue
            elif result_type == "timeout":
                return None

        # After all 3 phases still tie (shouldn't happen but safety)
        return match["p1_uid"]  # Seed advantage

    @app_commands.command(name="tournamentstatus", description="🏆 View current tournament bracket!")
    async def tournamentstatus(self, interaction: discord.Interaction):
        gid = interaction.guild.id
        t = await get_active_tournament(gid)
        if not t:
            return await interaction.response.send_message(embed=discord.Embed(
                title="🏆 No Active Tournament",
                description="*The kingdom is at peace. No tournament in progress.*\n"
                "A tournament begins when the throne is empty!", color=0x95A5A6))
        bracket_data = json.loads(t["bracket"]) if t.get("bracket") else []
        participants = json.loads(t["participants"]) if t.get("participants") else []
        if not bracket_data:
            return await interaction.response.send_message(embed=discord.Embed(
                title="🏆 Tournament — Recruiting",
                description="*Warriors are being summoned! The bracket will appear once all have responded.*",
                color=0xFF6B35))
        e = bracket_embed(bracket_data, participants, interaction.guild.name)
        e.description = f"Status: **{t['status'].upper()}** • Round: **{t.get('current_round', 0)}**"
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="tournamenthistory", description="📜 View past tournaments.")
    async def tournamenthistory(self, interaction: discord.Interaction):
        gid = interaction.guild.id
        history = await get_tournament_history(gid)
        if not history:
            return await interaction.response.send_message(embed=discord.Embed(
                title="📜 No Tournament History",
                description="*No tournaments have been completed in this kingdom yet.*", color=0x95A5A6))
        e = discord.Embed(title="📜 Tournament History", color=0xFFD700)
        for t in history[:10]:
            parts = json.loads(t["participants"]) if t.get("participants") else []
            winner_name = "Unknown"
            for p in parts:
                if p["uid"] == t.get("winner_id"):
                    winner_name = p["name"]
                    break
            part_names = ", ".join(p["name"] for p in parts) if parts else "N/A"
            ts = t["ended_at"][:10] if t.get("ended_at") else "?"
            e.add_field(name=f"👑 {winner_name} — {ts}",
                value=f"Participants: {part_names}", inline=False)
        await interaction.response.send_message(embed=e)

async def setup(bot):
    await bot.add_cog(TournamentCog(bot))
