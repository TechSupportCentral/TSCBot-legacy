from discord.ext import commands
import discord
import yaml
from main import get_database
mongodb = get_database()

class custom_commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    global collection
    collection = mongodb['custom-commands']
    _custom_commands = {}

    with open('config.yaml', 'r') as config_file:
        config = yaml.load(config_file, Loader=yaml.BaseLoader)
    global channel_ids
    channel_ids = config['channel_ids']

    @commands.Cog.listener()
    async def on_ready(self):
        async def add_command(self, name, value):
            self._custom_commands[name] = value

            @commands.command(name=name)
            async def cmd(self, ctx):
                await ctx.send(value)

            cmd.cog = self
            self.__cog_commands__ += (cmd,)
            self.bot.add_command(cmd)

        for command in collection.find():
            await add_command(self, command['name'], command['value'])

    @commands.command(name="add-custom")
    @commands.has_permissions(administrator=True)
    async def add_custom(self, ctx, name=None, *, value=None):
        async def add_command(self, name, value):
            self._custom_commands[name] = value

            @commands.command(name=name)
            async def cmd(self, ctx):
                await ctx.send(value)

            cmd.cog = self
            self.__cog_commands__ += (cmd,)
            self.bot.add_command(cmd)

#            @discord.app_commands.command(name=name)
#            async def appcmd(self, interaction: discord.Interaction):
#                await interaction.response.send_message(value)
#
#            self.bot.tree.add_command(appcmd)
#            self.bot.tree.sync()

        if not name:
            await ctx.send("Please provide a name for the new custom command.")
            return
        if not value:
            await ctx.send("Please provide the response for when the command is run.")
            return

        if self._custom_commands[name] or ctx.bot.get_command(name):
            await ctx.send(f"The command `{name}` already exists.")
            return

        collection.insert_one({"name": name, "value": value})
        await add_command(self, name, value)

        embed = discord.Embed(title="Custom Command Added", color=discord.Color.green())
        embed.set_thumbnail(url=ctx.message.author.display_avatar)
        embed.add_field(name="Added by", value=ctx.message.author, inline=False)
        embed.add_field(name="Command Name", value=name, inline=False)
        embed.add_field(name="Command Response", value=value, inline=False)
        channel = ctx.bot.get_channel(int(channel_ids['staff_news']))
        await channel.send(embed=embed)
        await ctx.message.add_reaction("✅")
        await ctx.send(f"Please give the command a description with `!add-custom-description {name} description here`.")

    @commands.command(name="remove-custom")
    @commands.has_permissions(administrator=True)
    async def remove_custom(self, ctx, arg=None):
        if not arg:
            await ctx.send("Please provide the name of the custom command to remove.")
            return

        if not self._custom_commands[arg]:
            if ctx.bot.get_command(arg):
                await ctx.send("You cannot remove a built-in command.")
                return
            else:
                await ctx.send(f"The command `{arg}` does not exist.")
                return
        else:
            value = self._custom_commands[arg]

        collection.delete_one({"name": arg})
        del self._custom_commands[arg]
        ctx.bot.remove_command(arg)

        embed = discord.Embed(title="Custom Command Removed", color=discord.Color.red())
        embed.set_thumbnail(url=ctx.message.author.display_avatar)
        embed.add_field(name="Removed by", value=ctx.message.author, inline=False)
        embed.add_field(name="Command Name", value=arg, inline=False)
        embed.add_field(name="Command Response", value=value, inline=False)
        channel = ctx.bot.get_channel(int(channel_ids['staff_news']))
        await channel.send(embed=embed)
        await ctx.message.add_reaction("✅")

    @commands.command(name="add-custom-description")
    @commands.has_permissions(administrator=True)
    async def add_desc(self, ctx, name=None, *, desc=None):
        if not name:
            await ctx.send("Please provide the name of the custom command to describe.")
            return
        elif not desc:
            await ctx.send(f"Please provide the description for the command `{name}`.")
            return

        if not self._custom_commands[name]:
            if ctx.bot.get_command(name):
                await ctx.send("You cannot add a description to a built-in command.")
                return
            else:
                await ctx.send(f"The command `{name}` does not exist.")
                return

        collection.update_one({"name": name}, {"$set": {"description": desc}})
#        cmd = self.bot.tree.get_command(name)
#        await cmd.edit(description=desc)
#        self.bot.tree.sync()
        await ctx.message.add_reaction("✅")

async def setup(bot):
    await bot.add_cog(custom_commands(bot))
