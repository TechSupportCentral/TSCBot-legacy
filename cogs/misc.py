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

    @commands.command(name='commands')
    async def _commands(self, ctx, arg=None):
        with open('commands.yaml', 'r') as commands_file:
            commands = yaml.load(commands_file, Loader=yaml.BaseLoader)

        if not arg:
            embed = discord.Embed(title="Command List", description="Commands come in categories. Here is a list of categories, run `!commands <category>` to see the commands in a certain category.", color=0x00a0a0)
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)
            for category in commands:
                if not '_desc' in category:
                    embed.add_field(name=category + ':', value=commands[category + '_desc'], inline=True)
            await ctx.send(embed=embed)
        elif arg in commands:
            guild = ctx.message.guild
            mod_role = guild.get_role(int(role_ids['moderator']))
            trial_role = guild.get_role(int(role_ids['trial_mod']))
            owner_role = guild.get_role(int(role_ids['owner']))
            if arg == "moderation" and not mod_role in ctx.author.roles and not trial_role in ctx.author.roles:
                await ctx.send("The `moderation` category can only be viewed by moderators.")
                return
            elif arg == "administration" and not owner_role in ctx.author.roles:
                await ctx.send("The `administration` category can only be viewed by admins.")
                return
            embed = discord.Embed(title="Command List", description=f"Commands in the {arg} category:", color=0x00a0a0)
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)
            for command in commands[arg]:
                embed.add_field(name=command + ':', value=commands[arg][command], inline=False)
            await ctx.send(embed=embed)
        else:
            await ctx.send('Please send a valid category')

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
        collection.insert_one({"_id": str(ctx.message.id), "text": reminder, "time": fancytime, "user": str(ctx.message.author.id), "end": str(round(datetime.now().timestamp() + seconds))})
        await ctx.send(f"I will remind you in {fancytime}.")
        await sleep(seconds)
        collection.delete_one({"_id": str(ctx.message.id)})

        embed = discord.Embed(title=f"Reminder from {fancytime} ago:", description=f"{reminder}\n\n[link to original message]({ctx.message.jump_url})", color=0x00a0a0)
        if ctx.message.author.dm_channel is None:
            dm = await ctx.message.author.create_dm()
        else:
            dm = ctx.message.author.dm_channel
        await dm.send(embed=embed)

async def setup(bot):
    await bot.add_cog(misc(bot))
