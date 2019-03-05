#!/usr/bin/env python
from configparser import ConfigParser
import logging
from discord.ext import commands
from silva import bot_commands
import discord
import sqlite3

logging.basicConfig(level=logging.INFO)

config = ConfigParser()
config.read('config.ini')

with open(config['default']['discord_token']) as fp:
    TOKEN = fp.read().strip()
COMMAND_PREFIX = config['default']['command_prefix']

bot = commands.Bot(
    command_prefix=COMMAND_PREFIX,
    description="The best sniper in Phantagarde...or possibly all the gardes.",
    case_insensitive=True)

bot.add_cog(bot_commands.SilvaCmds(bot))


@bot.event
async def on_connect():
    bot.conn = sqlite3.connect('aliases.sqlite3')
    bot.conn.row_factory = sqlite3.Row
    bot.cursor = bot.conn.cursor()
    cmd: str = (
        "CREATE TABLE IF NOT EXISTS aliases"
        " (id integer primary key autoincrement,"
        " word text, alias text, is_proper_noun int DEFAULT 1)"
    )
    bot.cursor.execute(cmd)
    cmd: str = (
        "CREATE UNIQUE INDEX IF NOT EXISTS"
        " idx_positions_id ON aliases(id)"
    )
    bot.cursor.execute(cmd)
    bot.conn.commit()


@bot.event
async def on_ready():
    logging.info(f'Logged in as {bot.user.name} ({bot.user.id})')
    logging.info('------')
    activity = discord.Game(name=f'{COMMAND_PREFIX}help for help')
    await bot.change_presence(status=discord.Status.online, activity=activity)

bot.run(TOKEN)
