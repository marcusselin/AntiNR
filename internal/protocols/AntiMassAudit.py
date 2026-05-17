import discord
from discord.ext import commands
import datetime
import os
import asyncio

#Custom
from internal.DatabaseHandlerUnit import DatabaseHandler
DataBaseUnit = DatabaseHandler()

MAX_ACTIONS = int(os.getenv("MAX_ACTIONS"))
TIME_WINDOW = int(os.getenv("TIME_WINDOW_A"))

class AntiMassAudit(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_auditlog_update(self, entry: discord.AuditLogEntry):
        user = entry.user
        guild = entry.guild
        print("hmm2")

        if not DataBaseUnit.is_configured(guild.id):
            return

        if user.id == self.bot.user.id:
            return #Ignore bot
        elif user.id == guild.owner.id:
            return #Ignore server owner
        
        #Add the action to the list
        now = datetime.datetime.utcnow().timestamp()
        actions = self.user_actions
        actions.append(now)
        print("hmm")

        while actions and now - actions[0] > TIME_WINDOW:
            actions.popleft()
        
        if len(actions) > MAX_ACTIONS:
            #Too much actions, set in quarantine
            self.user_actions[user.id].clear()

            try:
                guild = user.guild
                quarantined_role = discord.utils.get(guild.roles, name="quarantined")
                if not quarantined_role:
                    quarantined_role = await guild.create_role(
                        name="quarantined",
                        permissions=discord.Permissions.none(),
                        reason="Initialize quarantine role",
                        color=discord.Colour.dark_red()
                    )

                    bot_member = guild.me
                    bot_top_role = bot_member.top_role
                    roles = guild.roles
                    position = bot_top_role.position - 1
                    if position <= 1:
                        position = 1 #Dont go too low
                    
                    await guild.edit_role_positions(positions={quarantined_role: position})

                    #Disable permissions
                    for channel in guild.channels:
                        try:
                            await channel.set_permissions(quarantined_role, send_messages=False, view_channel=False)
                        except:
                            continue
                
                REPORT_CHANNEL = DataBaseUnit.get_report_channel(guild.id)

                await guild.author.add_roles(quarantined_role, reason="Quarantined by AntiNR")
                channel = guild.get_channel(REPORT_CHANNEL)
                if channel:
                    embed = discord.Embed(
                        title=":warning: Protocol Violation :warning:",
                        description=(
                            f"**Protocol:** AntiMassAudit\n"
                            f"**Violator:** {guild.author.mention}\n"
                            f"**Countermeasures:** Quarantined\n\n"
                            f"**:no_entry:WARNING possible server contamination :no_entry:**\n"
                            f"Moderators, please analyze the situation."
                        ),
                        color=discord.Color.orange()
                    )
                    await channel.send(embed=embed)
            except Exception as e:
                print(e)

async def setup(bot):
    await bot.add_cog(AntiMassAudit(bot))