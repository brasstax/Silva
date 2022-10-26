#!/usr/bin/env python
import logging
from discord.ext import commands
from discord import Embed, Colour, __version__, File
from discord import utils as discord_utils
from silva.utilities import misc, wikimedia_cats
from datetime import datetime, date
import pytz
import re
from bs4 import BeautifulSoup
import random


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
        async with ctx.channel.typing():
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

    @commands.command(name="biglify2")
    async def biglify2(self, ctx, emoji: str):
        """
        Takes a Discord emoji and makes it bigger using a GPT-trained model.
        Doesn't work for GIFs.
        """
        logging.info(f"{ctx.author} requested biglify for {emoji}.")
        emoji_regex = r"(^\\?<a?:\w+:\d+>$)|(^\\?.$)"
        if not re.match(emoji_regex, emoji):
            return await ctx.send("No emoji found.")
        utils = misc.EmojiUtils()
        # strip out any backslashes in our emoji string.
        emoji = emoji.replace("\\", "")
        # For standard emoji, check to see if we can grab the image
        # from MaxCDN.
        async with ctx.channel.typing():
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
                data, img_type = await utils.get_emoji(
                    "discord", emoji_id, gpt=True, gpt_use_close=True)
                return await ctx.send(file=File(data, f"{emoji_name}.{img_type}"))
            except Exception as e:
                logging.warning(e)
                return await ctx.send("Couldn't biglify at this time.")

    @commands.command(name="biglify")
    async def biglify(self, ctx, emoji: str):
        """
        Takes a Discord emoji and makes it bigger using a GPT-trained model.
        Doesn't work for GIFs. Uses a different mechanism for edge detection
        in case the normal biglify doesn't work out.
        """
        logging.info(f"{ctx.author} requested biglify2 for {emoji}.")
        emoji_regex = r"(^\\?<a?:\w+:\d+>$)|(^\\?.$)"
        if not re.match(emoji_regex, emoji):
            return await ctx.send("No emoji found.")
        utils = misc.EmojiUtils()
        # strip out any backslashes in our emoji string.
        emoji = emoji.replace("\\", "")
        # For standard emoji, check to see if we can grab the image
        # from MaxCDN.
        async with ctx.channel.typing():
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
                data, img_type = await utils.get_emoji(
                    "discord", emoji_id, gpt=True, gpt_use_close=False)
                return await ctx.send(file=File(data, f"{emoji_name}.{img_type}"))
            except Exception as e:
                logging.warning(e)
                return await ctx.send("Couldn't biglify at this time.")

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

    # @commands.command(name="headpat", aliases=["stick"])
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

    @commands.command(name="choose")
    async def choose(self, ctx, *, choices: str = None):
        """
        Chooses from a set of choices, separated by commas. Maximum of 20 choices supported.
        """
        guild = ctx.guild if ctx.guild else "a direct message"
        if choices:
            logging.info(f"choose requested by {ctx.author} in {guild} with args '{choices}'.")
        else:
            logging.info(f"choose requested by {ctx.author} in {guild} with no args.")
            msg = f"To use: `{self.bot.COMMAND_PREFIX}choose item1, item2, item3`"
            return await ctx.send(msg)
        items_list = [item.strip() for item in choices.split(",")]
        if len(items_list) > 20:
            msg = f"{ctx.author.display_name}, I don't feel like choosing between more than 20 items."
            return await ctx.send(msg)
        items = set(items_list)
        item = random.choice(tuple(items))
        return await ctx.send(item)

    @commands.command(name="covidstandardtime", aliases=["cvst", "covidtime"])
    async def covid_standard_time(self, ctx):
        """
        Returns the days, in UTC, since March 1, 2020.
        """
        guild = ctx.guild if ctx.guild else "a direct message"
        logging.info(f"cvst requested by {ctx.author} in {guild}.")
        days = self.text_utils.days_since(date(2020, 3, 1))
        now = datetime.now(pytz.utc)
        msg = f"Today is {now.strftime('%A')}, March {days}{self.text_utils.inflect_day(days)} UTC, 2020."
        return await ctx.send(msg)

    @commands.command(name="roll", aliases=["dicebag", "dice"])
    async def dicebag(self, ctx, *, roll: str="1d6"):
        """
        A purple felt dicebag with clicky-clacky plastic dice. Smells like plastic.
        :param: roll (str): a string representation of the amount of dice to roll, the type of dice,
        and any modifiers.
        Modifiers can be one of the following:
        - +
        - -
        - x or *
        - / (will round down)
        Examples:
        * roll 1d6
        * roll 2d20+1
        * roll 6d100x2
        * roll 5d20/4
        """
        guild = ctx.guild if ctx.guild else "a direct message"
        logging.info(f"roll requested by {ctx.author} in {guild} with args '{roll}'.")
        try:
            dice = misc.Dicebag(roll)
        except (misc.InvalidDiceString, misc.TooManyDiceError) as e:
            return await ctx.send(e)
        result = await dice.roll_dice()
        dice_count = dice.roll_dict['dice_count']
        dice_type = dice.roll_dict['dice_type']
        mod_type = dice.roll_dict['mod_type']
        mod_value = dice.roll_dict['mod_value']
        msg = (
            f"Rolled {dice_count} {dice_type}-sided"
            f" {'die' if dice_count == 1 else 'dice'}"
            f"{f', {mod_type}{mod_value} modifier.' if mod_value != 0 else '.'}"
            f" **{result}{'! CRITICAL HIT!!**' if result == 20 and mod_value == 0 else '.**'}"
        )
        return await ctx.send(msg)

    @commands.command(name="av", aliases=["avatar"])
    async def get_avatar(self, ctx, *name: str):
        """
        Returns the avatar of a user. Can either specify username without the discriminator
        (less accurate) or username with discriminator (ie Seymour#9035).
        """
        guild = ctx.guild if ctx.guild else "a direct message"
        if name:
            logging.info(f"av requested by {ctx.author} in {guild} with args '{name}'.")
        else:
            logging.info(f"av requested by {ctx.author} in {guild} with no args.")
        name = " ".join(name)
        try:
            avatar = self.text_utils.get_avatar(self.bot, name)
        except IndexError:
             msg = f"{ctx.author.display_name}, I couldn't find any users with the name '{name}'."
             return await ctx.send(msg)
        logging.info(avatar)
        return await ctx.send(avatar)