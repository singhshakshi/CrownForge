"""cogs/quest.py — Solo quest with guild_id + jail check."""
import random, discord
from discord import app_commands
from discord.ext import commands
from database import get_effective_stats, add_xp, add_coins, set_mood
from helpers import check_jail

MONSTERS = [
    {"name":"Goblin","emoji":"👺","base_hp":40,"base_atk":8,"base_def":4,"xp":25,"coins":15},
    {"name":"Skeleton","emoji":"💀","base_hp":50,"base_atk":10,"base_def":5,"xp":30,"coins":20},
    {"name":"Wolf","emoji":"🐺","base_hp":45,"base_atk":12,"base_def":3,"xp":28,"coins":18},
    {"name":"Orc","emoji":"👹","base_hp":70,"base_atk":14,"base_def":8,"xp":45,"coins":30},
    {"name":"Dark Knight","emoji":"🖤","base_hp":90,"base_atk":16,"base_def":12,"xp":60,"coins":40},
    {"name":"Vampire","emoji":"🧛","base_hp":80,"base_atk":18,"base_def":6,"xp":55,"coins":35},
    {"name":"Necromancer","emoji":"🧙","base_hp":65,"base_atk":22,"base_def":5,"xp":65,"coins":45},
    {"name":"Dragon","emoji":"🐉","base_hp":150,"base_atk":25,"base_def":18,"xp":120,"coins":80},
    {"name":"Demon Lord","emoji":"😈","base_hp":200,"base_atk":30,"base_def":20,"xp":150,"coins":100},
    {"name":"Slime","emoji":"🟢","base_hp":25,"base_atk":5,"base_def":2,"xp":15,"coins":10},
    {"name":"Giant Spider","emoji":"🕷️","base_hp":55,"base_atk":13,"base_def":6,"xp":35,"coins":22},
    {"name":"Troll","emoji":"🧌","base_hp":100,"base_atk":15,"base_def":14,"xp":50,"coins":35},
]
def scale_monster(m, lvl):
    s = 1+(lvl-1)*0.25
    return {k: m[k] if k in ("name","emoji") else int(m[k]*s) if k.startswith("base_") else int(m[k]*s)
            for k in m} | {"hp":int(m["base_hp"]*s),"atk":int(m["base_atk"]*s),"defense":int(m["base_def"]*s),
            "xp":int(m["xp"]*s),"coins":int(m["coins"]*s),"name":m["name"],"emoji":m["emoji"]}
def pick_monster(lvl):
    pool = [m for m in MONSTERS if m["base_hp"] <= (70 if lvl<=3 else 120 if lvl<=7 else 999)]
    return scale_monster(random.choice(pool), lvl)
def simulate_combat(ps, m):
    p_hp, m_hp, log, turn = ps["effective_max_hp"], m["hp"], [], 0
    while p_hp > 0 and m_hp > 0 and turn < 30:
        turn += 1
        crit = random.random() < ps["crit_chance"]
        raw = max(1, ps["effective_attack"]-m["defense"]//2+random.randint(-3,5))
        if crit: raw*=2; log.append(f"⚡ T{turn}: CRIT `{raw}`!")
        else: log.append(f"⚔️ T{turn}: Deal `{raw}`")
        m_hp -= raw
        if m_hp <= 0: break
        md = max(1, m["atk"]-ps["effective_defense"]//2+random.randint(-3,5))
        log.append(f"💥 {m['emoji']} hits `{md}`"); p_hp -= md
    return {"won":m_hp<=0,"log":log[-8:],"remaining_hp":max(0,p_hp),"turns":turn}

class QuestCog(commands.Cog):
    def __init__(self, bot): self.bot = bot
    @app_commands.command(name="quest", description="⚔️ Fight a monster!")
    async def quest(self, interaction: discord.Interaction):
        gid = interaction.guild.id if interaction.guild else None
        if not gid: return
        if await check_jail(interaction): return
        stats = await get_effective_stats(interaction.user.id, gid)
        if not stats: return await interaction.response.send_message(embed=discord.Embed(title="❌",description="Use `/start`!",color=0xE74C3C), ephemeral=True)
        if stats["hp"] <= 0: return await interaction.response.send_message(embed=discord.Embed(title="💀",description="Use `/heal`!",color=0xE74C3C), ephemeral=True)
        monster = pick_monster(stats["level"]); result = simulate_combat(stats, monster)
        if result["won"]:
            xp_gain, coin_gain = monster["xp"], monster["coins"]
            lr = await add_xp(interaction.user.id, gid, xp_gain)
            await add_coins(interaction.user.id, gid, coin_gain)
            await set_mood(interaction.user.id, gid, "happy")
            e = discord.Embed(title=f"🏆 Victory vs {monster['emoji']} {monster['name']}!", color=0x2ECC71)
            e.add_field(name="📜", value="\n".join(result["log"]), inline=False)
            e.add_field(name="✨XP",value=f"`+{xp_gain}`",inline=True)
            e.add_field(name="💰",value=f"`+{coin_gain}`",inline=True)
            if lr["leveled_up"]: e.add_field(name="🎉 LEVEL UP!",value=f"**Level {lr['new_level']}**!",inline=False)
        else:
            cl = min(stats["coins"], max(5, monster["coins"]//3))
            await add_coins(interaction.user.id, gid, -cl)
            await set_mood(interaction.user.id, gid, "sad")
            e = discord.Embed(title=f"💀 Defeated by {monster['emoji']} {monster['name']}...", color=0xE74C3C)
            e.add_field(name="📜",value="\n".join(result["log"]),inline=False)
            e.add_field(name="💸",value=f"`-{cl}`",inline=True)
        await interaction.response.send_message(embed=e)

async def setup(bot): await bot.add_cog(QuestCog(bot))
