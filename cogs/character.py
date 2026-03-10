"""cogs/character.py — /start (cross-server identity) and /profile with jail check."""
import discord
from discord import app_commands
from discord.ext import commands
from database import (create_character, get_character, character_exists, get_effective_stats,
    get_equipped_items, get_equipped_pet, xp_for_level, get_hunt_trophies,
    get_kingdom, is_kingsguard, is_royal_soldier, get_lawyer,
    global_exists, get_global_profile, get_strongest_warrior, ensure_kingdom,
    update_kingdom, get_total_players, add_coins, add_player_item)
from helpers import check_jail
from datetime import datetime

ROLE_DATA = {
    "Warrior":{"emoji":"⚔️","hp":150,"attack":18,"defense":14,"crit_chance":0.05,
        "pronouns":("he","him","his"),"color":0xE74C3C,"desc":"Mighty fighter. He can become King."},
    "Mage":{"emoji":"🔮","hp":80,"attack":28,"defense":6,"crit_chance":0.10,
        "pronouns":("she","her","her"),"color":0x9B59B6,"desc":"Powerful spellcaster. She curses enemies."},
    "Thief":{"emoji":"🗡️","hp":110,"attack":16,"defense":12,"crit_chance":0.20,
        "pronouns":("he","him","his"),"color":0x2ECC71,"desc":"Cunning rogue. He steals coins."},
    "Worker":{"emoji":"⛏️","hp":120,"attack":10,"defense":16,"crit_chance":0.05,
        "pronouns":("they","them","their"),"color":0xF39C12,"desc":"Hardworking crafter. They earn steady coins."},
    "Rival":{"emoji":"😈","hp":120,"attack":20,"defense":10,"crit_chance":0.15,
        "pronouns":("he","him","his"),"color":0xE91E63,"desc":"King's sworn enemy. He gets bonus vs royalty."},
    "Commoner":{"emoji":"👤","hp":100,"attack":12,"defense":12,"crit_chance":0.10,
        "pronouns":("they","them","their"),"color":0x95A5A6,"desc":"Common citizen. They can switch roles at lvl 5."},
    "Rogue":{"emoji":"🗡️","hp":110,"attack":18,"defense":12,"crit_chance":0.25,
        "pronouns":("he","him","his"),"color":0x2ECC71,"desc":"Legacy swift striker."},
}
def get_pronouns(cls):
    d = ROLE_DATA.get(cls, ROLE_DATA["Commoner"])
    return {"subject":d["pronouns"][0],"object":d["pronouns"][1],"possessive":d["pronouns"][2]}
MOOD_EMOJIS = {"happy":"😊","sad":"😢","neutral":"😐"}

class RoleSelect(discord.ui.Select):
    """Role selector for /start. If returning=True, stats are NOT overwritten."""
    def __init__(self, uid, gid, uname, returning=False):
        self.uid, self.gid, self.uname, self.returning = uid, gid, uname, returning
        options = [discord.SelectOption(label=n,emoji=d["emoji"],description=d["desc"][:50],value=n)
                   for n,d in ROLE_DATA.items() if n != "Rogue"]
        super().__init__(placeholder="Choose your role…", options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.uid: return await interaction.response.send_message("❌", ephemeral=True)
        cls = self.values[0]; d = ROLE_DATA[cls]; p = get_pronouns(cls)

        if self.returning:
            # Returning player: just create server profile, global stats preserved
            await create_character(self.uid, self.gid, self.uname, cls, d["hp"], d["attack"], d["defense"], d["crit_chance"])
            gp = await get_global_profile(self.uid)
            e = discord.Embed(title=f"⚔️ Welcome Back, {self.uname}!", color=0xFFD700,
                description=f"*Your legend precedes you.* Your power carries over from your other kingdoms.\n\n"
                f"📊 **Global Stats:** Level `{gp['level']}` • HP `{gp['max_hp']}` • ATK `{gp['attack']}` • DEF `{gp['defense']}`\n\n"
                f"🏰 **Server Role:** {d['emoji']} **{cls}**\n"
                f"💰 Starting coins: **100** 🪙\n\n"
                f"*Here you start fresh. Choose your role and begin your new chapter.* 👑")
        else:
            # New player: create both global + server profiles
            await create_character(self.uid, self.gid, self.uname, cls, d["hp"], d["attack"], d["defense"], d["crit_chance"])
            e = discord.Embed(title=f"{d['emoji']} {cls} Created!", color=d["color"],
                description=f"Welcome, **{self.uname}**! {p['subject'].title()} chose the **{cls}** path.")
            e.add_field(name="❤️HP",value=f"`{d['hp']}`",inline=True)
            e.add_field(name="⚔️ATK",value=f"`{d['attack']}`",inline=True)
            e.add_field(name="🛡️DEF",value=f"`{d['defense']}`",inline=True)

        self.view.stop()
        await interaction.response.edit_message(embed=e, view=None)

        # ═══ POST-CREATION CHECKS ═══
        gid = self.gid
        guild = interaction.guild
        if not guild: return

        # Auto-crown: If 1-2 players and this player is a Warrior
        if cls == "Warrior":
            await ensure_kingdom(gid)
            k = await get_kingdom(gid)
            total = await get_total_players(gid)
            if total <= 2 and (not k or not k.get("king_id")):
                from database import update_kingdom as _uk
                await _uk(gid, king_id=self.uid, king_crowned_at=datetime.utcnow().isoformat())
                await add_coins(self.uid, gid, 1000)
                await add_player_item(self.uid, gid, "King Trophy", "trophy")
                ch = guild.system_channel or (guild.text_channels[0] if guild.text_channels else None)
                if ch:
                    try:
                        await ch.send(embed=discord.Embed(title="👑 A King Claims the Throne!",
                            description=f"👑 With no challengers to stand against him, **{self.uname}** "
                            f"claims the throne unopposed. A king by default — but a king nonetheless. ⚔️\n\n"
                            f"💰 +1000 🪙 • 🏆 King Trophy", color=0xFFD700))
                    except: pass
            elif k and k.get("king_id") and k["king_id"] != self.uid:
                # Check if this new Warrior is stronger than the King
                new_stats = await get_effective_stats(self.uid, gid)
                king_stats = await get_effective_stats(k["king_id"], gid)
                if new_stats and king_stats:
                    n_total = new_stats["hp"] + new_stats["effective_attack"] + new_stats["effective_defense"] + new_stats["level"]
                    k_total = king_stats["hp"] + king_stats["effective_attack"] + king_stats["effective_defense"] + king_stats["level"]
                    if n_total > k_total:
                        try:
                            king_member = guild.get_member(k["king_id"])
                            king_name = king_member.display_name if king_member else "the King"
                            await interaction.user.send(embed=discord.Embed(title="⚔️ Your Power Rivals the Crown!",
                                description=f"*Your power rivals the current King.*\n\n"
                                f"You are strong enough to challenge for the throne. "
                                f"Use `/challengeking` to declare war on **{king_name}**!\n\n"
                                f"📊 Your stats: `{n_total}` vs King's: `{k_total}`\n"
                                f"*Will you seize the crown?* ⚔️", color=0xFF6B35))
                        except: pass

class RoleSelectView(discord.ui.View):
    def __init__(self, uid, gid, uname, returning=False):
        super().__init__(timeout=60)
        self.add_item(RoleSelect(uid, gid, uname, returning=returning))

class CharacterCog(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @app_commands.command(name="start", description="🎮 Create your RPG character!")
    async def start(self, interaction: discord.Interaction):
        gid = interaction.guild.id if interaction.guild else None
        if not gid: return await interaction.response.send_message("❌ Use in a server!", ephemeral=True)
        if await character_exists(interaction.user.id, gid):
            return await interaction.response.send_message(embed=discord.Embed(title="⚠️",description="Already have a character! `/profile`",color=0xF39C12), ephemeral=True)

        # Check if returning player (has global profile from another server)
        returning = await global_exists(interaction.user.id)

        if returning:
            gp = await get_global_profile(interaction.user.id)
            e = discord.Embed(title="⚔️ Your Legend Precedes You!", color=0xFFD700,
                description=f"*Welcome back, **{interaction.user.display_name}**!*\n\n"
                f"Your power carries over from your other kingdoms — but here you start fresh.\n\n"
                f"📊 **Your Global Stats:**\n"
                f"• Level: **{gp['level']}** • HP: **{gp['max_hp']}**\n"
                f"• ATK: **{gp['attack']}** • DEF: **{gp['defense']}**\n\n"
                f"Choose your role for this kingdom and begin your new chapter! 👑")
        else:
            e = discord.Embed(title="⚔️ Choose Your Role", color=0x3498DB)
            for n,d in ROLE_DATA.items():
                if n == "Rogue": continue
                e.add_field(name=f"{d['emoji']} {n}", value=f"{d['desc']}\n❤️`{d['hp']}` ⚔️`{d['attack']}` 🛡️`{d['defense']}`", inline=False)

        await interaction.response.send_message(embed=e,
            view=RoleSelectView(interaction.user.id, gid, interaction.user.display_name, returning=returning))

    @app_commands.command(name="profile", description="📊 View your profile.")
    async def profile(self, interaction: discord.Interaction):
        gid = interaction.guild.id if interaction.guild else None
        if not gid: return
        if await check_jail(interaction): return
        stats = await get_effective_stats(interaction.user.id, gid)
        if not stats: return await interaction.response.send_message(embed=discord.Embed(title="❌",description="Use `/start`!",color=0xE74C3C), ephemeral=True)
        cls = stats["class"]; rd = ROLE_DATA.get(cls, ROLE_DATA["Commoner"]); pn = get_pronouns(cls)
        tags = [f"{rd['emoji']} {stats['username']} — Lvl {stats['level']} {cls}"]
        k = await get_kingdom(gid)
        if k and k.get("king_id") == interaction.user.id: tags.append("👑 King")
        elif k and k.get("queen_id") == interaction.user.id: tags.append("👑 Queen")
        if await is_kingsguard(gid, interaction.user.id): tags.append("🛡️ Guard")
        if await is_royal_soldier(gid, interaction.user.id): tags.append("⚔️ Soldier")
        if await get_lawyer(interaction.user.id, gid): tags.append("⚖️ Lawyer")
        mood = stats.get("mood","neutral"); me = MOOD_EMOJIS.get(mood,"😐")
        xn = xp_for_level(stats["level"]); xp = stats["xp"]/xn if xn else 1
        hp = stats["hp"]/stats["effective_max_hp"] if stats["effective_max_hp"] else 1
        e = discord.Embed(title=" • ".join(tags), color=rd["color"])
        e.set_thumbnail(url=interaction.user.display_avatar.url)
        e.add_field(name="📊 Stats", inline=False,
            value=f"❤️ `{stats['hp']}`/`{stats['effective_max_hp']}` {'❤️'*int(hp*10)}{'🖤'*(10-int(hp*10))}\n⚔️ `{stats['effective_attack']}` 🛡️ `{stats['effective_defense']}` 🎯 `{int(stats['crit_chance']*100)}%`\n{me} {mood.title()}")
        e.add_field(name="📈 Progress", value=f"Lvl `{stats['level']}` • XP `{stats['xp']}`/`{xn}`\n{'▓'*int(xp*10)}{'░'*(10-int(xp*10))}", inline=True)
        e.add_field(name="💰", value=f"`{stats['coins']}` 🪙", inline=True)
        eq = await get_equipped_items(interaction.user.id, gid)
        if eq: e.add_field(name="🎒 Gear", value="\n".join(f"🔹 **{i['item_name']}**" for i in eq), inline=False)
        pet = await get_equipped_pet(interaction.user.id, gid)
        if pet: e.add_field(name="🐾 Pet", value=pet["pet_name"], inline=True)
        tr = await get_hunt_trophies(interaction.user.id, gid)
        if tr: e.add_field(name="🏆 Trophies", value=", ".join(f"{t['animal_name']}x{t['count']}" for t in tr[:5]), inline=False)
        e.add_field(name="🌐 Global", value="*Stats shared across all servers*", inline=False)
        e.set_footer(text=f"⚔️ Crown Forge • {pn['subject']}/{pn['object']}")
        await interaction.response.send_message(embed=e)

async def setup(bot): await bot.add_cog(CharacterCog(bot))
