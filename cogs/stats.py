import discord
from discord.ext import commands
import DBA
from helpers.checkers import check_if_banned_characters
from helpers.senders import send_to_verification_log
from helpers.getters import get_partner_avg
from helpers.getters import get_tier_id_list
from helpers import iso_country_to_emoji
import subprocess
import operator
import plotting
import config
import vlog_msg


class StatsCog(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.slash_command(
        name="stats",
        description="Player statistics",
    )
    async def stats(
        self,
        ctx,
        tier: discord.Option(
            str, description="Which tier? (a, b, c, all, sq)", required=False
        ),
        mogi_format: discord.Option(
            int, description="Your choices: (1, 2, 3, 4, 6)", required=False
        ),
        last: discord.Option(int, description="How many mogis?", required=False),
        player: discord.Option(str, description="Which player?", required=False),
        season: discord.Option(int, description="Season number (5, 6)", required=False),
    ):
        await ctx.defer()
        # Validate strings
        # Season picker
        if config.DTB == "lounge_dev":
            stats_db = "lounge_dev"
        else:
            stats_db = f"s{config.CURRENT_SEASON}200lounge"
            if season is None:
                pass
            else:
                try:
                    if season in [5, 6]:
                        pass
                    else:
                        await ctx.respond("Invalid season")
                        return
                    stats_db = f"s{int(season)}200lounge"
                except Exception as e:
                    await ctx.respond("Invalid season")
                    return
        # Tier picker
        if tier is None:
            pass
        else:  # User entered a value, so check it
            bad = await check_if_banned_characters(tier)
            if bad:
                await ctx.respond("Invalid tier")
                await send_to_verification_log(self.client, ctx, tier, vlog_msg.error1)
                return
            # Retrieve tier ID and api request the discord.TextChannel object
            try:
                with DBA.DBAccess(stats_db) as db:
                    tier_id = db.query(
                        "SELECT tier_id FROM tier WHERE tier_name = %s;", (tier,)
                    )[0][0]
                    tier_channel = f"tier-{tier}"
            except Exception as e:  # bad input 2 - no tier by that name
                await ctx.respond("Invalid tier")
                return
        # Status for self or others
        if player is None:
            pass
        else:
            bad = await check_if_banned_characters(player)
            if bad:
                await ctx.respond("Invalid player")
                await send_to_verification_log(
                    self.client, ctx, player, vlog_msg.error1
                )
                return
            # Retrieve player ID
            try:
                with DBA.DBAccess(stats_db) as db:
                    player_id = db.query(
                        "SELECT player_id FROM player WHERE player_name = %s;",
                        (player,),
                    )[0][0]
            except Exception:  # bad input 2 - no player by that name
                await ctx.respond("Invalid player")
                return
        # Last n mogis
        if last is None:
            number_of_mogis = 999999
        else:
            if last < 0:
                await ctx.respond(
                    f"You will score 180 and gain 99999 MMR in the next {abs(last)} mogi(s)."
                )
                return
            number_of_mogis = last

        # Format picker
        mogi_format_list = []
        if mogi_format is None:
            mogi_format_list = [1, 2, 3, 4, 6]
        elif mogi_format in [1, 2, 3, 4, 6]:
            mogi_format_list.append(mogi_format)
        else:
            await ctx.respond(f"Invalid format: `{mogi_format}`")
            return
        mogi_format_string = ",".join(str(e) for e in mogi_format_list)

        if ctx.channel.id in await get_tier_id_list():
            await ctx.respond("`/stats` is not available in tier channels.")
            return
        mmr_history = []  #
        score_history = []  #
        mogi_id_history = []  #
        last_10_wins = 0  #
        last_10_losses = 0  #
        last_10_change = 0  #
        average_score = 0
        partner_average = 0
        top_score = 0  #
        events_played = 0  #
        largest_gain = 0  #
        largest_loss = 0  #
        rank = 0
        count_of_wins = 0
        if player is None:
            my_player_id = ctx.author.id
        else:
            my_player_id = player_id

        # Checks for valid player
        try:
            with DBA.DBAccess(stats_db) as db:
                temp = db.query(
                    "SELECT base_mmr, peak_mmr, mmr, player_name, country_code FROM player WHERE player_id = %s;",
                    (my_player_id,),
                )
                if temp[0][0] is None:
                    base = 0
                else:
                    base = temp[0][0]
                peak = temp[0][1]
                mmr = temp[0][2]
                player_name = temp[0][3]
                country_code = temp[0][4]
            with DBA.DBAccess(stats_db) as db:
                temp = db.query(
                    "SELECT COUNT(*) FROM player WHERE mmr >= %s ORDER BY mmr DESC;",
                    (mmr,),
                )
                rank = temp[0][0]
        except Exception as e:
            await ctx.respond("``Error 31:`` Player not found.")
            return

        # Get emoji flag for iso country
        emoji_flag = await iso_country_to_emoji(country_code)

        # Create matplotlib MMR history graph
        if tier is None:
            with DBA.DBAccess(stats_db) as db:
                sql = (
                    "SELECT pm.mmr_change, pm.score, pm.mogi_id FROM player_mogi pm JOIN mogi m ON pm.mogi_id = m.mogi_id WHERE pm.player_id = %s AND m.mogi_format IN (%s) ORDER BY m.create_date DESC LIMIT %s;"
                    % ("%s", mogi_format_string, "%s")
                )

                temp = db.query(
                    sql, (my_player_id, number_of_mogis)
                )  # order newest first

                try:
                    # This will fail and throw an exception if no matches are found in above query
                    did_u_play_yet = temp[0][0]
                except Exception:
                    await ctx.respond("You must play at least 1 match to use `/stats`")
                    return

                for i in range(len(temp)):
                    mmr_history.append(temp[i][0])  # append to list newest first
                    score_history.append(temp[i][1])
                    mogi_id_history.append(temp[i][2])
                    if (
                        i <= 9
                    ):  # if we are at the last 10 indexes (first 10, newest first)
                        last_10_change += mmr_history[i]
                        if mmr_history[i] > 0:
                            last_10_wins += 1
                        else:
                            last_10_losses += 1
            partner_average = await get_partner_avg(
                self.client,
                my_player_id,
                number_of_mogis,
                mogi_format_string,
                "%",
                stats_db,
            )
        elif tier_id in await get_tier_id_list():
            try:
                with DBA.DBAccess(stats_db) as db:
                    sql = (
                        "SELECT pm.mmr_change, pm.score, pm.mogi_id FROM player_mogi pm JOIN mogi m ON pm.mogi_id = m.mogi_id WHERE pm.player_id = %s AND m.tier_id = %s AND m.mogi_format IN (%s) ORDER BY m.create_date DESC LIMIT %s;"
                        % ("%s", "%s", mogi_format_string, "%s")
                    )

                    temp = db.query(sql, (my_player_id, tier_id, number_of_mogis))

                    for i in range(len(temp)):
                        mmr_history.append(temp[i][0])
                        score_history.append(temp[i][1])
                        mogi_id_history.append(temp[i][2])
                        if i <= 9:
                            last_10_change += mmr_history[i]
                            if mmr_history[i] > 0:
                                last_10_wins += 1
                            else:
                                last_10_losses += 1
            except Exception as e:
                await ctx.respond(f"You have not played in {tier_channel}")
                return
            partner_average = await get_partner_avg(
                self.client,
                my_player_id,
                number_of_mogis,
                mogi_format_string,
                tier_id,
                stats_db,
            )
        else:
            await ctx.respond(f"``Error 30:`` {tier_channel} is not a valid tier")
            return
        mmr_history.reverse()  # reverse list, oldest first for matplotlib
        score_history.reverse()
        mogi_id_history.reverse()

        events_played = len(mmr_history)
        try:
            top_index, top_score = max(
                enumerate(score_history), key=operator.itemgetter(1)
            )
        except Exception:
            await ctx.respond(f"You have not played in {tier_channel}")
            return
        top_mogi_id = mogi_id_history[top_index]

        try:
            largest_gain = max(mmr_history)
        except Exception:
            largest_gain = 0

        largest_loss = min(mmr_history)
        average_score = sum(score_history) / len(score_history)

        # Start at proper value for mmr graph
        if last is None:
            graph_base = base
        else:
            graph_base = mmr + (sum(mmr_history) * -1)

        for match in mmr_history:
            if match > 0:
                count_of_wins += 1
        win_rate = (count_of_wins / len(mmr_history)) * 100

        file = plotting.create_plot(graph_base, mmr_history)
        f = discord.File(file, filename="stats.png")

        title = "Stats"
        if tier is None:
            pass
        else:
            title += f" | tier-{tier}"

        if mogi_format is None:
            pass
        else:
            if int(mogi_format) == 1:
                title += " | FFA"
            else:
                title += f" | {mogi_format}v"

        if last is None:
            pass
        else:
            title += f" | Last {last}"

        red, green, blue = 129, 120, 118
        if mmr >= 1500:
            red, green, blue = 230, 126, 34
        if mmr >= 3000:
            red, green, blue = 125, 131, 150
        if mmr >= 4500:
            red, green, blue = 241, 196, 15
        if mmr >= 6000:
            red, green, blue = 0, 162, 184
        if mmr >= 7500:
            red, green, blue = 185, 242, 255
        if mmr >= 9000:
            red, green, blue = 0, 0, 0
        if mmr >= 11000:
            red, green, blue = 163, 2, 44
        rank_filename = "./images/rank.png"
        stats_rank_filename = "./images/stats_rank.png"

        rgb_flag = f"rgb({red},{green},{blue})"
        # correct = subprocess.run(['convert', rank_filename, '-fill', rgb_flag, '-tint', '100', stats_rank_filename])
        subprocess.run(
            [
                "convert",
                rank_filename,
                "-fill",
                rgb_flag,
                "-tint",
                "100",
                stats_rank_filename,
            ]
        )
        # f=discord.File(rank_filename, filename='rank.jpg')
        sf = discord.File(stats_rank_filename, filename="stats_rank.jpg")

        embed = discord.Embed(
            title=f"{title}",
            description=f"{emoji_flag} [{player_name}](https://200-lounge.com/player/{player_name})",
            color=discord.Color.from_rgb(red, green, blue),
        )  # website link
        embed.add_field(name="Rank", value=f"{rank}", inline=True)
        embed.add_field(name="MMR", value=f"{mmr}", inline=True)
        embed.add_field(name="Peak MMR", value=f"{peak}", inline=True)
        embed.add_field(name="Win Rate", value=f"{round(win_rate,0)}%", inline=True)
        embed.add_field(
            name="W-L (Last 10)",
            value=f"{last_10_wins} - {last_10_losses}",
            inline=True,
        )
        embed.add_field(name="+/- (Last 10)", value=f"{last_10_change}", inline=True)
        embed.add_field(
            name="Avg. Score", value=f"{round(average_score, 2)}", inline=True
        )
        embed.add_field(
            name="Top Score",
            value=f"[{top_score}](https://200-lounge.com/mogi/{top_mogi_id})",
            inline=True,
        )  # website link
        embed.add_field(name="Partner Avg.", value=f"{partner_average}", inline=True)
        embed.add_field(name="Events Played", value=f"{events_played}", inline=True)
        embed.add_field(name="Largest Gain", value=f"{largest_gain}", inline=True)
        embed.add_field(name="Largest Loss", value=f"{largest_loss}", inline=True)
        embed.add_field(name="Base MMR", value=f"{base}", inline=True)
        embed.set_thumbnail(url="attachment://stats_rank.jpg")
        embed.set_image(url="attachment://stats.png")
        # await channel.send(file=f, embed=embed)
        await ctx.respond(files=[f, sf], embed=embed)
        return


def setup(client):
    client.add_cog(StatsCog(client))
