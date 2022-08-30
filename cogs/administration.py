from discord.ext import commands
import discord
import yaml
import re
#from emoji import emoji_count
from main import get_database
mongodb = get_database()

class administration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    with open('config.yaml', 'r') as config_file:
        config = yaml.load(config_file, Loader=yaml.BaseLoader)
    global channel_ids
    channel_ids = config['channel_ids']

    @commands.command(name="add-swear")
    @commands.has_permissions(administrator=True)
    async def add_swear(self, ctx, arg=None):
        if not arg:
            await ctx.send("Please provide the name of the new swear.")
            return

        collection = mongodb['swears']
        for swear in collection.find():
            if swear['swear'] == arg:
                await ctx.send(f"The swear `{arg}` already exists.")
                return
        collection.insert_one({"swear": arg})
        await ctx.send(f"Swear `{arg}` successfully added.")
        await ctx.send("reload swears")

    @commands.command(name="remove-swear")
    @commands.has_permissions(administrator=True)
    async def remove_swear(self, ctx, arg=None):
        if not arg:
            await ctx.send("Please provide the name of the swear to remove.")
            return

        collection = mongodb['swears']
        found = False
        for swear in collection.find():
            if swear['swear'] == arg:
                found = True
                break
        if not found:
            await ctx.send(f"The swear `{arg}` was not found.")
            return
        collection.delete_one({"swear": arg})
        await ctx.send(f"Swear `{arg}` successfully removed.")
        await ctx.send("reload swears")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def swearlist(self, ctx):
        collection = mongodb['swears']
        description = ""
        for swear in collection.find():
            description += f"\n{swear['swear']}"
        embed = discord.Embed(title="Swearlist", description=description, color=0x00a0a0)
        await ctx.send(embed=embed)

#    @commands.command(name="add-reaction-role")
#    async def add_reaction_role(self, ctx, role=None, reaction=None, *, message=None):
#        if not role:
#            await ctx.send("Please provide the ID of the role to add.")
#            return
#        if not reaction:
#            await ctx.send("Please provide the emoji to use as a reaction.")
#            return
#        if not message:
#            await ctx.send("Please provide the contents of the reaction role message.")
#            return
#
#        if not ctx.message.guild.get_role(int(role)):
#            await ctx.send("Not a valid role.")
#            return
#
#        if emoji_count(reaction) != 1:
#            await ctx.send("Not a valid emoji.")
#            return
#
#        channel = self.bot.get_channel(int(channel_ids['reaction_roles']))
#        message = await channel.send(message)
#        await message.add_reaction(reaction)
#
#        collection = mongodb['reaction-roles']
#        collection.insert_one({"_id": str(message.id), "role": role, "emoji": reaction})
#
#        await ctx.message.add_reaction("✅")
#        await ctx.send("reload reaction roles")

    @commands.command()
    async def softban(self, ctx, user=None):
        guild = ctx.message.guild
        if not user:
            await ctx.send("Please mention a user to softban.")
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

        await guild.ban(discord.Object(id=id), delete_message_days=7, reason="softban")
        await ctx.message.add_reaction("✅")
        await guild.unban(discord.Object(id=id), reason="softban")

async def setup(bot):
    await bot.add_cog(administration(bot))
