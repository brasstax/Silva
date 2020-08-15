#!/usr/bin/env python
import logging
from discord.ext import commands
from discord import Embed, Colour, __version__, File
from discord import utils as discord_utils
from silva.utilities import misc, wikimedia_cats
from datetime import datetime
import pytz
import re
from bs4 import BeautifulSoup


class Commands(commands.Cog, name="Misc. commands"):
    def __init__(self, bot):
        self.bot = bot
        self.text_utils = misc.TextUtils()
        logging.info("Misc commands initialized.")

    @commands.command(name="testregex", aliases=["test", "regex"], hidden=True)
    @commands.is_owner()
    async def test_regex(self, ctx, *, arg):
        bot = self.bot
        text_utils = self.text_utils
        text = arg
        new_text = await text_utils.regex(bot.conn, text)
        await ctx.send(new_text)

    @commands.command(name="jst", aliases=["time"])
    async def time(self, ctx):
        """
        Sends the current time, in JST, to a channel.
        """
        guild = ctx.guild if ctx.guild else "a direct message"
        logging.info(f"time requested by {ctx.author} in {guild}.")
        now = datetime.utcnow().replace(tzinfo=pytz.utc)
        jst = now.astimezone(tz=pytz.timezone("Asia/Tokyo"))
        jst_str = datetime.strftime(jst, "%-H:%M:%S, %A, %B %-d, %Y JST")
        msg = f"It's currently {jst_str}."
        await ctx.send(msg)

    @commands.command(name="page", aliases=["ping"])
    async def page(self, ctx):
        """
        Pages the owner of this bot.
        """
        guild = ctx.guild if ctx.guild else "a direct message"
        logging.info(f"page requested by {ctx.author} in {guild}.")
        # The two servers the bot should be allowed to page the owner in.
        if ctx.guild.id != 173939350613131265 and ctx.guild.id != 305461329882251275:
            await ctx.send("You must be in the same server as the owner.")
        else:
            app_info = await self.bot.application_info()
            owner = app_info.owner
            msg = f"{owner.mention}, {ctx.author.mention} is looking for you."
            await ctx.send(msg)

    @commands.command(name="info", aliases=["blame", "github", "credits"])
    async def info(self, ctx):
        """
        Outputs running info about this bot.
        """
        guild = ctx.guild if ctx.guild else "a direct message"
        logging.info(f"blame requested by {ctx.author} in {guild}.")
        app_info = await self.bot.application_info()
        msg = Embed(
            title="Silva (https://github.com/brasstax/silva)",
            url="https://github.com/brasstax/silva",
            color=Colour.teal(),
        )
        msg.set_author(
            name="Silva",
            url="https://github.com/brasstax/silva",
            icon_url=app_info.icon_url,
        )
        msg.add_field(name="Author", value=app_info.owner, inline=False)
        msg.add_field(name="Framework", value=f"Discord.py {__version__}")
        await ctx.send(embed=msg)

    @commands.command(name="embiggen", aliases=["bigmoji", "hugemoji"])
    async def hugemoji(self, ctx, emoji: str):
        """
        Takes a Discord emoji and posts it as a large picture.
        """
        logging.info(f"{ctx.author} requested embiggen for {emoji}.")
        emoji_regex = r"(^\\?<a?:\w+:\d+>$)|(^\\?.$)"
        if not re.match(emoji_regex, emoji):
            return await ctx.send("No emoji found.")
        utils = misc.EmojiUtils()
        # strip out any backslashes in our emoji string.
        emoji = emoji.replace("\\", "")
        # For standard emoji, check to see if we can grab the image
        # from MaxCDN.
        if len(emoji) == 1:
            emoji_id = hex(ord(emoji))[2:]
            emoji_name_ext = f"{emoji_id}.png"
            try:
                data, img_type = await utils.get_emoji("maxcdn", emoji_id)
                data.seek(0)
                return await ctx.send(file=File(data, f"{emoji_name_ext}"))
            except utils.NoEmojiFound:
                return await ctx.send("No emoji found.")
            except Exception as e:
                logging.warning(e)
                return await ctx.send("Couldn't embiggen at this time.")
        # Static emojis are uploaded as png, and animated emojis are
        # uploaded as a gif. Try to get the gif first; if 415,
        # get the PNG.
        # Get only the ID (in case the emoji name has a number)
        emoji_id = re.findall(r"\d+", emoji)[-1]
        # Get the name of the emoji (avoids the 'a:' prefix)
        # for animated emoji
        emoji_name = re.findall(r":\w+", emoji)[0][1:]
        try:
            data, img_type = await utils.get_emoji("discord", emoji_id)
            return await ctx.send(file=File(data, f"{emoji_name}.{img_type}"))
        except Exception as e:
            logging.warning(e)
            return await ctx.send("Couldn't embiggen at this time.")

    @commands.command(name="cat", aliases=["catte", "likeblue"])
    async def wikicat(self, ctx):
        """
        Gets a random cat picture from Wikipedia.
        """
        logging.info(f"{ctx.author} requested a cat picture.")
        cat = wikimedia_cats.wikicats()
        init_msg = await ctx.send("BETA: Getting a cat picture, one sec.")
        async with ctx.channel.typing():
            await cat.async_init()
            try:
                artist = cat.info["user"]
                desc = BeautifulSoup(
                    cat.info["extmetadata"]["ImageDescription"]["value"],
                    features="html.parser",
                ).text
                desc_url = cat.info["descriptionurl"]
                filename = desc_url.split(":")[-1].replace("_", " ")
                desc_surl = cat.info["descriptionshorturl"]
                picture = cat.info["thumburl"]
                await init_msg.delete()
                msg_embed = Embed(
                    title=filename,
                    url=desc_surl,
                    color=Colour.dark_purple(),
                    description=desc,
                )
                msg_embed.set_author(name=artist)
                msg_embed.set_image(url=picture)
                return await ctx.send(embed=msg_embed)
            except Exception as e:
                try:
                    logging.warning(e)
                    logging.warning(f"cat info: {cat.info}")
                    logging.warning(f"cat breed: {cat.breed}")
                    logging.warning(f"cat images_list: {cat.images_list}")
                    logging.warning(f"cat list: {cat.cat_list}")
                    return await init_msg.edit(
                        content="BETA: Couldn't get a cat picture from Wikipedia."
                    )  # noqa
                except Exception as e:
                    logging.warning(e)
                    logging.warning(cat)
                    return await init_msg.edit(
                        content="BETA: Couldn't get a cat picture from Wikipedia."
                    )  # noqa

    @commands.command(name="headpat", aliases=["stick"])
    async def headpat(self, ctx, *name: str):
        """
        Stick *really* wanted this command.
        """
        guild = ctx.guild if ctx.guild else "a direct message"
        logging.info(f"stick requested by {ctx.author} in {guild}.")
        name = " ".join(name)
        if not name:
            msg = f"_headpats {discord_utils.escape_markdown(ctx.author.display_name)}_"
            return await ctx.send(msg)
        try:
            users = self.text_utils.user_searcher(self.bot, name)
        except ValueError:
            return await ctx.send(
                "Please narrow down your search (use `username#id` if needed.)"
            )
        if not users:
            msg = f"{ctx.author.display_name}, I couldn't find any users with the name '{name}'."
            msg += (
                f" You can have a headpat anyway. _headpats {discord_utils.escape_markdown(ctx.author.display_name)}_"
            )
            return await ctx.send(msg)
        msg = (
            f"_headpats {', '.join([discord_utils.escape_markdown(x.display_name) for x in users])}"
            f" and {discord_utils.escape_markdown(ctx.author.display_name)}_")
        return await ctx.send(msg)
