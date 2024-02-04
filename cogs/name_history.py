from discord.ext import commands
from helpers import convert_datetime_to_unix_timestamp
import DBA
import discord
from config import NAME_CHANGE_DELTA_LIMIT

class NameHistory(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.slash_command(
        name='name_history',
        description='See your lounge name history',
    )
    async def name_history(self, ctx):
        await ctx.defer(ephemeral=True)
        player_id = ctx.author.id
        player_name_dict = {}
        latest_name_change_timestamp = 0
        try:
            with DBA.DBAccess() as db:
                temp = db.query('SELECT requested_name, create_date FROM player_name_request WHERE was_accepted = 1 AND player_id = %s ORDER BY create_date DESC LIMIT 20;', (player_id,))
                for name in temp:
                    timestamp = await convert_datetime_to_unix_timestamp(name[1])
                    timestamp = int(timestamp)
                    if latest_name_change_timestamp < timestamp:
                        latest_name_change_timestamp = timestamp
                    player_name_dict[name[0]] = f'<t:{timestamp}:d>'
        except Exception as e:
            await ctx.respond('An unknown error occured. Please try again later.')
        
        next_available_name_change_timestamp = latest_name_change_timestamp + NAME_CHANGE_DELTA_LIMIT
        print("i'm before the embed")
        print(next_available_name_change_timestamp)
        try:
            embed = discord.Embed(title='Name History', description=f'Next change: <t:{next_available_name_change_timestamp}:d>', color=discord.Color.blurple())
            print("the embed has been created.. now i will loop")
            for item in list(player_name_dict.items()):
                embed.add_field(name=item[0], value=item[1], inline=False)
            await ctx.respond(embed=embed, content=None)
        
        except Exception as e:
            print(e)


def setup(client):
    client.add_cog(NameHistory(client))
