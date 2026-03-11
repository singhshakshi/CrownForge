"""cogs/events.py — Kingdom events, checks empty thrones, auto-triggers tournaments."""
import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
from database import (get_kingdom, ensure_kingdom, update_kingdom, get_active_tournament,
    get_total_players, get_top_warriors, add_coins, add_player_item)

class EventsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_events.start()

    def cog_unload(self):
        self.check_events.cancel()

    @tasks.loop(hours=1)
    async def check_events(self):
        for g in self.bot.guilds:
            await ensure_kingdom(g.id)
            k = await get_kingdom(g.id)
            if not k:
                continue

            ch = g.system_channel or (g.text_channels[0] if g.text_channels else None)
            if not ch:
                continue

            # Auto-crown for tiny servers (1-2 players, no king)
            if not k.get("king_id"):
                total = await get_total_players(g.id)
                t = await get_active_tournament(g.id)
                if not t:
                    if total <= 2 and total >= 1:
                        warriors = await get_top_warriors(g.id, 1)
                        if warriors:
                            w = warriors[0]
                            await update_kingdom(g.id, king_id=w["user_id"],
                                king_crowned_at=datetime.utcnow().isoformat())
                            await add_coins(w["user_id"], g.id, 1000)
                            await add_player_item(w["user_id"], g.id, "King Trophy", "trophy")
                            try:
                                await ch.send(embed=discord.Embed(title="👑 A King Claims the Throne!",
                                    description=f"👑 With no challengers to stand against him, **{w['username']}** "
                                    f"claims the throne unopposed. A king by default — but a king nonetheless. ⚔️\n\n"
                                    f"💰 +1000 🪙 • 🏆 King Trophy",
                                    color=0xFFD700))
                            except: pass
                    elif total >= 2:
                        tc = self.bot.get_cog("TournamentCog")
                        if tc:
                            try:
                                await tc.trigger_tournament(g.id, ch,
                                    "The throne stands empty! The realm demands a ruler!")
                            except: pass
                continue

            # Weekly kingdom challenge event
            last = k.get("last_event")
            if last:
                try:
                    if datetime.utcnow() - datetime.fromisoformat(last) < timedelta(days=7):
                        continue
                except:
                    pass
            await update_kingdom(g.id, last_event=datetime.utcnow().isoformat())
            try:
                await ch.send(embed=discord.Embed(title="🏰 KINGDOM EVENT!",
                    description="⚔️ A Kingdom Challenge Event has begun!\n\n"
                    "Any Warrior whose stats exceed the King's may use `/challengeking` "
                    "to fight for the Crown!\n\n*Event lasts 24 hours.* 🏆",
                    color=0xFF6B35))
            except:
                pass

    @check_events.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(EventsCog(bot))
