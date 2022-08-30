import discord
from discord.ext import commands
from asyncio import run
import logging
import os
import yaml
import pymongo

with open('config.yaml', 'r') as config_file:
    config = yaml.load(config_file, Loader=yaml.BaseLoader)

def get_database():
    client = pymongo.MongoClient(config['mongo_uri'])
    db = client[config['mongo_db']]
    return db

if __name__ == "__main__":
    mongodb = get_database()

    intents = discord.Intents.default()
    intents.members = True
    intents.message_content = True
    bot = commands.Bot(command_prefix=config['prefix'], intents=intents, help_command=None)
    discord.utils.setup_logging(level=logging.INFO)

    @bot.event
    async def on_ready():
        print('Logged in as ' + bot.user.name)

    async def run_bot():
        async with bot:
            for filename in os.listdir('cogs'):
                if filename.endswith('.py'):
                    await bot.load_extension(f'cogs.{filename[:-3]}')
                    print(f'Cog {filename[:-3]} loaded')

            await bot.start(config['token'])
    run(run_bot())
