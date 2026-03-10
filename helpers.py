"""helpers.py — Shared utilities: jail check, guild requirement."""
import discord
from datetime import datetime
from database import get_active_jail

async def check_jail(interaction: discord.Interaction) -> bool:
    """Returns True if jailed (command should abort). Sends embed if so."""
    if not interaction.guild: return False
    jail = await get_active_jail(interaction.user.id, interaction.guild.id)
    if not jail: return False
    jailed_at = datetime.fromisoformat(jail["jailed_at"])
    remaining = (jail["sentence_hours"] * 3600) - (datetime.utcnow() - jailed_at).total_seconds()
    h, rem = divmod(int(remaining), 3600); m = rem // 60
    e = discord.Embed(title="⛓️ Ye Art Imprisoned, Knave!", color=0x2C2F33,
        description=f"Thou hast been cast into the dungeon for thy crimes!\n\n"
                    f"⚖️ **Crime:** {jail['crime']}\n"
                    f"⏳ **Remaining:** {h}h {m}m\n"
                    f"💰 **Fine:** {jail['fine_amount']} coins\n"
                    f"🔓 **Bail:** {jail['bail_amount']} coins\n\n"
                    f"Use `/fine` to pay thy fine or `/bail` for outside aid.")
    e.set_footer(text="⚔️ Only /jailstatus, /fine, /bail permitted")
    await interaction.response.send_message(embed=e, ephemeral=True)
    return True

def require_guild(interaction: discord.Interaction):
    """Returns guild_id or None."""
    return interaction.guild.id if interaction.guild else None
