"""cogs/lawyers.py — Lawyer system: bar exam, defend, court records."""
import random, discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
from database import (get_character, get_lawyer, create_lawyer, revoke_lawyer, get_all_lawyers,
    update_lawyer_record, add_bar_exam_attempt, get_last_bar_exam, add_court_record,
    get_court_records, get_active_jail, release_prisoner, add_coins,
    get_kingdom, update_kingdom, is_king)

BAR_QUESTIONS = [
    {"q":"What is the dungeon sentence for a Thief caught stealing?","a":"B",
     "opts":{"A":"1 hour","B":"2 hours","C":"4 hours","D":"6 hours"}},
    {"q":"What fine doth a Rival pay for excessive plotting?","a":"C",
     "opts":{"A":"200 coins","B":"300 coins","C":"500 coins","D":"800 coins"}},
    {"q":"Who alone may grant a Royal Pardon?","a":"D",
     "opts":{"A":"Anyone","B":"The Queen","C":"A Lawyer","D":"The King"}},
    {"q":"What is the bail multiplier over the base fine?","a":"B",
     "opts":{"A":"1×","B":"1.5×","C":"2×","D":"3×"}},
    {"q":"May a Lawyer defend themselves in court?","a":"B",
     "opts":{"A":"Aye","B":"Nay","C":"Only with King's leave","D":"Only once"}},
    {"q":"What befalls a jailed Royal Soldier?","a":"C",
     "opts":{"A":"Nothing","B":"Double sentence","C":"Loses rank","D":"Exile"}},
    {"q":"The fine for dueling the King outside events?","a":"C",
     "opts":{"A":"300 coins","B":"500 coins","C":"800 coins","D":"1000 coins"}},
    {"q":"How many /plot uses cause King dethroning?","a":"B",
     "opts":{"A":"2","B":"3","C":"4","D":"5"}},
    {"q":"Who may view any citizen's crime log?","a":"C",
     "opts":{"A":"Everyone","B":"Only King","C":"King & Soldiers","D":"Lawyers only"}},
    {"q":"Maximum tax rate the King can set?","a":"C",
     "opts":{"A":"10%","B":"15%","C":"20%","D":"25%"}},
    {"q":"Where do fine coins go?","a":"B",
     "opts":{"A":"Destroyed","B":"Kingdom Treasury","C":"King's wallet","D":"Bank"}},
    {"q":"Patrol cooldown for Royal Soldiers?","a":"B",
     "opts":{"A":"1 hour","B":"2 hours","C":"4 hours","D":"6 hours"}},
    {"q":"Can jailed players use /quest?","a":"B",
     "opts":{"A":"Aye","B":"Nay","C":"With fine","D":"After 1hr"}},
    {"q":"Who appoints Royal Soldiers?","a":"C",
     "opts":{"A":"The Queen","B":"Lawyers","C":"The King","D":"Popular vote"}},
    {"q":"Reward for a Lawyer's successful acquittal?","a":"C",
     "opts":{"A":"100 coins","B":"200 coins","C":"400 coins","D":"500 coins"}},
]

class ExamView(discord.ui.View):
    def __init__(self, uid, gid, questions):
        super().__init__(timeout=300)
        self.uid, self.gid = uid, gid
        self.questions = questions  # list of 10
        self.current = 0; self.score = 0; self.answered = False

    def _embed(self):
        q = self.questions[self.current]
        e = discord.Embed(title=f"⚖️ Bar Exam — Question {self.current+1}/10", color=0x9B59B6,
            description=f"📜 *{q['q']}*\n\n" + "\n".join(f"**{k}.** {v}" for k, v in q["opts"].items()))
        e.set_footer(text=f"Score: {self.score}/{self.current} • Need 7/10 to pass")
        return e

    async def _answer(self, interaction, choice):
        if interaction.user.id != self.uid:
            return await interaction.response.send_message("❌ Not your exam!", ephemeral=True)
        if self.answered: return
        self.answered = True
        q = self.questions[self.current]
        correct = choice == q["a"]
        if correct: self.score += 1
        self.current += 1
        if self.current >= 10:
            passed = self.score >= 7
            if passed:
                await create_lawyer(self.uid, self.gid)
                await add_bar_exam_attempt(self.uid, self.gid, self.score, True)
                e = discord.Embed(title="⚖️ BAR EXAM PASSED!", color=0x2ECC71,
                    description=f"📜 *Hear ye! **{interaction.user.display_name}** hath proven mastery of Kingdom Law!*\n\n"
                                f"🏆 Score: **{self.score}/10**\n"
                                f"⚖️ Thou art now a **Licensed Lawyer** of the realm!\n\n"
                                f"*Use `/defend @prisoner` to take cases. Justice awaits!*")
                self.stop()
                return await interaction.response.edit_message(embed=e, view=None)
            else:
                await add_bar_exam_attempt(self.uid, self.gid, self.score, False)
                e = discord.Embed(title="❌ Bar Exam FAILED", color=0xE74C3C,
                    description=f"📜 *Alas! Thou hast not demonstrated sufficient knowledge.*\n\n"
                                f"Score: **{self.score}/10** (needed 7)\n"
                                f"*Thou may retake the exam after **24 hours**.*")
                self.stop()
                return await interaction.response.edit_message(embed=e, view=None)
        self.answered = False
        await interaction.response.edit_message(embed=self._embed(), view=self)

    @discord.ui.button(label="A", style=discord.ButtonStyle.primary, row=0)
    async def a(self, i, b): await self._answer(i, "A")
    @discord.ui.button(label="B", style=discord.ButtonStyle.primary, row=0)
    async def b(self, i, b): await self._answer(i, "B")
    @discord.ui.button(label="C", style=discord.ButtonStyle.primary, row=0)
    async def c(self, i, b): await self._answer(i, "C")
    @discord.ui.button(label="D", style=discord.ButtonStyle.primary, row=0)
    async def d(self, i, b): await self._answer(i, "D")

class DefenseModal(discord.ui.Modal, title="⚖️ Defense Argument"):
    defense = discord.ui.TextInput(label="Thy Defense", style=discord.TextStyle.paragraph,
        placeholder="Present thy argument for the prisoner's innocence...", max_length=1000)
    def __init__(self, lawyer_id, prisoner_id, gid, crime, prisoner_name):
        super().__init__()
        self.lawyer_id, self.prisoner_id, self.gid = lawyer_id, prisoner_id, gid
        self.crime, self.prisoner_name = crime, prisoner_name
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=discord.Embed(
            title="⚖️ Defense Submitted!", color=0x3498DB,
            description=f"Thy defense of **{self.prisoner_name}** has been sent to the King!\n"
                        f"*Await His Majesty's judgement...* 👑"), ephemeral=True)
        # Send to King
        k = await get_kingdom(self.gid)
        if not k or not k["king_id"]: return
        king = interaction.guild.get_member(k["king_id"])
        if not king: return
        e = discord.Embed(title="⚖️ Case Before the Crown", color=0xFFD700,
            description=f"📜 *A Lawyer presents a defense!*\n\n"
                        f"⛓️ **Prisoner:** {self.prisoner_name}\n"
                        f"⚖️ **Crime:** {self.crime}\n"
                        f"📝 **Defense:**\n*{self.defense.value}*\n\n"
                        f"*What is thy judgement, Your Majesty?*")
        try:
            await king.send(embed=e, view=JudgementView(self.lawyer_id, self.prisoner_id, self.gid,
                self.crime, self.defense.value, self.prisoner_name, interaction.user.display_name))
        except:
            ch = interaction.channel
            if ch: await ch.send(f"⚠️ Could not DM King. {king.mention}, check `/jail`!")

class JudgementView(discord.ui.View):
    def __init__(self, lawyer_id, prisoner_id, gid, crime, defense, prisoner_name, lawyer_name):
        super().__init__(timeout=3600)
        self.lid, self.pid, self.gid = lawyer_id, prisoner_id, gid
        self.crime, self.defense, self.pname, self.lname = crime, defense, prisoner_name, lawyer_name

    @discord.ui.button(label="Reduce ⬇️", style=discord.ButtonStyle.primary)
    async def reduce(self, interaction: discord.Interaction, button):
        # Cut sentence in half
        from database import get_active_jail
        import aiosqlite; from database import DB_PATH
        jail = await get_active_jail(self.pid, self.gid)
        if jail:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("UPDATE jail SET sentence_hours=sentence_hours/2 WHERE id=?", (jail["id"],))
                await db.commit()
        await update_lawyer_record(self.lid, self.gid, won=True)
        await add_court_record(self.gid, self.pid, self.lid, self.crime, self.defense, "reduced")
        # Pay lawyer 150 from treasury
        k = await get_kingdom(self.gid)
        if k and k["treasury"] >= 150:
            await update_kingdom(self.gid, treasury=k["treasury"] - 150)
            await add_coins(self.lid, self.gid, 150)
        self.stop()
        await interaction.response.edit_message(embed=discord.Embed(title="⬇️ Sentence Reduced!",
            description=f"The King shows mercy! **{self.pname}**'s sentence halved.\n"
                        f"Lawyer **{self.lname}** earns 150🪙.", color=0x3498DB), view=None)

    @discord.ui.button(label="Acquit 🆓", style=discord.ButtonStyle.success)
    async def acquit(self, interaction: discord.Interaction, button):
        await release_prisoner(self.pid, self.gid)
        await update_lawyer_record(self.lid, self.gid, won=True)
        await add_court_record(self.gid, self.pid, self.lid, self.crime, self.defense, "acquitted")
        k = await get_kingdom(self.gid)
        if k and k["treasury"] >= 400:
            await update_kingdom(self.gid, treasury=k["treasury"] - 400)
            await add_coins(self.lid, self.gid, 400)
        self.stop()
        await interaction.response.edit_message(embed=discord.Embed(title="🆓 ACQUITTED!",
            description=f"👑 *By Royal Decree!*\n**{self.pname}** is FREE! All charges dropped!\n"
                        f"Lawyer **{self.lname}** earns 400🪙.", color=0x2ECC71), view=None)

    @discord.ui.button(label="Dismiss ❌", style=discord.ButtonStyle.danger)
    async def dismiss(self, interaction: discord.Interaction, button):
        await update_lawyer_record(self.lid, self.gid, won=False)
        await add_court_record(self.gid, self.pid, self.lid, self.crime, self.defense, "dismissed")
        self.stop()
        await interaction.response.edit_message(embed=discord.Embed(title="❌ Case Dismissed!",
            description=f"The King is unmoved! **{self.pname}** remains imprisoned.\n"
                        f"Lawyer **{self.lname}**'s defense rejected.", color=0xE74C3C), view=None)

class LawyersCog(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @app_commands.command(name="barexam", description="⚖️ Take the Bar Exam to become a Lawyer!")
    async def barexam(self, interaction: discord.Interaction):
        gid = interaction.guild.id; uid = interaction.user.id
        char = await get_character(uid, gid)
        if not char: return await interaction.response.send_message(embed=discord.Embed(title="❌", description="Use `/start`!", color=0xE74C3C), ephemeral=True)
        if await get_lawyer(uid, gid):
            return await interaction.response.send_message(embed=discord.Embed(title="⚖️", description="Already a Licensed Lawyer!", color=0xF39C12), ephemeral=True)
        # Check 24hr cooldown
        last = await get_last_bar_exam(uid, gid)
        if last and (datetime.utcnow() - last).total_seconds() < 86400:
            rem = 86400 - (datetime.utcnow() - last).total_seconds()
            h = int(rem // 3600)
            return await interaction.response.send_message(embed=discord.Embed(title="⏳",
                description=f"Retake in **{h}h**. Study harder!", color=0xF39C12), ephemeral=True)
        # Check if jailed
        if await get_active_jail(uid, gid):
            return await interaction.response.send_message(embed=discord.Embed(title="⛓️",
                description="Cannot take bar exam while imprisoned!", color=0xE74C3C), ephemeral=True)
        # Pick 10 random questions
        qs = random.sample(BAR_QUESTIONS, 10)
        view = ExamView(uid, gid, qs)
        e = discord.Embed(title="⚖️ Bar Exam — Kingdom Law", color=0x9B59B6,
            description="📜 *Prove thy knowledge of Kingdom Law!*\n\n"
                        "• 10 questions about crimes, sentences, and kingdom rules\n"
                        "• Score **7/10** or higher to pass\n"
                        "• Failure: 24-hour wait before retake\n\n"
                        "*The first question awaits...*")
        await interaction.response.send_message(embed=e, ephemeral=True)
        await interaction.edit_original_response(embed=view._embed(), view=view)

    @app_commands.command(name="defend", description="⚖️ (Lawyer) Defend a prisoner!")
    @app_commands.describe(prisoner="The accused")
    async def defend(self, interaction: discord.Interaction, prisoner: discord.Member):
        gid = interaction.guild.id; uid = interaction.user.id
        lawyer = await get_lawyer(uid, gid)
        if not lawyer:
            return await interaction.response.send_message(embed=discord.Embed(title="❌",
                description="Not a Lawyer! Pass `/barexam` first.", color=0xE74C3C), ephemeral=True)
        if prisoner.id == uid:
            return await interaction.response.send_message(embed=discord.Embed(title="❌",
                description="A Lawyer cannot defend themselves! *'Tis a conflict of interest!*", color=0xE74C3C), ephemeral=True)
        jail = await get_active_jail(prisoner.id, gid)
        if not jail:
            return await interaction.response.send_message(embed=discord.Embed(title="❌",
                description="That soul is not imprisoned!", color=0xE74C3C), ephemeral=True)
        # Check if lawyer is jailed → revoke
        if await get_active_jail(uid, gid):
            await revoke_lawyer(uid, gid)
            return await interaction.response.send_message(embed=discord.Embed(title="⛓️ License Revoked!",
                description="A jailed Lawyer loses their license permanently! Retake `/barexam`.", color=0xE74C3C))
        await interaction.response.send_modal(
            DefenseModal(uid, prisoner.id, gid, jail["crime"], prisoner.display_name))

    @app_commands.command(name="lawyers", description="⚖️ View all Lawyers in the realm.")
    async def lawyers(self, interaction: discord.Interaction):
        gid = interaction.guild.id
        lawyers = await get_all_lawyers(gid)
        if not lawyers:
            return await interaction.response.send_message(embed=discord.Embed(title="⚖️ No Lawyers",
                description="*The realm lacks legal counsel!* Take `/barexam` to become one.", color=0x95A5A6))
        e = discord.Embed(title="⚖️ Kingdom Lawyers", color=0x9B59B6,
            description="*Licensed practitioners of Kingdom Law*\n")
        for l in lawyers:
            total = l["cases_won"] + l["cases_lost"]
            wr = f"{int(l['cases_won']/total*100)}%" if total > 0 else "N/A"
            e.add_field(name=f"⚖️ {l['username']}",
                value=f"Won: `{l['cases_won']}` • Lost: `{l['cases_lost']}` • WR: `{wr}`", inline=False)
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="courtrecord", description="📜 View past court cases.")
    async def courtrecord(self, interaction: discord.Interaction):
        gid = interaction.guild.id
        records = await get_court_records(gid)
        if not records:
            return await interaction.response.send_message(embed=discord.Embed(title="📜 No Records",
                description="*The court archives are empty!*", color=0x95A5A6))
        e = discord.Embed(title="📜 Court Records", color=0x9B59B6)
        for r in records[:10]:
            ts = r["timestamp"][:16] if r["timestamp"] else "?"
            outcome_emoji = {"reduced":"⬇️","acquitted":"🆓","dismissed":"❌"}.get(r["outcome"],"❓")
            e.add_field(name=f"{outcome_emoji} Case #{r['id']}",
                value=f"⚖️ {r['crime']}\n🏛️ Outcome: **{r['outcome'].title()}**\n📅 {ts}", inline=False)
        await interaction.response.send_message(embed=e)

async def setup(bot): await bot.add_cog(LawyersCog(bot))
