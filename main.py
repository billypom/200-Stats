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
        await ctx.respond('Sorry! An unknown error occurred.')
        logging.warning(f'ERROR | ctx: {ctx} | error: {error}')
        return
    
if __name__ == "__main__":
    client.run(config.TOKEN)
