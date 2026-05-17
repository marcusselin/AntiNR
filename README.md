## Usage

### Installation

1. Download newest release
2. Install following depencies:
```
discord.py
python-dotenv
```
   with 
```
pip install discord.py python-dotenv
```

### Configuring

Open `configuration/conf.env`, add your discord bot token and configure other fields with values of your liking.

## Modifying

### Custom modules! 

AntiNR is coded with modularity on mind. Put your custom core modules to `internal/core` and secondary modules (protocols) to `internal/protocols`.
You can use this template on each new module .py file you create to those directories:
```
from discord.ext import commands
import discord

class NewModule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    #Example - add your own listeners
    async def on_guild_join(self, guild: discord.Guild):
        print("hello!")

async def setup(bot):
    await bot.add_cog(NewModule(bot))
```
### Secure configuration base!
Put your custom configuration to your `conf.env` file in `configuration`, and load them using `os.getenv(var_name)`.