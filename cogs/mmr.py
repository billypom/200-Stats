from discord.ext import commands
import DBA

class MMR(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.slash_command(
        name='mmr',
        description='Your mmr',
    )
    async def mmr(self, ctx):
        await ctx.defer(ephemeral=True)
        try:
            with DBA.DBAccess() as db:
                temp = db.query('SELECT p.mmr, r.rank_name FROM player as p JOIN ranks as r ON p.rank_id = r.rank_id WHERE p.player_id = %s;', (ctx.author.id,))
                mmr = temp[0][0]
                rank_name = temp[0][1]
            if temp:
                pass
            else:
                await ctx.respond('Player not found')
                return
            if mmr is None:
                mmr = "n/a"
            await ctx.respond(f'`MMR:` {mmr}\n`Rank:` {rank_name}')
            return
        except Exception as e:
            await ctx.respond('Player not found.')
            return

def setup(client):
    client.add_cog(MMR(client))
