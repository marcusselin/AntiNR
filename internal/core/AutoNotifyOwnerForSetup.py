from discord.ext import commands
import discord

class AutoNotifier(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        owner = guild.owner

        try:
            if owner is not None:
                embed = discord.Embed(
                    title=":warning: Manual setup required :warning:",
                    description=(
                        f"{owner.mention}, you must first configure me before my protocols and commands will be activated on your server ({guild.name})\n"
                        f"Use '/setup' to configurate me for your awesome server!"
                    ),
                    color=discord.Color.orange()
                )
                embed.set_footer(text=f"Thank you for choosing me! If you need any help, check my bio for link to our discord support server!")
                await owner.send(embed=embed)
        except discord.Forbidden:
            print("ERR: Failed to send message to {owner}")

async def setup(bot):
    await bot.add_cog(AutoNotifier(bot))