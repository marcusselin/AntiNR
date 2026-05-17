import discord #import default configurations
import os #import os
from dotenv import load_dotenv #import .env reader
from discord.ext import commands #import command configuration
from discord import app_commands
from pathlib import Path
import datetime
from datetime import datetime
import sys

#Load discord token from local file
load_dotenv("configuration/conf.env")
TOKEN = os.getenv("TOKEN")
CHANNEL_ID = os.getenv("SERVERID")
CURRENT_VERSION = os.getenv("VERSION")

#Custom
from internal.DatabaseHandlerUnit import DatabaseHandler
DataBaseUnit = DatabaseHandler()

guild = discord.Object(id=CHANNEL_ID)
#Initialize
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="/", intents=intents, help_command=None)

#UTILITIES-----------------------------------------------------------------------------------------
def logMessage(type, message):
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{time}] [{type}] {message}")
#INIT-----------------------------------------------------------------------------------------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    #Setting up the activity for the bot when its running
    activity = discord.Game(name=f"Protecting {len(bot.guilds)} servers from raids & nukes!")
    await bot.change_presence(status=discord.Status.do_not_disturb, activity=activity)

    #Import modules
    #Setup dirs
    local_directory = Path(__file__).parent
    core = local_directory / "internal" / "core"
    protocols = local_directory / "internal" / "protocols"
    core_path = "internal.core."
    protocol_path = "internal.protocols."

    #Load core modules
    try:
        for module in core.rglob("*"):
            if (module.is_file() and module.suffix == ".py"):
                await bot.load_extension(f"{core_path}{module.stem}")
                logMessage("INFO", f"Successfully loaded core module \"{module.stem}\"")
    except Exception as e:
        logMessage("FATAL_ERROR", f"CORE PANIC:\nFailed to load core module \"{module.stem}\"on init:\n{e}")
        await bot.close()
        sys.exit(1)

    #Load secondary modules: protocols
    for module in protocols.rglob("*"):
        if (module.is_file() and module.suffix == ".py"):
            try:
                await bot.load_extension(f"{protocol_path}{module.stem}")
                logMessage("INFO", f"Successfully loaded protocol module \"{module.stem}\"")
            except Exception as e:
                logMessage("ERROR", f"Failed to load protocol \"{module.stem}\":\n{e}\nIgnoring module \"{module.stem}\".")
                continue

    #await bot.tree.clear_commands(guild=)

    try:
        synced = await bot.tree.sync() #guild=guild for spesific server
        print(f"Synced total of {len(synced)} commands")
    except Exception as e:
        print(f"Error: {e}")

#COMMANDS-----------------------------------------------------------------------------------------
@bot.tree.command(name="setup", description="Setup the bot")
@app_commands.describe(report_channel="Choose the channel where i send the security reports")
async def setup(interaction: discord.Interaction, report_channel: discord.TextChannel):
    await interaction.response.defer(thinking=True)

    #Set the report channel
    DataBaseUnit.set_report_channel(interaction.guild.id, report_channel.id)

    #Setup quarantine role
    quarantine_role = discord.utils.get(interaction.guild.roles, name="quarantined")
    if not quarantine_role:
        quarantine_role = await interaction.guild.create_role(
            name="quarantined",
            permissions=discord.Permissions.none(),
            reason="Initialize quarantine role",
            color=discord.Colour.dark_red()
        )

        #Disable permissions
        for channel in interaction.guild.channels:
            try:
                await channel.set_permissions(quarantine_role, send_messages=False, view_channel=False)
            except:
                continue
                
    #Setup the unverified role
    unverified_role = discord.utils.get(interaction.guild.roles, name="unverified")
    if not unverified_role:
        unverified_role = await interaction.guild.create_role(
            name="unverified",
            permissions=discord.Permissions.none(),
            color=discord.Color.from_rgb(0, 0, 0),
            reason="Unverified bot"
        )

        for channel2 in interaction.guild.channels:
            try:
                await channel2.set_permissions(unverified_role, send_messages=False, view_channel=False)
            except:
                continue
    #Make sure the role is in proper position, so that the mods cannot remove it
    #Quarantined role
    bot_member = interaction.guild.me
    bot_top_role = bot_member.top_role
    roles = interaction.guild.roles
    position = bot_top_role.position - 1
    if position <= 1:
        position = 1 #Dont go too low

    #Unverified role
    bot_member2 = interaction.guild.me
    bot_top_role2 = bot_member2.top_role
    roles = interaction.guild.roles
    position2 = bot_top_role2.position - 2
    if position2 <= 1:
        position2 = 1 #Dont go too low

    await interaction.guild.edit_role_positions(positions={
        quarantine_role: position,
        unverified_role: position2
    })

    #Result
    await interaction.followup.send("Setup successful!")

#Quarantine
@bot.tree.command(name="quarantine", description="Set user/bot into quarantine")
@app_commands.describe(target="User/Bot to be set into quarantine")
async def quarantine(interaction: discord.Interaction, target: discord.Member):
    await interaction.response.defer(thinking=True)

    #Is the bot configurated?
    if not DataBaseUnit.is_configured(interaction.guild.id):
        await interaction.followup.send(f"Cannot run commands and protocols without configuration. {interaction.guild.owner.mention}, Use /setup to initialize me.\n*Error code: ConfNotFound*")
        return

    #Does the user have necessary permissions?
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.followup.send(f"{interaction.user.mention}, you dont have permission to run this command!", ephemeral=True)
        return

    try:
        quarantine_role = discord.utils.get(interaction.guild.roles, name="quarantined")
        if quarantine_role and quarantine_role in target.roles:
            await interaction.followup.send(f"User/Bot {target.name} is already in quarantine!", ephemeral=True)
            return
        
        #Bot cannot quarantine itself
        if target.id == interaction.client.user.id:
            await interaction.followup.send(f"I can't quarantine myself :face_with_spiral_eyes:")
            return

        #Owner cannot be quarantined
        if target == interaction.guild.owner:
            await interaction.followup.send(f"You really think i could quarantine the owner of this server :rolling_eyes:")
            return

        #Give timeout
        max_timeout = datetime.timedelta(days=28)
        timeout_total = discord.utils.utcnow() + max_timeout
        await target.edit(timed_out_until=timeout_total, reason="Quarantined by AntiNR")

        #Remove roles
        removed_roles = []
        for role in target.roles:
            if role.is_default():
                continue
            try:
                await target.remove_roles(role, reason="Quarantine")
                removed_roles.append(role.name)
            except:
                continue
        
        #Give quarantined role
        if not quarantine_role:
            quarantine_role = await interaction.guild.create_role(
                name="quarantined",
                permissions=discord.Permissions.none(),
                reason="Initialize quarantine role",
                color=discord.Colour.dark_red()
            )

            #Make sure the role is in proper position, so that the mods cannot remove it
            bot_member = interaction.guild.me
            bot_top_role = bot_member.top_role
            roles = interaction.guild.roles
            position = bot_top_role.position - 1
            if position <= 1:
                position = 1 #Dont go too low

            await interaction.guild.edit_role_positions(positions={quarantine_role: position})   

            #Disable permissions
            for channel in interaction.guild.channels:
                try:
                    await channel.set_permissions(quarantine_role, send_messages=False, view_channel=False)
                except:
                    continue
        
        #Make sure the quarantined role is just below the bot highest role
        bot_member = interaction.guild.me
        bot_top_role = bot_member.top_role

        securityAlert = False

        if quarantine_role.position != bot_top_role.position - 1:
            print("Was too low!")
            securityAlert = True
            target_position = bot_top_role.position - 1
            if target_position <= 1:
                target_position = 1
            
            await interaction.guild.edit_role_positions(positions={quarantine_role: target_position})
         
        
        await target.add_roles(quarantine_role, reason="Quarantined by AntiNR")

        additionalText = ""
        if securityAlert:
            additionalText = "\n:warning: **Security warning, quarantine role level is too low. Make sure that the quarantine role is below AntiNR bot role to prevent persons removing the role. :warning:** "

        await interaction.followup.send(
            f":white_check_mark: {target.mention} has been set into quarantine:\n"
            f":hourglass: Timeout: {max_timeout.days} days\n"
            f":no_entry: Removed roles: {', '.join(removed_roles) if removed_roles else 'nothing'}\n"
            f":lock: Locked all permission by giving quarantined role ({quarantine_role.name})"
            f"{additionalText}"
        )

    except Exception as e:
        await interaction.followup.send(f":warning: Error {e} occured while attempting to set {target.name} to quarantine! :warning:", ephemeral=True)

#Release from quarantine
@bot.tree.command(name="release", description="Releases user/bot from quarantine")
@app_commands.describe(target="User/Bot to be released from quarantine")
async def release(interaction: discord.Interaction, target: discord.Member):
    #Is the bot configurated?
    if not DataBaseUnit.is_configured(interaction.guild.id):
        await interaction.response.send_message(f"Cannot run commands and protocols without configuration. {interaction.guild.owner.mention}, Use /setup to initialize me.\n*Error code: ConfNotFound*")
        return
    
    #Does the user have permissions?
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message(f"{interaction.user.mention}, you dont have permission to run this command!", ephemeral=True)
        return
    
    #Bot cannot release itself
    if target.id == interaction.client.user.id:
        await interaction.response.send_message(f"I can't release myself from quarantine :face_with_spiral_eyes:")
        return
    
    #Bot cannot release owner
    if target == interaction.guild.owner:
        await interaction.response.send_message(f"I can't do that :expressionless:")
        return
        
    try:
        quarantine_role = discord.utils.get(interaction.guild.roles, name="quarantined")
        unverified_role = discord.utils.get(interaction.guild.roles, name="unverified")

        #If user is not in quarantine
        if not quarantine_role or quarantine_role not in target.roles:
            await interaction.response.send_message(
                f":information_source: {target.name} is not in quarantine!", ephemeral=True
            )
            return
        
        if unverified_role and unverified_role in target.roles:
            await interaction.response.send_message(
                f":no_entry: {target.name} is unverified, and can only be released by owner!", ephemeral=True
            )
            return

        #Remove timeout
        await target.edit(timed_out_until=None, reason="Released from quarantine")

        #Remove quarantine role (return the permissions)
        await target.remove_roles(quarantine_role, reason="Released from quarantine")

        await interaction.response.send_message(
            f":unlock: {target.name} was released from quarantine!"
        )
    except Exception as e:
        await interaction.response.send_message(f":warning: Error {e} occured while attempting to release {target.name} from quarantine! :warning:", ephemeral=True)   

#Verify

@bot.tree.command(name="verifybot", description="Verifies bot")
@app_commands.describe(target="Bot to be verified")
async def verifybot(interaction: discord.Interaction, target: discord.Member):
    #Is the bot configurated?
    if not DataBaseUnit.is_configured(interaction.guild.id):
        await interaction.response.send_message(f"Cannot run commands and protocols without configuration. {interaction.guild.owner.mention}, Use /setup to initialize me.\n*Error code: ConfNotFound*")
        return
    
    if not target.bot:
        await interaction.response.send_message(":no_entry: Target is not a bot. You can only verify an bot!")
        return

    if interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message(f":no_entry: {interaction.user.mention}, only the owner can verify!")
        return

    await interaction.response.defer(thinking=True)

    #Remove roles
    quarantine_role = discord.utils.get(interaction.guild.roles, name="quarantined")
    unverified_role = discord.utils.get(interaction.guild.roles, name="unverified")

    roles_to_remove = []
    if unverified_role and unverified_role in target.roles:
        if quarantine_role and quarantine_role in target.roles:
            roles_to_remove.append(quarantine_role)
            roles_to_remove.append(unverified_role)
        else:
            await interaction.followup.send(f":no_entry: Invalid user")
            return
    else:
        await interaction.followup.send(f":no_entry: This bot is already verified!")
        return
    
    try:
        if roles_to_remove:
            await target.remove_roles(*roles_to_remove, reason="Bot verified by server owner")

        #Remove timeout
        await target.edit(timed_out_until=None, reason="Bot verified by server owner")

        await interaction.followup.send(f":white_check_mark: Bot {target.name} was verified by owner, and was released from quarantine. However, i will still monitor it!")
    except Exception as e:
        await interaction.followup.send(f":warning: {e} occured while attempting to verify {target.name}")


#Info
@bot.tree.command(name="info", description="Info about the bot")
async def info(interaction: discord.Interaction):
    await interaction.response.send_message(
        f"### AntiRN - info\n"
        f"*I am the shield against raiders & nukes!*\n"
        f"Developed proudly by AntiRN team\n"
        f"Use /help to get information about the commands avaible\n"
        f"Client version {CURRENT_VERSION}\n\n"
        f"Join our discord for more info & support! You can find it in my bio. Thank you for choosing our bot!"
    )

#Help
@bot.tree.command(name="help", description="View all avaible commands")
async def help(interaction: discord.Interaction):
    commands = bot.tree.get_commands(guild=guild)
    help_text = "### Avaible commands\n"
    
    for cmd in commands:
        help_text += f"/{cmd.name} - {cmd.description}\n"

    await interaction.response.send_message(help_text)

#MAIN----------------------------------------------------------------------------------------------
# :)
bot.run(TOKEN)