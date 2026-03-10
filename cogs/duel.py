"""cogs/duel.py — PvP duel with guild_id, jail check, rival bonus."""
import random, discord
from discord import app_commands
from discord.ext import commands
from database import get_effective_stats, add_xp, add_coins, set_mood, update_character, is_king, is_kingsguard
from helpers import check_jail

def hp_bar(c,m,l=10):
    f=max(0,int((c/m)*l)) if m>0 else 0; return "❤️"*f+"🖤"*(l-f)

class DuelView(discord.ui.View):
    def __init__(self, p1id,p2id,p1s,p2s,p1n,p2n,gid):
        super().__init__(timeout=120)
        self.p1id,self.p2id,self.p1s,self.p2s,self.p1n,self.p2n=p1id,p2id,p1s,p2s,p1n,p2n
        self.p1hp,self.p1mx=p1s["effective_max_hp"],p1s["effective_max_hp"]
        self.p2hp,self.p2mx=p2s["effective_max_hp"],p2s["effective_max_hp"]
        self.turn,self.tnum,self.log,self.ended,self.gid=p1id,1,[],False,gid
    def tn(self): return self.p1n if self.turn==self.p1id else self.p2n
    async def interaction_check(self, i):
        if i.user.id!=self.turn: await i.response.send_message("❌ Not your turn!",ephemeral=True); return False
        return True
    def _embed(self):
        e=discord.Embed(title=f"⚔️ Duel — Turn {self.tnum}",description=f"**{self.tn()}**'s turn!",color=0xFF6B35)
        e.add_field(name=f"🔴 {self.p1n}",value=f"`{max(0,self.p1hp)}`/`{self.p1mx}`\n{hp_bar(self.p1hp,self.p1mx)}",inline=True)
        e.add_field(name=f"🔵 {self.p2n}",value=f"`{max(0,self.p2hp)}`/`{self.p2mx}`\n{hp_bar(self.p2hp,self.p2mx)}",inline=True)
        if self.log: e.add_field(name="📜",value="\n".join(self.log[-5:]),inline=False)
        return e
    async def _attack(self, i, special):
        if self.ended: return
        an=self.p1n if self.turn==self.p1id else self.p2n
        a_s=self.p1s if self.turn==self.p1id else self.p2s
        d_d=(self.p2s if self.turn==self.p1id else self.p1s)["effective_defense"]
        if special and random.random()<0.4:
            self.log.append(f"💨 **{an}** MISSED Special!"); self.turn=self.p2id if self.turn==self.p1id else self.p1id; self.tnum+=1
            return await i.response.edit_message(embed=self._embed(),view=self)
        dmg=max(1,a_s["effective_attack"]-d_d//2+random.randint(-2,4))
        if special: dmg*=2
        crit=random.random()<a_s["crit_chance"]
        if crit: dmg=int(dmg*1.5)
        if self.turn==self.p1id: self.p2hp-=dmg
        else: self.p1hp-=dmg
        ct=" **CRIT!**" if crit else ""; at="Special" if special else "Attack"
        self.log.append(f"⚔️ **{an}** {at} `{dmg}`{ct}")
        if self.p1hp<=0 or self.p2hp<=0:
            self.ended=True; wid=self.p1id if self.p2hp<=0 else self.p2id
            wn=self.p1n if self.p2hp<=0 else self.p2n; lid=self.p2id if self.p2hp<=0 else self.p1id
            xr,cr=50+self.tnum*5,30+self.tnum*3; cl=max(5,cr//3)
            await add_xp(wid,self.gid,xr); await add_coins(wid,self.gid,cr); await add_coins(lid,self.gid,-cl)
            await set_mood(wid,self.gid,"happy"); await set_mood(lid,self.gid,"sad")
            await update_character(lid,self.gid,hp=0)
            e=discord.Embed(title=f"🏆 {wn} Wins!",color=0xFFD700)
            e.add_field(name="📜",value="\n".join(self.log[-5:]),inline=False)
            e.add_field(name="🎁",value=f"**{wn}:** +{xr}XP +{cr}🪙\nLoser: -{cl}🪙",inline=False)
            self.stop(); return await i.response.edit_message(embed=e,view=None)
        self.turn=self.p2id if self.turn==self.p1id else self.p1id; self.tnum+=1
        await i.response.edit_message(embed=self._embed(),view=self)

    @discord.ui.button(label="⚔️ Attack",style=discord.ButtonStyle.primary)
    async def atk(self,i,b): await self._attack(i,False)
    @discord.ui.button(label="💥 Special",style=discord.ButtonStyle.danger)
    async def spc(self,i,b): await self._attack(i,True)
    @discord.ui.button(label="🏃 Flee",style=discord.ButtonStyle.secondary)
    async def flee(self,i,b):
        if self.ended: return
        self.ended=True; self.stop()
        await i.response.edit_message(embed=discord.Embed(title="🏃 Fled!",color=0x95A5A6),view=None)

class DuelCog(commands.Cog):
    def __init__(self,bot): self.bot=bot
    @app_commands.command(name="duel",description="⚔️ Challenge another player!")
    @app_commands.describe(opponent="Player to duel")
    async def duel(self, interaction: discord.Interaction, opponent: discord.Member):
        gid = interaction.guild.id if interaction.guild else None
        if not gid: return
        if await check_jail(interaction): return
        if opponent.id==interaction.user.id or opponent.bot:
            return await interaction.response.send_message(embed=discord.Embed(title="❌",description="Invalid!",color=0xE74C3C),ephemeral=True)
        p1=await get_effective_stats(interaction.user.id,gid); p2=await get_effective_stats(opponent.id,gid)
        if not p1: return await interaction.response.send_message(embed=discord.Embed(title="❌",description="Use `/start`!",color=0xE74C3C),ephemeral=True)
        if not p2: return await interaction.response.send_message(embed=discord.Embed(title="❌",description="Opponent needs `/start`!",color=0xE74C3C),ephemeral=True)
        if p1["class"]=="Worker": return await interaction.response.send_message(embed=discord.Embed(title="❌",description="Workers cannot duel!",color=0xE74C3C),ephemeral=True)
        if p1["hp"]<=0 or p2["hp"]<=0: return await interaction.response.send_message(embed=discord.Embed(title="💀",description="Someone is knocked out!",color=0xE74C3C),ephemeral=True)
        # Rival bonus
        if p1["class"]=="Rival" and (await is_king(gid,opponent.id) or await is_kingsguard(gid,opponent.id)):
            p1["effective_attack"]=int(p1["effective_attack"]*1.2)
        if p2["class"]=="Rival" and (await is_king(gid,interaction.user.id) or await is_kingsguard(gid,interaction.user.id)):
            p2["effective_attack"]=int(p2["effective_attack"]*1.2)
        v=DuelView(interaction.user.id,opponent.id,p1,p2,interaction.user.display_name,opponent.display_name,gid)
        await interaction.response.send_message(embed=v._embed(),view=v)

async def setup(bot): await bot.add_cog(DuelCog(bot))
