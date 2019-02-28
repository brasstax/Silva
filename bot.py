#!/usr/bin/env python
from configparser import ConfigParser
import logging
from discord.ext import commands
import discord

logging.basicConfig(level=logging.INFO)

config = ConfigParser()
config.read('config.ini')

with open(config['default']['discord_token']) as fp:
    TOKEN = fp.read().strip()
COMMAND_PREFIX = config['default']['command_prefix']

bot = commands.Bot(
    command_prefix=COMMAND_PREFIX,
    description="The best sniper in Phantagarde...or possibly all the gardes.")


@bot.event
async def on_ready():
    logging.info(f'Logged in as {bot.user.name} ({bot.user.id})')
    logging.info('------')
    activity = discord.Game(name=f'{COMMAND_PREFIX}help for help')
    await bot.change_presence(status=discord.Status.online, activity=activity)

bot.run(TOKEN)
