import sys
import os
import discord
from discord.ext import commands
import logging
import config

log_format = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(filename='200stats.log', filemode='a', level=logging.INFO, format=log_format, datefmt='%Y-%m-%d %H:%M:%S')

project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.append(project_root)

intents = discord.Intents()
client = discord.Bot(intents=intents, activity=discord.Game(str('200cc Stats')))

# Load cogs  
for extension in config.COMMAND_EXTENSIONS:
    client.load_extension(f'cogs.{extension}')

@client.event
async def on_application_command_error(ctx, error):
    if ctx.guild is None:
        await ctx.respond('Sorry! My commands do not work in DMs.')
        return
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.respond(error, delete_after=10)
        return
    elif isinstance(error, commands.MissingRole):
        await ctx.respond('You do not have permission to use this command.', delete_after=20)
        return
    elif isinstance(error, commands.MissingAnyRole):
        await ctx.respond('You do not have permission to use this command.', delete_after=20)
        return
    else:
        await ctx.respond('Sorry! An unknown error occurred.')
        return
    
if __name__ == "__main__":
    client.run(config.TOKEN)
