from discord.ext import commands
import discord
import yaml
from asyncio import sleep
from datetime import datetime
import re
from main import get_database
mongodb = get_database()

async def seconds_to_fancytime(seconds, granularity):
    result = []
    intervals = (
        ('days', 86400),
        ('hours', 3600),
        ('minutes', 60),
        ('seconds', 1),
    )

    for name, count in intervals:
        value = seconds // count
        if value:
            seconds -= value * count
            if value == 1:
                name = name.rstrip('s')
            result.append(str(value) + " " + name)
    if len(result) > 1:
        result[-1] = "and " + result[-1]
    if len(result) < 3:
        return ' '.join(result[:granularity])
    else:
        return ', '.join(result[:granularity])

class misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    with open('config.yaml', 'r') as config_file:
        config = yaml.load(config_file, Loader=yaml.BaseLoader)
    global channel_ids
    channel_ids = config['channel_ids']
    global role_ids
    role_ids = config['role_ids']

    @commands.command()
    async def alert(self, ctx, *, description=None):
        if description:
            alert = description
        else:
            alert = "A description was not provided."
        embed = discord.Embed(title="Moderator Alert", description=f"[Jump to message]({ctx.message.jump_url})\n{alert}", color=discord.Color.red())
        embed.add_field(name="Alert Author", value=ctx.message.author, inline=True)
        embed.add_field(name="User ID", value=ctx.message.author.id, inline=True)
        channel = self.bot.get_channel(int(channel_ids['modlog']))
        await channel.send(f"<@&{role_ids['moderator']}> <@&{role_ids['trial_mod']}>", embed=embed)
        await ctx.send("The moderators have been alerted.")

    @commands.command()
    async def suggest(self, ctx, *, suggestion=None):
        if not suggestion:
            await ctx.send("Please provide a suggestion.")
            return
        embed = discord.Embed(description=f"**Suggestion:** {suggestion}", color=discord.Color.lighter_grey())
        embed.set_author(name=ctx.author, icon_url=ctx.author.display_avatar)
        embed.add_field(name="Status", value="Pending")
        channel = self.bot.get_channel(int(channel_ids['suggestions_list']))
        await channel.send(embed=embed)
        await ctx.message.add_reaction("✅")

    @commands.command()
    async def remindme(self, ctx, time=None, *, reminder=None):
        if not time:
            await ctx.send("Please specify the time you would like to be reminded in.")
            return
        if not reminder:
            reminder = "No description provided."
        gran = 0
        for char in time:
            gran += char.isalpha()
        if gran > 4:
            await ctx.send("The time you mentioned for me to remind you in is not in the correct format.\nIt should look something like `1d2h3m4s` (1 day, 2 hours, 3 minutes, and 4 seconds).")
            return
        cooltime = [int(a[ :-1]) if a else b for a,b in zip(re.search('(\d+d)?(\d+h)?(\d+m)?(\d+s)?', time).groups(), [0, 0, 0, 0])]
        seconds = cooltime[0]*86400 + cooltime[1]*3600 + cooltime[2]*60 + cooltime[3]
        fancytime = await seconds_to_fancytime(seconds, gran)

        collection = mongodb['reminders']
        collection.insert_one({"_id": str(ctx.message.id), "text": reminder, "time": fancytime, "user": str(ctx.message.author.id), "end": str(int(datetime.now().strftime("%s")) + seconds)})
        await ctx.send(f"I will remind you in {fancytime}.")
        await sleep(seconds)
        collection.delete_one({"_id": str(ctx.message.id)})

        embed = discord.Embed(title=f"Reminder from {fancytime} ago:", description=f"{reminder}\n\n[link to original message]({ctx.message.jump_url})", color=0x00a0a0)
        if ctx.message.author.dm_channel is None:
            dm = await ctx.message.author.create_dm()
        else:
            dm = ctx.message.author.dm_channel
        await dm.send(embed=embed)

    @commands.command()
    async def shorten(self, ctx, link=None):
        if not link:
            await ctx.send("Please specify a link to shorten.")
            return

        if re.search(r"https?:\/\/(www\.)?amazon\.[^\/]*", link) and re.search(r"\/dp\/B0[\dA-Z]{8}\/", link):
            amazon = re.search(r"amazon\.[^\/]*", link).group()
            dp = re.search(r"\/dp\/B0[0-9A-Z]{8}\/", link).group()
            await ctx.send("https://" + amazon + dp)

        elif re.search(r"https?:\/\/(www\.)?youtube\.com", link) and re.search(r"(\?|&)v=[\d\w-]{11}", link):
            v = re.search(r"(\?|&)v=[\d\w-]{11}", link).group()[3:]

            if re.search(r"(\?|&)t=\d+", link):
                t = "&" + re.search(r"(\?|&)t=\d+", link).group()[1:]
            else:
                t = ""

            await ctx.send("https://youtu.be/" + v + t)

async def setup(bot):
    await bot.add_cog(misc(bot))
