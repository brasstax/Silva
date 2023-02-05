#!/usr/bin/env python
from configparser import ConfigParser
import logging
from discord.ext import commands
from silva.bot_commands import Silva, Aliases, Misc, Pronouns
from silva.utilities import granblue_twitter, scheduled_commands
import discord
import aiosqlite
import asyncio
import argparse

loop = asyncio.get_event_loop()
parser = argparse.ArgumentParser(description="A Granblue Fantasy discord bot.")
parser.add_argument("--config", "-c", type=str, default="config.ini")
args = parser.parse_args()
config_file = args.config

intents = discord.Intents.default()
intents.members = True

log_format = "[%(filename)s:%(lineno)s:%(funcName)s() ]%(asctime)s - %(levelname)s - %(message)s"  # noqa
logging.basicConfig(level=logging.INFO, format=log_format)

config = ConfigParser(interpolation=None)
config.read(config_file)

with open(config["default"]["discord_token"]) as fp:
    TOKEN = fp.read().strip()
COMMAND_PREFIX = config["default"]["command_prefix"]

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or(COMMAND_PREFIX),
    description="The best sniper. She'll drink you under the table.",
    case_insensitive=True,
    intents=intents
)
bot.aliases_conn = "aliases.sqlite3"
bot.events_channel = config["twitter"]["discord_news_feed_channel_id"]

setattr(bot, "events_channel", int(config["twitter"]["discord_events_channel_id"]))

setattr(bot, "is_following", False)

bot.add_cog(Silva.Commands(bot))
bot.add_cog(Misc.Commands(bot))
bot.add_cog(Aliases.Commands(bot))
bot.add_cog(Pronouns.Commands(bot))

@bot.event
async def on_connect():
    bot.COMMAND_PREFIX = COMMAND_PREFIX
    async with aiosqlite.connect(bot.aliases_conn) as db:
        db.row_factory = aiosqlite.Row
        cmd: str = (
            "CREATE TABLE IF NOT EXISTS aliases"
            " (id integer primary key autoincrement,"
            " word text, alias text, is_proper_noun int DEFAULT 1)"
        )
        await db.execute(cmd)
        cmd: str = (
            "CREATE UNIQUE INDEX IF NOT EXISTS" " idx_positions_id ON aliases(id)"
        )
        await db.execute(cmd)
        cmd: str = (
            "CREATE TABLE IF NOT EXISTS pronouns"
            " (id integer primary key autoincrement,"
            " user text, user_id int, pronouns text DEFAULT 0)"
        )
        await db.execute(cmd)
        cmd: str = (
            "CREATE UNIQUE INDEX IF NOT EXISTS"
            " idx_positions_pronouns_id ON pronouns(id)"
        )
        await db.execute(cmd)
        cmd: str = (
            "CREATE UNIQUE INDEX IF NOT EXISTS"
            " idx_positions_pronouns_user_id ON pronouns(user_id)"
        )
        await db.execute(cmd)
        cmd: str = (
            "CREATE TABLE IF NOT EXISTS raidroles"
            " (id integer primary key autoincrement,"
            " role_id int, role_name text)"
        )
        await db.execute(cmd)
        cmd: str = (
            "CREATE UNIQUE INDEX IF NOT EXISTS" " idx_raid_group ON raidroles(role_id)"
        )
        await db.execute(cmd)
        await db.commit()


@bot.event
async def on_ready():
    logging.info(f"Logged in as {bot.user.name} ({bot.user.id})")
    logging.info("------")
    activity = discord.Game(name=f"{COMMAND_PREFIX}help for help")
    await bot.change_presence(status=discord.Status.online, activity=activity)
    to_follow = config["twitter"]["twitter_usernames"].split(",")
    bot.twitter = granblue_twitter.Twitter(
        bot=bot,
        discord_channel_id=config["twitter"]["discord_news_feed_channel_id"],
        twitter_usernames=to_follow,
        twitter_database_db=config["database"]["database"],
        twitter_database_host=config["database"]["host"],
        twitter_database_username=config["database"]["username"],
        twitter_database_password=config["database"]["password"]
    )
    await bot.twitter.follow()


@bot.event
async def on_command_error(ctx, *args, **kwargs):
    warning = args[0]
    guild = ctx.guild
    if guild is None:
        guild = "direct message"
    msg = f"{ctx.author} from {guild} caused an error: {warning}"
    logging.warning(f"message: {msg}")
    pass


try:
    loop.run_until_complete(bot.login(token=TOKEN))
    scheduled = scheduled_commands.ScheduledEvents(bot)
    loop.create_task(scheduled.update_events())
    loop.run_until_complete(bot.connect())
except KeyboardInterrupt:
    logging.info("Logging out. (You might need to ctrl-C twice.)")
    loop.run_until_complete(bot.twitter.client.conn.close())
    loop.run_until_complete(bot.logout())
finally:
    loop.close()
