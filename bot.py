#!/usr/bin/env python
from configparser import ConfigParser
import logging
from discord.ext import commands
from silva import bot_commands
from silva.utilities import granblue_twitter
import discord
import aiosqlite
import asyncio
import argparse

loop = asyncio.get_event_loop()
parser = argparse.ArgumentParser(description='A Granblue Fantasy discord bot.')
parser.add_argument('--config', '-c', type=str, default='config.ini')
args = parser.parse_args()
config_file = args.config

log_format = "%(asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(level=logging.INFO, format=log_format)

config = ConfigParser()
config.read(config_file)

with open(config['default']['discord_token']) as fp:
    TOKEN = fp.read().strip()
COMMAND_PREFIX = config['default']['command_prefix']

bot = commands.Bot(
    command_prefix=COMMAND_PREFIX,
    description="The best sniper. She'll drink you under the table.",
    case_insensitive=True)

setattr(
    bot, 'events_channel',
    int(config['twitter']['discord_events_channel_id']))

bot.add_cog(bot_commands.SilvaCmds(bot))
bot.add_cog(bot_commands.MiscCommands(bot))

twitter_config = ConfigParser()
twitter_config.read(config['default']['twitter_tokens'])


@bot.event
async def on_connect():
    bot.conn = 'aliases.sqlite3'
    async with aiosqlite.connect(bot.conn) as db:
        db.row_factory = aiosqlite.Row
        cmd: str = (
            "CREATE TABLE IF NOT EXISTS aliases"
            " (id integer primary key autoincrement,"
            " word text, alias text, is_proper_noun int DEFAULT 1)"
        )
        await db.execute(cmd)
        cmd: str = (
            "CREATE UNIQUE INDEX IF NOT EXISTS"
            " idx_positions_id ON aliases(id)"
        )
        await db.execute(cmd)
        await db.commit()


@bot.event
async def on_ready():
    logging.info(f'Logged in as {bot.user.name} ({bot.user.id})')
    logging.info('------')
    activity = discord.Game(name=f'{COMMAND_PREFIX}help for help')
    await bot.change_presence(status=discord.Status.online, activity=activity)
    to_follow_str = config['twitter']['twitter_user_id'].split(',')
    to_follow = [int(item) for item in to_follow_str]
    twitter = granblue_twitter.Twitter(
        bot=bot,
        consumer=twitter_config['default']['api'],
        consumer_secret=twitter_config['default']['api_secret'],
        access=twitter_config['default']['access_token'],
        access_secret=twitter_config['default']['access_token_secret'],
        discord_channel_id=config['twitter']['discord_news_feed_channel_id'],
        twitter_user_id=to_follow)
    await twitter.follow()


@bot.event
async def on_command_error(ctx, *args, **kwargs):
    warning = args[0]
    guild = ctx.guild
    if guild is None:
        guild = 'direct message'
    msg = f'{ctx.author} from {guild} caused an error: {warning}'
    logging.warning(f'message: {msg}')
    mention = ctx.author.mention
    content = ctx.message.content
    r = f"{mention}, I don't know what `{content}` means."
    await ctx.send(r)

try:
    loop.run_until_complete(bot.login(token=TOKEN))
    loop.run_until_complete(bot.connect())
except KeyboardInterrupt:
    logging.info('Logging out. (You might need to ctrl-C twice.)')
    loop.run_until_complete(bot.logout())
finally:
    loop.close()
