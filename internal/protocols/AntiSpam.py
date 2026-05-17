import time
from collections import defaultdict, deque
from discord.ext import commands
import discord
import dotenv
import os
import datetime
import asyncio

#Custom
from internal.DatabaseHandlerUnit import DatabaseHandler
DataBaseUnit = DatabaseHandler()

MAX_MESSAGES = int(os.getenv("MAX_MESSAGES")) #How much messages
TIME_WINDOW = float(os.getenv("TIME_WINDOW")) #In time
WARNING_COOLDOWN = float(os.getenv("WARNING_COOLDOWN")) #After this, the bot resends warning (cooldown)
HOURS = int(os.getenv("TIMEOUT_HOURS"))
WARN_RESET_DELAY = float(os.getenv("WARN_RESET_DELAY"))

class AntiSpam(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_messages = defaultdict(lambda: deque())
        self.warned_users = {}
        self.warn_times = {}
        self.warn_reset_tasks = {}
    
    @commands.Cog.listener()
    async def on_message(self, message):
        #Is the bot configurated?
        if not DataBaseUnit.is_configured(message.guild.id):
            return

        if message.author.id == self.bot.user.id:
            return #Ignore the messages sent by this
        elif message.author.id == message.guild.owner.id:
            return #Ignore messages from owner of the server

        now = time.time()
        uid = message.author.id
        timestamps = self.user_messages[uid]
        timestamps.append(now)

        REPORT_CHANNEL = DataBaseUnit.get_report_channel(message.guild.id)

        while timestamps and now - timestamps[0] > TIME_WINDOW:
            timestamps.popleft()
        
        if len(timestamps) > MAX_MESSAGES:
            #Exceeded the limit
            if message.author.bot:
                #If it was a bot
                guild = message.guild
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
                
                await message.author.add_roles(quarantined_role, reason="Quarantined by AntiNR")
                channel = guild.get_channel(REPORT_CHANNEL)
                if channel:
                    embed = discord.Embed(
                        title=":warning: Protocol Violation :warning:",
                        description=(
                            f"**Protocol:** AntiSpam\n"
                            f"**Violator:** {message.author.mention}\n"
                            f"**Countermeasures:** Quarantined\n\n"
                            f"Moderators, please analyze the situation."
                        ),
                        color=discord.Color.orange()
                    )
                    await channel.send(embed=embed)
                    

            elif isinstance(message.author, discord.Member):
                #If it was user
                last_warn = self.warned_users.get(uid, 0)
                if now - last_warn > WARNING_COOLDOWN:
                    self.warned_users[uid] = now
                    if not uid in self.warn_times:
                        self.warn_times[uid] = 0

                    if uid in self.warn_reset_tasks:
                        self.warn_reset_tasks[uid].cancel()
                    
                    self.warn_reset_tasks[uid] = asyncio.create_task(self.reset_warn_later(uid))

                    if self.warn_times[uid] == 0:
                        #First warning
                        await message.channel.send(f":warning: {message.author.mention}, you are sending messages too fast. Slow down!")
                        self.warn_times[uid] = self.warn_times[uid] + 1
                    elif self.warn_times[uid] == 1:
                        #Second warning
                        await message.channel.send(f":warning: {message.author.mention}, you are sending messages too fast. Stop!")
                        self.warn_times[uid] = self.warn_times[uid] + 1
                    elif self.warn_times[uid] == 2:
                        #Third and last warning
                        await message.channel.send(f":warning: {message.author.mention}, you are sending messages too fast. This is your last warning, stop!")
                        self.warn_times[uid] = self.warn_times[uid] + 1
                    elif self.warn_times[uid] > 2:
                        #Give timeout
                        self.warn_times[uid] = 0
                        timeout = datetime.timedelta(hours=HOURS)
                        timeout_total = discord.utils.utcnow() + timeout
                        await message.author.edit(timed_out_until=timeout_total, reason="Spamming")
                        await message.channel.send(f":information_source: {message.author.mention} was muted for {HOURS} hour(s) by AntiSpam protocol")

                        guild = message.guild
                        channel = guild.get_channel(REPORT_CHANNEL)
                        if channel:
                            embed = discord.Embed(
                                title=":warning: Protocol Violation :warning:\n",
                                description=(
                                    f"**Protocol:** AntiSpam\n"
                                    f"**Violator:** {message.author.mention}\n"
                                    f"**Countermeasures:** {HOURS} hour(s) mute"
                                ),
                                color=discord.Color.orange()
                            )
                            await channel.send(embed=embed)
                    else:
                        await message.channel.send(f":warning: {message.author.mention}, you are sending messages too fast. Slow down!")
            else:
                #Unkown sender
                guild = message.guild
                channel = guild.get_channel(REPORT_CHANNEL)
                if channel:
                    embed = discord.Embed(
                        title=":warning: Protocol Violation :warning:\n",
                        description=(
                            f"**Protocol:** AntiSpam\n"
                            f"**Violator:** {message.author.mention}\n"
                            f"**Countermeasures:** ERROR: message.author type is unkown\n"
                            f"**WARNING: This sender is unkown. Moderators, please resolve the situation manually."
                        ),
                        color=discord.Color.orange()
                    )
                    await channel.send(embed=embed)

    async def reset_warn_later(self, uid):
        try:
            await asyncio.sleep(WARN_RESET_DELAY)
            self.warn_times[uid] = 0
            del self.warn_reset_tasks[uid]
        except asyncio.CancelledError:
            pass #Resetting was interrupted due new warn message

async def setup(bot):
    await bot.add_cog(AntiSpam(bot))