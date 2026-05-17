import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import datetime

#Custom
from internal.DatabaseHandlerUnit import DatabaseHandler
DataBaseUnit = DatabaseHandler()

class AutoBotQuarantine(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        #Is the bot configurated?
        if not DataBaseUnit.is_configured(member.guild.id):
            return

        if not member.bot:
            #Wasnt bot
            print("was not a bot")
            return
        
        print("Was a bot")
        try:
            guild = member.guild

            securityAlert = False

            #Try to find the adder of the bot
            adder = None
            async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.bot_add):
                if entry.target.id == member.id:
                    adder = entry.user
                    break
            else:
                adder = None

            REPORT_CHANNEL = DataBaseUnit.get_report_channel(guild.id)

            if adder.id == guild.owner.id: #If the bot was installed by owner
                if REPORT_CHANNEL:
                    channel = guild.get_channel(REPORT_CHANNEL)
                    if channel:
                        embed = discord.Embed(
                            title=":information_source: Security Notification, new Bot joined :information_source:",
                            description=(
                                f"**Bot name:** {member.mention}\n"
                                f"**ID:** {member.id}\n"
                                f"This bot was installed by the server owner, {guild.owner.mention}.\n\n"
                                f"I will be monitoring it!"
                            ),
                            color=discord.Color.orange()
                        )
                        await channel.send(embed=embed)
            else: #Bot was installed by someone else than owner (AutoQuarantine)
                #Set the string variable
                adderName = "Unkown"
                if adder:
                    adderName = f"{adder.mention}"

                quarantine_role = discord.utils.get(guild.roles, name="quarantined")
                if not quarantine_role:
                    
                    bot_member = guild.me
                    bot_top_role = bot_member.top_role
                    roles = guild.roles
                    position = bot_top_role.position - 1
                    if position <= 1:
                        position = 1 #Dont go too low

                    quarantine_role = await guild.create_role(
                        name="quarantined",
                        permissions=discord.Permissions.none(),
                        reason="Initialize quarantine role"
                    )

                    for channel in guild.channels:
                        try:
                            await channel.set_permissions(quarantine_role, send_messages=False, view_channel=False)
                        except:
                            continue
                    
                await member.add_roles(quarantine_role, reason="Unverified bot joined - automatic quarantine protocol")

                unverified_role = discord.utils.get(guild.roles, name="unverified")
                if not unverified_role:
                    unverified_role = await guild.create_role(
                        name="unverified",
                        permissions=discord.Permissions.none(),
                        color=discord.Color.from_rgb(0, 0, 0),
                        reason="Unverified bot"
                    )

                    for channel2 in guild.channels:
                        try:
                            await channel2.set_permissions(unverified_role, send_messages=False, view_channel=False)
                        except:
                            continue

                    bot_member = guild.me
                    bot_top_role = bot_member.top_role
                    roles = guild.roles
                    position = bot_top_role.position - 2
                    if position <= 1:
                        position = 1 #Dont go too low
                            
                await member.add_roles(unverified_role, reason="Unverified bot joined - automatic quarantine protocol")

                max_timeout = datetime.timedelta(days=28)
                timeout_total = discord.utils.utcnow() + max_timeout
                await member.edit(timed_out_until=timeout_total, reason="Quarantined by AntiNR")

                #Check if the role order is correct
                bot_member2 = guild.me
                bot_top_role2 = bot_member2.top_role
                if (quarantine_role.position != bot_top_role2.position - 1 or unverified_role.position != bot_top_role2.position - 2):
                    securityAlert = True

                additionalText = ""
                if (securityAlert):
                    additionalText = "\n\n:warning: **Security warning, quarantine or/and unverified role level is too low. Make sure that the quarantine role is below AntiNR bot role to prevent persons removing the role. :warning:** "

                if REPORT_CHANNEL:
                    print("Channel found")
                    channel = guild.get_channel(REPORT_CHANNEL)
                    if channel:
                        embed = discord.Embed(
                            title=":warning: Security Alert, unverified Bot joined :warning:",
                            description=(
                                f"**Bot Name:** {member.mention}\n"
                                f"**ID:** {member.id}\n"
                                f"**Installed by:** {adderName}\n\n"
                                f"{guild.owner.mention}, please verify this bot before it can interact with the server.\n"
                                f"The bot has been placed in quarantine and marked as unverified."
                                f"{additionalText}"
                            ),
                            color=discord.Color.orange()
                        )

                        await channel.send(embed=embed)
                else:
                    print("Channel was not found")
        except Exception as e:
            print(f"{e} occured")

async def setup(bot):
    await bot.add_cog(AutoBotQuarantine(bot))