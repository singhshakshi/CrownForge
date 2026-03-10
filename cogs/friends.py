"""cogs/friends.py — Friends with guild_id."""
import discord
from discord import app_commands
from discord.ext import commands
from database import send_friend_request, accept_friend_request, decline_friend_request, get_friends, remove_friend, are_friends
from helpers import check_jail

class FRView(discord.ui.View):
    def __init__(self,fid,tid,gid):
        super().__init__(timeout=120); self.fid,self.tid,self.gid=fid,tid,gid
    async def interaction_check(self,i):
        if i.user.id!=self.tid: await i.response.send_message("❌",ephemeral=True); return False
        return True
    @discord.ui.button(label="Accept ✅",style=discord.ButtonStyle.success)
    async def acc(self,i,b): await accept_friend_request(self.fid,self.tid,self.gid); self.stop(); await i.response.edit_message(embed=discord.Embed(title="✅ Friends!",color=0x2ECC71),view=None)
    @discord.ui.button(label="Decline ❌",style=discord.ButtonStyle.danger)
    async def dec(self,i,b): await decline_friend_request(self.fid,self.tid,self.gid); self.stop(); await i.response.edit_message(embed=discord.Embed(title="❌ Declined",color=0xE74C3C),view=None)

class FriendsCog(commands.Cog):
    def __init__(self,bot): self.bot=bot
    @app_commands.command(name="addfriend",description="👥 Send friend request!")
    @app_commands.describe(target="Player")
    async def addfriend(self,interaction:discord.Interaction,target:discord.Member):
        gid=interaction.guild.id
        if await check_jail(interaction): return
        r=await send_friend_request(interaction.user.id,target.id,gid)
        if r!="sent": return await interaction.response.send_message(embed=discord.Embed(title="❌",description=r,color=0xF39C12),ephemeral=True)
        await interaction.response.send_message(embed=discord.Embed(title="👥 Friend Request!",description=f"To {target.mention}",color=0x3498DB),
            view=FRView(interaction.user.id,target.id,gid))

    @app_commands.command(name="friends",description="👥 Friend list.")
    async def friends(self,interaction:discord.Interaction):
        gid=interaction.guild.id
        if await check_jail(interaction): return
        fl=await get_friends(interaction.user.id,gid)
        if not fl: return await interaction.response.send_message(embed=discord.Embed(title="👥 No Friends",color=0x95A5A6))
        e=discord.Embed(title="👥 Friends",color=0x3498DB)
        for f in fl[:20]:
            me={"happy":"😊","sad":"😢"}.get(f.get("mood",""),"😐")
            e.add_field(name=f["username"],value=f"Lvl {f['level']} {f['class']} {me}",inline=True)
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="removefriend",description="👥 Remove friend.")
    @app_commands.describe(target="Friend")
    async def removefriend(self,interaction:discord.Interaction,target:discord.Member):
        gid=interaction.guild.id
        if await check_jail(interaction): return
        if not await are_friends(interaction.user.id,target.id,gid): return await interaction.response.send_message(embed=discord.Embed(title="❌",description="Not friends!",color=0xE74C3C),ephemeral=True)
        await remove_friend(interaction.user.id,target.id,gid)
        await interaction.response.send_message(embed=discord.Embed(title="👥 Removed",color=0x95A5A6))

async def setup(bot): await bot.add_cog(FriendsCog(bot))
