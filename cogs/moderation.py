from discord.ext import commands
import discord
import yaml
from asyncio import sleep
from time import time
from calendar import timegm
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

class moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    with open('config.yaml', 'r') as config_file:
        config = yaml.load(config_file, Loader=yaml.BaseLoader)
    global role_ids
    role_ids = config['role_ids']
    global channel_ids
    channel_ids = config['channel_ids']

    @commands.command()
    async def purge(self, ctx, num=None, *, reason=None):
        guild = ctx.message.guild
        mod_role = guild.get_role(int(role_ids['moderator']))
        if not mod_role in ctx.message.author.roles:
            await ctx.send("You do not have permission to run this command.")
            return

        if not num:
            await ctx.send("Please mention a number of messages to purge.")
            return
        elif num.isdigit():
            num = int(num)
        else:
            await ctx.send("Not a valid number of messages")
            return

        if num > 100:
            await ctx.send("You can only delete 100 or fewer messages at once.")
            return

        if not reason:
            reason = "No reason provided."

        await ctx.channel.purge(limit=num + 1)
        embed=discord.Embed(title=f"{num} Messages Deleted", color=discord.Color.red())
        embed.set_thumbnail(url=ctx.message.author.display_avatar)
        embed.add_field(name="Deleted by", value=ctx.message.author.global_name, inline=True)
        embed.add_field(name="In channel", value=ctx.message.channel.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        channel = self.bot.get_channel(int(channel_ids['modlog']))
        await channel.send(embed=embed)

    @commands.command()
    async def userinfo(self, ctx, arg=None):
        guild = ctx.message.guild
        mod_role = guild.get_role(int(role_ids['moderator']))
        trial_mod_role = guild.get_role(int(role_ids['trial_mod']))
        if mod_role not in ctx.message.author.roles and trial_mod_role not in ctx.message.author.roles:
            await ctx.send("You do not have permission to run this command.")
            return

        if not arg:
            id = ctx.message.author.id
        elif re.search(r"<@!?\d+>", arg):
            id = int(re.search(r"\d+", arg).group())
        elif arg.isdigit():
            id = int(arg)
        else:
            await ctx.send("Users have to be in the form of an ID or a mention.")
            return

        if guild.get_member(id) is None:
            await ctx.send("User is not in the server.")
            return

        member = guild.get_member(id)
        if member.discriminator == "0":
            embed = discord.Embed(title=member.name, color=0x00a0a0)
        else:
            embed = discord.Embed(title=member, color=0x00a0a0)
        embed.set_thumbnail(url=member.display_avatar)
        embed.add_field(name="User ID", value=id, inline=False)
        if member.name != member.display_name:
            embed.add_field(name="Nickname", value=member.display_name, inline=False)

        created = timegm(member.created_at.timetuple())
        joined = timegm(member.joined_at.timetuple())
        created_delta = round(time() - created)
        joined_delta = round(time() - joined)
        if created_delta < 604800:
            created_fancy = await seconds_to_fancytime(created_delta, 2)
        else:
            created_fancy = await seconds_to_fancytime(created_delta, 1)
        if joined_delta < 604800:
            joined_fancy = await seconds_to_fancytime(joined_delta, 2)
        else:
            joined_fancy = await seconds_to_fancytime(joined_delta, 1)
        embed.add_field(name="Account Created:", value=f"<t:{created}> ({created_fancy} ago)", inline=True)
        embed.add_field(name="Joined Server:", value=f"<t:{joined}> ({joined_fancy} ago)", inline=True)
        if joined - created < 604800:
            embed.add_field(name="Difference between creation and join:", value=await seconds_to_fancytime(joined - created, 2), inline=False)

        mentions = []
        for role in member.roles:
            if role.name != "@everyone":
                mentions.append(role.mention)
        roles = ", ".join(mentions)
        embed.add_field(name="Roles", value=roles, inline=False)
        await ctx.send(embed=embed)

    @commands.command()
    async def warnings(self, ctx, arg=None):
        guild = ctx.message.guild
        mod_role = guild.get_role(int(role_ids['moderator']))
        trial_mod_role = guild.get_role(int(role_ids['trial_mod']))
        if mod_role not in ctx.message.author.roles and trial_mod_role not in ctx.message.author.roles:
            await ctx.send("You do not have permission to run this command.")
            return

        if not arg:
            await ctx.send("Please mention a user to check the warnings of.")
            return
        elif re.search(r"<@!?\d+>", arg):
            id = int(re.search(r"\d+", arg).group())
        elif arg.isdigit():
            id = int(arg)
        else:
            await ctx.send("Users have to be in the form of an ID or a mention.")
            return

        if guild.get_member(id) is None:
            description = ""
        else:
            description = f"**User:** {guild.get_member(id).name}\n"

        collection = mongodb['moderation']
        found = False
        number = 0
        for warning in collection.find():
            if warning['user'] == str(id):
                found = True
                number += 1
                description = description + f"\n`{number}`:\n**Type:** {warning['type']}\n**Reason:** {warning['reason']}\n**Moderator:** {guild.get_member(int(warning['moderator']))}\n**Message ID:** {warning['_id']}\n"
        if not found:
            await ctx.send("This user has no warnings.")
            return
        embed = discord.Embed(title="Warnings", description=description, color=0x00a0a0)
        await ctx.send(embed=embed)

    @commands.command()
    async def warn(self, ctx, user=None, *, reason=None):
        guild = ctx.message.guild
        mod_role = guild.get_role(int(role_ids['moderator']))
        trial_mod_role = guild.get_role(int(role_ids['trial_mod']))
        if mod_role not in ctx.message.author.roles and trial_mod_role not in ctx.message.author.roles:
            await ctx.send("You do not have permission to run this command.")
            return

        if not user:
            await ctx.send("Please mention a user to warn.")
            return
        elif re.search(r"<@!?\d+>", user):
            id = int(re.search(r"\d+", user).group())
        elif user.isdigit():
            id = int(user)
        else:
            await ctx.send("Users have to be in the form of an ID or a mention.")
            return

        if guild.get_member(id) is None:
            await ctx.send("User is not in the server.")
            return
        member = guild.get_member(id)

        if member.top_role.position > ctx.message.author.top_role.position:
            await ctx.send(f"{member.global_name} is higher than you in the role hierarchy, cannot warn.")
            return
        if member.bot:
            await ctx.send("You cannot warn bots.")
            return

        if not reason:
            reason = "No reason provided."

        channel = self.bot.get_channel(int(channel_ids['modlog']))
        message = await channel.send(".")
        embed = discord.Embed(title="Warning", description=f"Use `!unwarn {message.id} <reason>` to remove this warning. Note: This is not the user's ID, rather the ID of this message.", color=discord.Color.red())
        embed.set_thumbnail(url=member.display_avatar)
        embed.add_field(name="User warned", value=member.name, inline=True)
        embed.add_field(name="User ID", value=str(id), inline=True)
        embed.add_field(name="Moderator", value=ctx.message.author.global_name, inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        await message.edit(content="", embed=embed)

        collection = mongodb['moderation']
        collection.insert_one({"_id": str(message.id), "type": "warn", "user": str(id), "moderator": str(ctx.message.author.id), "reason": reason})

        dmbed = discord.Embed(title="You have been warned.", description=f"**Reason:** {reason}", color=discord.Color.red())
        try:
            await member.send(embed=dmbed)
        except:
            await ctx.send("The member was warned successfully, but a DM was unable to be sent.")
            return
        await ctx.message.add_reaction("✅")

    @commands.command()
    async def unwarn(self, ctx, id=None, *, reason=None):
        guild = ctx.message.guild
        mod_role = guild.get_role(int(role_ids['moderator']))
        trial_mod_role = guild.get_role(int(role_ids['trial_mod']))
        if mod_role not in ctx.message.author.roles and trial_mod_role not in ctx.message.author.roles:
            await ctx.send("You do not have permission to run this command.")
            return

        if not id:
            await ctx.send("Please mention the ID of a warn message to remove.")
            return
        elif not id.isdigit():
            await ctx.send("Warns have to be in the form of a Message ID.")
            return

        collection = mongodb['moderation']
        found = False
        for warn in collection.find():
            if warn['_id'] == id:
                found = True
                user = warn['user']
                og_reason = warn['reason']
        if not found:
            await ctx.send("The warn was not found.")
            return
        collection.delete_one({"_id": id})

        if not reason:
            reason = "No reason provided."

        member = guild.get_member(int(user))
        embed = discord.Embed(title="Warning Removed", color=discord.Color.green())
        embed.set_thumbnail(url=member.display_avatar)
        embed.add_field(name="User unwarned", value=member.name, inline=True)
        embed.add_field(name="User ID", value=user, inline=True)
        embed.add_field(name="Moderator", value=ctx.message.author.global_name, inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        channel = self.bot.get_channel(int(channel_ids['modlog']))
        await channel.send(embed=embed)

        dmbed = discord.Embed(title="Your warning has been removed.", color=discord.Color.green())
        dmbed.add_field(name="Original reason for warn", value=og_reason, inline=False)
        dmbed.add_field(name="Reason for removal", value=reason, inline=False)
        try:
            await member.send(embed=dmbed)
        except:
            await ctx.send("The warn was removed successfully, but a DM was unable to be sent to the original warned user.")
            return
        await ctx.message.add_reaction("✅")

    @commands.command()
    async def reason(self, ctx, id=None, *, reason=None):
        guild = ctx.message.guild
        mod_role = guild.get_role(int(role_ids['moderator']))
        trial_mod_role = guild.get_role(int(role_ids['trial_mod']))
        if mod_role not in ctx.message.author.roles and trial_mod_role not in ctx.message.author.roles:
            await ctx.send("You do not have permission to run this command.")
            return

        if not id:
            await ctx.send("Please mention the message ID of a warning to update the reason of.")
            return
        elif not id.isdigit():
            await ctx.send("Warnings have to be in the form of a Message ID.")
            return

        collection = mongodb['moderation']
        found = False
        for warn in collection.find():
            if warn['_id'] == id:
                found = True
                user = warn['user']
                moderator = warn['moderator']
                og_reason = warn['reason']
        if not found:
            await ctx.send("The warning was not found.")
            return
        if ctx.message.author.id != int(moderator) and guild.get_role(int(role_ids['owner'])) not in ctx.message.author.roles:
            await ctx.send("This is not your warning to change.")
            return

        if not reason:
            reason = "No reason provided."

        collection.update_one({"_id": id}, {"$set": {"reason": reason}})
        channel = self.bot.get_channel(int(channel_ids['modlog']))
        message = await channel.fetch_message(int(id))
        og_embed = message.embeds[0]
        embed = discord.Embed(title=og_embed.title, description=og_embed.description, color=og_embed.color)
        embed.set_thumbnail(url=og_embed.thumbnail.url)
        for field in og_embed.fields:
            if field.name == "Reason":
                embed.add_field(name="Reason", value=reason, inline=field.inline)
            else:
                embed.add_field(name=field.name, value=field.value, inline=field.inline)
        embed.set_footer(text=og_embed.footer.text)
        await message.edit(embed=embed)

        member = guild.get_member(int(user))
        dmbed = discord.Embed(title="Your warning has been updated.", color=0x00a0a0)
        dmbed.add_field(name="Original reason", value=og_reason, inline=False)
        dmbed.add_field(name="New reason", value=reason, inline=False)
        try:
            await member.send(embed=dmbed)
        except:
            await ctx.send("The reason was updated successfully, but a DM was unable to be sent to the warned user.")
            return
        await ctx.message.add_reaction("✅")

    @commands.command()
    async def kick(self, ctx, user=None, *, reason=None):
        guild = ctx.message.guild
        mod_role = guild.get_role(int(role_ids['moderator']))
        owner_role = guild.get_role(int(role_ids['owner']))
        if mod_role not in ctx.message.author.roles:
            await ctx.send("You do not have permission to run this command.")
            return

        if not user:
            await ctx.send("Please mention a user to kick.")
            return
        elif re.search(r"<@!?\d+>", user):
            id = int(re.search(r"\d+", user).group())
        elif user.isdigit():
            id = int(user)
        else:
            await ctx.send("Users have to be in the form of an ID or a mention.")
            return

        if guild.get_member(id) is None:
            await ctx.send("User is not in the server.")
            return
        member = guild.get_member(id)

        if member.top_role.position >= ctx.message.author.top_role.position:
            await ctx.send(f"{member.global_name} is higher than or equal to you in the role hierarchy, cannot kick.")
            return
        if member.bot and owner_role not in ctx.message.author.roles:
            await ctx.send("You do not have permission to kick bots.")
            return

        if not reason:
            reason = "No reason provided."

        embed = discord.Embed(title="Kick", color=discord.Color.red())
        embed.set_thumbnail(url=member.display_avatar)
        embed.add_field(name="User kicked", value=member.name, inline=True)
        embed.add_field(name="User ID", value=str(id), inline=True)
        embed.add_field(name="Moderator", value=ctx.message.author.global_name, inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        channel = self.bot.get_channel(int(channel_ids['modlog']))
        message = await channel.send(embed=embed)

        collection = mongodb['moderation']
        collection.insert_one({"_id": str(message.id), "type": "kick", "user": str(id), "moderator": str(ctx.message.author.id), "reason": reason})

        dmbed = discord.Embed(title="You have been kicked.", description=f"**Reason:** {reason}", color=discord.Color.red())
        dm_failed = False
        try:
            await member.send(embed=dmbed)
        except:
            dm_failed = True

        if dm_failed:
            await ctx.send("The member was kicked successfully, but a DM was unable to be sent.")
        else:
            await ctx.message.add_reaction("✅")
        await guild.kick(member, reason=reason)

    @commands.command()
    async def ban(self, ctx, user=None, *, reason=None):
        guild = ctx.message.guild
        mod_role = guild.get_role(int(role_ids['moderator']))
        owner_role = guild.get_role(int(role_ids['owner']))
        if mod_role not in ctx.message.author.roles:
            await ctx.send("You do not have permission to run this command.")
            return

        if not user:
            await ctx.send("Please mention a user to ban.")
            return
        elif re.search(r"<@!?\d+>", user):
            id = int(re.search(r"\d+", user).group())
        elif user.isdigit():
            id = int(user)
        else:
            await ctx.send("Users have to be in the form of an ID or a mention.")
            return

        if guild.get_member(id) is None:
            member = await self.bot.fetch_user(id)
        else:
            member = guild.get_member(id)

        if not member:
            await ctx.send("Not a valid discord user.")
            return

        if guild.get_member(id) is not None:
            if member.top_role.position >= ctx.message.author.top_role.position:
                await ctx.send(f"{member.global_name} is higher than or equal to you in the role hierarchy, cannot ban.")
                return
            if member.bot and owner_role not in ctx.message.author.roles:
                await ctx.send("You do not have permission to ban bots.")
                return

        if not reason:
            reason = "No reason provided."

        embed = discord.Embed(title="Ban", color=discord.Color.red())
        embed.set_thumbnail(url=member.display_avatar)
        embed.add_field(name="User banned", value=member.name, inline=True)
        embed.add_field(name="User ID", value=str(id), inline=True)
        embed.add_field(name="Moderator", value=ctx.message.author.global_name, inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        channel = self.bot.get_channel(int(channel_ids['modlog']))
        message = await channel.send(embed=embed)

        collection = mongodb['moderation']
        collection.insert_one({"_id": str(message.id), "type": "ban", "user": str(id), "moderator": str(ctx.message.author.id), "reason": reason})

        dmbed = discord.Embed(title="You have been banned.", description=f"**Reason:** {reason}", color=discord.Color.red())
        dmbed.set_footer(text="You can appeal your ban at https://www.techsupportcentral.cf/appeal.php")
        try:
            await member.send(embed=dmbed)
        except:
            pass

        await guild.ban(discord.Object(id=id), delete_message_days=0, reason=reason)
        await ctx.message.add_reaction("✅")

    @commands.command()
    async def unban(self, ctx, user=None, *, reason=None):
        guild = ctx.message.guild
        mod_role = guild.get_role(int(role_ids['moderator']))
        if mod_role not in ctx.message.author.roles:
            await ctx.send("You do not have permission to run this command.")
            return

        if not user:
            await ctx.send("Please mention a user to unban.")
            return
        elif re.search(r"<@!?\d+>", user):
            id = int(re.search(r"\d+", user).group())
        elif user.isdigit():
            id = int(user)
        else:
            await ctx.send("Users have to be in the form of an ID or a mention.")
            return

        member = await self.bot.fetch_user(id)
        if not member:
            await ctx.send("Not a valid discord user.")
            return

        if not reason:
            reason = "No reason provided."

        embed = discord.Embed(title="Ban Removed", color=discord.Color.green())
        embed.set_thumbnail(url=member.display_avatar)
        embed.add_field(name="User unbanned", value=member.name, inline=True)
        embed.add_field(name="User ID", value=str(id), inline=True)
        embed.add_field(name="Moderator", value=ctx.message.author.global_name, inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        channel = self.bot.get_channel(int(channel_ids['modlog']))
        message = await channel.send(embed=embed)

        mod_collection = mongodb['moderation']
        mod_collection.insert_one({"_id": str(message.id), "type": "unban", "user": str(id), "moderator": str(ctx.message.author.id), "reason": reason})
        app_collection = mongodb['applications']
        app_collection.update_one({"id": str(id), "type": "appeal"}, {"$set": {"accepted": "yes"}})

        await guild.unban(discord.Object(id=id), reason=reason)
        await ctx.message.add_reaction("✅")

    @commands.command()
    async def mute(self, ctx, user=None, mutetime=None, *, reason=None):
        guild = ctx.message.guild
        mod_role = guild.get_role(int(role_ids['moderator']))
        trial_mod_role = guild.get_role(int(role_ids['trial_mod']))
        if mod_role not in ctx.message.author.roles and trial_mod_role not in ctx.message.author.roles:
            await ctx.send("You do not have permission to run this command.")
            return

        if not user:
            await ctx.send("Please mention a user to mute.")
            return
        elif re.search(r"<@!?\d+>", user):
            id = int(re.search(r"\d+", user).group())
        elif user.isdigit():
            id = int(user)
        else:
            await ctx.send("Users have to be in the form of an ID or a mention.")
            return

        if guild.get_member(id) is None:
            await ctx.send("User is not in the server.")
            return
        member = guild.get_member(id)

        if member.top_role.position >= ctx.message.author.top_role.position:
            await ctx.send(f"{member.global_name} is higher than or equal to you in the role hierarchy, cannot mute.")
            return
        if member.bot:
            await ctx.send("You cannot mute bots.")
            return

        if not mutetime:
            mutetime = "12h"
        gran = 0
        for char in mutetime:
            gran += char.isalpha()
        if gran > 4:
            await ctx.send("Please mention the time to mute in a format like `1d2h3m4s` (1 day, 2 hours, 3 minutes, 4 seconds).")
            return
        cooltime = [int(a[ :-1]) if a else b for a,b in zip(re.search('(\d+d)?(\d+h)?(\d+m)?(\d+s)?', mutetime).groups(), [0, 0, 0, 0])]
        seconds = cooltime[0]*86400 + cooltime[1]*3600 + cooltime[2]*60 + cooltime[3]
        fancytime = await seconds_to_fancytime(seconds, gran)

        if not reason:
            reason = "No reason provided."

        muted_role = guild.get_role(int(role_ids['muted']))
        if muted_role in member.roles:
            await ctx.send(f"{member.name} is already muted.")
            return

        embed = discord.Embed(title="Mute", color=discord.Color.red())
        embed.set_thumbnail(url=member.display_avatar)
        embed.add_field(name="User muted", value=member.name, inline=True)
        embed.add_field(name="User ID", value=str(id), inline=True)
        embed.add_field(name="Moderator", value=ctx.message.author.global_name, inline=False)
        embed.add_field(name="Time muted", value=fancytime, inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        channel = self.bot.get_channel(int(channel_ids['modlog']))
        message = await channel.send(embed=embed)

        collection = mongodb['moderation']
        collection.insert_one({"_id": str(message.id), "type": "mute", "user": str(id), "moderator": str(ctx.message.author.id), "start": str(round(time())), "time": str(seconds), "reason": reason})

        dmbed = discord.Embed(title=f"You have been muted for {fancytime}.", description=f"**Reason:** {reason}", color=discord.Color.red())
        dm_failed = False
        try:
            await member.send(embed=dmbed)
        except:
            dm_failed = True

        if dm_failed:
            await ctx.send(f"{member.name} was muted for {fancytime}. A DM was unable to be sent.")
        else:
            await ctx.send(f"{member.name} was muted for {fancytime}.")
            await ctx.message.add_reaction("✅")

        await member.add_roles(muted_role)
        await sleep(seconds)
        if not muted_role in member.roles:
            return

        dmbed2 = discord.Embed(title="You have been automatically unmuted.", color=discord.Color.green())
        dm2_failed = False
        try:
            await member.send(embed=dmbed2)
        except:
            dm2_failed = True

        embed2 = discord.Embed(title="Mute Removed", color=discord.Color.green())
        embed2.set_thumbnail(url=member.display_avatar)
        embed2.add_field(name="User unmuted", value=member.name, inline=True)
        embed2.add_field(name="User ID", value=str(id), inline=True)
        embed2.add_field(name="Reason", value="Automatic unmute", inline=False)
        if dm2_failed:
            embed2.set_footer(text="was unable to DM user")
        await channel.send(embed=embed2)
        await member.remove_roles(muted_role)

    @commands.command()
    async def unmute(self, ctx, user=None, *, reason=None):
        guild = ctx.message.guild
        mod_role = guild.get_role(int(role_ids['moderator']))
        trial_mod_role = guild.get_role(int(role_ids['trial_mod']))
        if mod_role not in ctx.message.author.roles and trial_mod_role not in ctx.message.author.roles:
            await ctx.send("You do not have permission to run this command.")
            return

        if not user:
            await ctx.send("Please mention a user to unmute.")
            return
        elif re.search(r"<@!?\d+>", user):
            id = int(re.search(r"\d+", user).group())
        elif user.isdigit():
            id = int(user)
        else:
            await ctx.send("Users have to be in the form of an ID or a mention.")
            return

        if guild.get_member(id) is None:
            await ctx.send("User is not in the server.")
            return
        member = guild.get_member(id)

        if not reason:
            reason = "No reason provided."

        muted_role = guild.get_role(int(role_ids['muted']))
        if not muted_role in member.roles:
            await ctx.send(f"{member.name} is not muted.")
            return

        embed = discord.Embed(title="Mute Removed", color=discord.Color.green())
        embed.set_thumbnail(url=member.display_avatar)
        embed.add_field(name="User unmuted", value=member.name, inline=True)
        embed.add_field(name="User ID", value=str(id), inline=True)
        embed.add_field(name="Moderator", value=ctx.message.author.global_name, inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        channel = self.bot.get_channel(int(channel_ids['modlog']))
        message = await channel.send(embed=embed)

        collection = mongodb['moderation']
        collection.insert_one({"_id": str(message.id), "type": "unmute", "user": str(id), "moderator": str(ctx.message.author.id), "reason": reason})

        dmbed = discord.Embed(title="You have been unmuted.", description=f"**Reason:** {reason}", color=discord.Color.green())
        dm_failed = False
        try:
            await member.send(embed=dmbed)
        except:
            dm_failed = True

        await member.remove_roles(muted_role)
        if dm_failed:
            await ctx.send("The member was unmuted successfully, but a DM was unable to be sent.")
        else:
            await ctx.message.add_reaction("✅")

async def setup(bot):
    await bot.add_cog(moderation(bot))
