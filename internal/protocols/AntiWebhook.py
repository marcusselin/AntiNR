import discord
import os
from discord.ext import commands, tasks

#Custom
from internal.DatabaseHandlerUnit import DatabaseHandler
DataBaseUnit = DatabaseHandler()

class AntiWebhook(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.checked_ones = []

    @commands.Cog.listener()
    async def on_webhooks_update(self, channel):
        guild = channel.guild
        REPORT_CHANNEL = DataBaseUnit.get_report_channel(guild.id)

        #Is the bot configurated?
        if not DataBaseUnit.is_configured(guild.id):
            return

        try:
            async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.webhook_create):
                webhook = entry.target
                webhook_name = webhook.name if hasattr(webhook, "name") else "Unkown"
                installer = entry.user
                report_channel = guild.get_channel(REPORT_CHANNEL)

                if (discord.utils.utcnow() - entry.created_at).total_seconds() > 5:
                    continue #Pass older ones

                if webhook.id in self.checked_ones:
                    #If this webhook is already checked, pass it
                    self.checked_ones.remove(webhook.id)
                    continue

                if webhook.channel.id == channel.id:
                    #Allow owner of the server to install webhooks, but send an security notification
                    self.checked_ones.append(webhook.id)

                    if installer == guild.owner:
                        if report_channel:
                            embed = discord.Embed(
                                title=":information_source: Security Notification, new webhook was installed :information_source:",
                                description=(
                                    f"**Webhook:** {webhook_name}\n"
                                    f"**ID:** {webhook.id}\n"
                                    f"This webhook was installed by the server owner, {guild.owner.mention}.\n\n"
                                    f"I will be monitoring it!"
                                ),
                                color=discord.Color.orange()
                            )
                            await report_channel.send(embed=embed)
                        return
                    
                    #Remove unauthorized webhook
                    success = True
                    try:
                        await webhook.delete(reason="Unauthorized webhook creation, removed by AntiRN AntiWebhook protocol")
                    except Exception as e:
                        success = False
                        print(f"Error occured while attempting to remove webhook: {e}")
                    
                    #Send alert to moderators & owner of the server
                    desc_success=(
                        f"**Protocol:** AntiWebhook\n"
                        f"**Violator:** {installer.mention}\n"
                        f"**Countermeasures:** Deleted unauthorized webhook '{webhook_name}'\n\n"
                        f"Only the owner({guild.owner.mention}) can install webhooks!"
                    )
                    
                    desc_failure=(
                        f"**Protocol:** AntiWebhook\n"
                        f"**Violator:** {installer.mention}\n"
                        f"**Countermeasures:** ERROR: Failed to delete unauthorized webhook '{webhook_name}' (only the owner({guild.owner.mention}) is authorized to install webhooks)\n\n"
                        f"Moderators, this requires your immediate actions."
                    )

                    report_channel = guild.get_channel(REPORT_CHANNEL)
                    if report_channel:
                        embed = discord.Embed(
                            title=":warning: Protocol Violation :warning:",
                            description= desc_success if success else desc_failure,
                            color=discord.Color.orange()
                        )
                        await report_channel.send(embed=embed)
                    
                    break
        except Exception as e:
            print(f"Error while trying to analyze webhooks ({e})")

async def setup(bot):
    await bot.add_cog(AntiWebhook(bot))