#!/usr/bin/env python
import logging
from discord.ext import commands
from discord import Embed, Colour, __version__, File
import aiohttp
from silva.utilities import gbfwiki, misc, wikimedia_cats
from datetime import datetime
import random
import pytz
import re
from bs4 import BeautifulSoup


class SilvaCmds(commands.Cog, name="GBF-related commands"):
    def __init__(self, bot):
        self.bot = bot
        self.text_utils = misc.TextUtils()
        logging.info('Silva commands initialized.')

    @commands.command(name='sparkcalc', aliases=['spark'])
    async def calculate_spark(
            self, ctx, crystals: int = 0, singles: int = 0, tens: int = 0):
        '''
        Calculates how many draws you have and how close you are to a spark.
        :param crystals (int): the amount of crystals a player holds.
        300 crystals for a single draw. 0 by default.
        :param singles (int): How many single-draw tickets a player has.
        Worth one draw. 0 by default.
        :param tens (int): How many ten-draw tickets a player has.
        Worth ten draws. 0 by default.
        '''
        guild = ctx.guild if ctx.guild else 'a direct message'
        logging.info(f'sparkcalc requested by {ctx.author} in {guild}.')
        try:
            t = self.text_utils
            draws, spark_percentage = t.calculate_spark(crystals, tens, singles)
        except misc.TextUtils.InvalidDrawsError as e:
            return await ctx.send(f'{e}, {ctx.author.display_name}')
        msg = f'{ctx.author.display_name},'
        msg += f" you have {crystals} crystal{(lambda x: 's' if x != 1 else '')(crystals)},"
        msg += f" {tens} ten-draw ticket{(lambda x: 's' if x != 1 else '')(tens)},"
        msg += f" and {singles} single-draw ticket{(lambda x: 's' if x != 1 else '')(singles)}."
        msg += f" You have **{draws} roll{(lambda x: 's' if x != 1 else '')(draws)}**."
        if spark_percentage >= 100 and spark_percentage < 200:
            msg += " You have one spark and you're"
            msg += f" {(spark_percentage % 100):.2f}%"
            msg += " closer to a spark after."
        elif spark_percentage >= 200:
            msg += f" You have {int(spark_percentage // 100)} sparks and"
            msg += f" you're {(spark_percentage % 100):.2f}% closer"
            msg += " to a spark after."
        else:
            msg += f' You are {spark_percentage:.2f}% closer'
            msg += ' to your next spark.'
        if random.randint(1, 100) <= 25 or spark_percentage >= 100:
            encouraging_msg = random.choice([
                "You've got this!",
                "Ganbaruby!",
                "<:ganbaruby:275832773464293377>",
                "<:gobu:284812336580263938>",
                "I hope you like your spark!",
                "May your spark shower you with the draws you want.",
                "Silva, with her heart of silver, believes in you!",
                "I'm excited for you and I can't wait for your spark."
            ])
            msg += f" {encouraging_msg}"
        if crystals == 0 and singles == 0 and tens == 0:
            msg += (
                "\n If you're not sure how this command works, check the"
                ' help on "sparkcalc".')
        return await ctx.send(msg)

    @commands.command(name='song', aliases=['tweyen'])
    async def song(self, ctx):
        '''
        Gets a fact about Song. Or Tweyen. Depends on Silva's mood.
        '''
        bot = self.bot
        text_utils = self.text_utils
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    'http://www.pycatfacts.com/catfacts.txt?sfw=true',
                        timeout=10) as fact:
                    status = fact.status
                    text = await fact.text()
            if status >= 400:
                new_text = random.choice(
                    [
                        'Hic... _hic..._ Soooooooong...where are youuuuu....',
                        'Heyyyyyy. Another beer! I ran out!',
                        'I love beer. More beeeeeeeeeeer!',
                        'Zzzzzz...',
                        'Beer! Beer! Beer! Beer! Beer!',
                        "We're never going to get SSR Reinhardtzar!"
                    ]
                )
                new_text += " (Silva has had a bit too much to drink."
                app_info = await self.bot.application_info()
                owner = app_info.owner
                new_text += (
                    f" {owner.mention},"
                    " please check why Silva isn't working right.)")
                logging.info(f'Status from server: {status} {text}')
            else:
                new_text = await text_utils.regex(bot.conn, text)
            await ctx.send(new_text)
            guild = ctx.guild if ctx.guild else 'a direct message'
            logging.info(f'song requested by {ctx.author} in {guild}.')
        except Exception as e:
            logging.warning(f'Could not get cat fact: {e}')
            await ctx.send("I couldn't get a fact at this time, sorry!")

    @commands.command()
    async def events(self, ctx):
        '''
        Gets information from gbf.wiki on current and future events.
        '''
        guild = ctx.guild if ctx.guild else 'a direct message'
        logging.info(f'events requested by {ctx.author} in {guild}.')
        thinking_msg = 'One sec, grabbing the current and upcoming events.'
        msg = await ctx.send(thinking_msg)
        now = datetime.utcnow().replace(tzinfo=pytz.utc)
        try:
            wiki = await gbfwiki.init_wiki()
            events = wiki.get_events()
            msg_current = Embed(
                title='Granblue Fantasy Current Events',
                url='https://gbf.wiki',
                color=Colour.teal(),
                timestamp=now)
            for event in events['current']:
                msg_current.add_field(
                    name=f"[{event['title']}]({event['url']})",
                    value=f"Ends on {event['finish']}",
                    inline=False
                )
            msg_upcoming = Embed(
                title='Granblue Fantasy Upcoming Events',
                url='https://gbf.wiki',
                color=Colour.dark_purple(),
                timestamp=now)
            for event in events['upcoming']:
                msg_upcoming.add_field(
                    name=f"[{event['title']}]({event['url']})",
                    value=f"{event['start']} to {event['finish']}",
                    inline=False
                )
            # send to a dedicated event channel if the message is not a DM
            if ctx.guild:
                events_channel = self.bot.get_channel(self.bot.events_channel)
            else:
                events_channel = ctx
            # If the event channel exists, search to see if the bot has posted
            # existing events before. If so, edit those instead of sending
            # a new embed. Best used for an events channel that is locked to
            # posting only by the bot.
            if ctx.guild:
                existing_messages = []
                async for message in events_channel.history(limit=200):
                    # Assume the first message to edit is the current events,
                    # and the second message is the upcoming events.
                    if message.author == self.bot.user and message.pinned:
                        existing_messages.append(message)
                    if len(existing_messages) >= 2:
                        break
                if not existing_messages:
                    await events_channel.send(embed=msg_current)
                    await events_channel.send(embed=msg_upcoming)
                else:
                    await existing_messages[0].edit(embed=msg_current)
                    await existing_messages[1].edit(embed=msg_upcoming)
            else:
                await events_channel.send(embed=msg_current)
                await events_channel.send(embed=msg_upcoming)
            if ctx.guild:
                mention_msg = (
                    f'Hi {ctx.author.mention}! I posted the current and'
                    f' upcoming events in {events_channel.mention}.')
            else:
                mention_msg = 'Here you go!'
            await msg.edit(content=mention_msg)
        except Exception as e:
            logging.warning(f'Could not retrieve events: {e}')
            await msg.edit(
                content="I couldn't retrieve the events at this time.")


class AliasCommands(commands.Cog, name='Alias commands'):
    def __init__(self, bot):
        self.bot = bot
        self.db_utils = misc.Database(bot.conn)
        logging.info('Alias commands initialized.')

    @commands.command(name='alias', aliases=['aliases'])
    async def get_alias(self, ctx, word: str):
        '''
        Gets the aliases for a given word.
        '''
        db = self.db_utils
        guild = ctx.guild if ctx.guild else 'a direct message'
        logging.info(
            f'aliases requested by {ctx.author} in {guild} for {word}.')
        aliases = await db.get_alias(word)
        if not aliases:
            msg = f'No aliases found for "{word}."'
        else:
            msg = f'Aliases for "{word}": {", ".join(aliases)}'
        await ctx.send(msg)

    @commands.command(name='addalias', aliases=['setalias'], hidden=True)
    @commands.is_owner()
    async def set_alias(
            self, ctx, word: str, alias: str, is_proper: bool = 'True'):
        '''
        Adds an alias to a given word.
        :param word (str): The word to add an alias for.
        :param alias (str): The alias to add to a word.
        :param is_proper (bool): Whether the alias is a proper noun.
        '''
        db = self.db_utils
        try:
            if is_proper:
                proper: int = 1
            else:
                proper: int = 0
            await db.set_alias(word, alias, proper)
            msg = f'Alias "{alias}" added for "{word}."'
            await ctx.send(msg)
        except misc.Database.AliasExistsError:
            msg = f'Alias "{alias}" already exists for "{word}."'
            await ctx.send(msg)

    @commands.command(name='rmalias', aliases=['delalias'], hidden=True)
    @commands.is_owner()
    async def rm_alias(
            self, ctx, word: str, alias: str):
        '''
        Removes an alias from a given word.
        :param word (str): the word to remove the alias from.
        :param alias (str): the alias to remove.
        '''
        db = self.db_utils
        aliases = await db.get_alias(word)
        if not aliases:
            await ctx.send(f'"{alias}" is not an alias of "{word}."')
            return
        aliases = [x.lower() for x in aliases]
        if alias not in aliases:
            await ctx.send(f'"{alias}" is not an alias of "{word}."')
        else:
            await db.rm_alias(word, alias)
            await ctx.send(f'"{alias}" removed as alias from "{word}."')
        return


class MiscCommands(commands.Cog, name='Misc. commands'):
    def __init__(self, bot):
        self.bot = bot
        self.text_utils = misc.TextUtils()
        logging.info('Misc commands initialized.')

    @commands.command(name='testregex', aliases=['test', 'regex'], hidden=True)
    @commands.is_owner()
    async def test_regex(self, ctx, *, arg):
        bot = self.bot
        text_utils = self.text_utils
        text = arg
        new_text = await text_utils.regex(bot.conn, text)
        await ctx.send(new_text)

    @commands.command(name='jst', aliases=['time'])
    async def time(self, ctx):
        '''
        Sends the current time, in JST, to a channel.
        '''
        guild = ctx.guild if ctx.guild else 'a direct message'
        logging.info(f'time requested by {ctx.author} in {guild}.')
        now = datetime.utcnow().replace(tzinfo=pytz.utc)
        jst = now.astimezone(tz=pytz.timezone('Asia/Tokyo'))
        jst_str = datetime.strftime(
            jst,
            '%-H:%M:%S, %A, %B %-d, %Y JST'
        )
        msg = f"It's currently {jst_str}."
        await ctx.send(msg)

    @commands.command(name='page', aliases=['ping'])
    async def page(self, ctx):
        '''
        Pages the owner of this bot.
        '''
        guild = ctx.guild if ctx.guild else 'a direct message'
        logging.info(f'page requested by {ctx.author} in {guild}.')
        # The two servers the bot should be allowed to page the owner in.
        if (ctx.guild.id != 173939350613131265
                and ctx.guild.id != 305461329882251275):
            await ctx.send('You must be in the same server as the owner.')
        else:
            app_info = await self.bot.application_info()
            owner = app_info.owner
            msg = f'{owner.mention}, {ctx.author.mention} is looking for you.'
            await ctx.send(msg)

    @commands.command(name='info', aliases=['blame', 'github', 'credits'])
    async def info(self, ctx):
        '''
        Outputs running info about this bot.
        '''
        guild = ctx.guild if ctx.guild else 'a direct message'
        logging.info(f'blame requested by {ctx.author} in {guild}.')
        app_info = await self.bot.application_info()
        msg = Embed(
            title='Silva (https://github.com/brasstax/silva)',
            url='https://github.com/brasstax/silva',
            color=Colour.teal())
        msg.set_author(
            name='Silva',
            url='https://github.com/brasstax/silva',
            icon_url=app_info.icon_url)
        msg.add_field(
            name="Author",
            value=app_info.owner,
            inline=False)
        msg.add_field(
            name="Framework",
            value=f"Discord.py {__version__}"
        )
        await ctx.send(embed=msg)

    @commands.command(name='embiggen', aliases=['bigmoji', 'hugemoji'])
    async def hugemoji(self, ctx, emoji: str):
        '''
        Takes a Discord emoji and posts it as a large picture.
        '''
        logging.info(f'{ctx.author} requested embiggen for {emoji}.')
        emoji_regex = r'(^\\?<a?:\w+:\d+>$)|(^\\?.$)'
        if not re.match(emoji_regex, emoji):
            return await ctx.send('No emoji found.')
        utils = misc.EmojiUtils()
        # strip out any backslashes in our emoji string.
        emoji = emoji.replace('\\', '')
        # For standard emoji, check to see if we can grab the image
        # from MaxCDN.
        if len(emoji) == 1:
            emoji_id = hex(ord(emoji))[2:]
            emoji_name_ext = f'{emoji_id}.png'
            try:
                data, img_type = await utils.get_emoji('maxcdn', emoji_id)
                data.seek(0)
                return await ctx.send(
                    file=File(data, f'{emoji_name_ext}'))
            except utils.NoEmojiFound:
                return await ctx.send("No emoji found.")
            except Exception as e:
                logging.warning(e)
                return await ctx.send("Couldn't embiggen at this time.")
        # Static emojis are uploaded as png, and animated emojis are
        # uploaded as a gif. Try to get the gif first; if 415,
        # get the PNG.
        # Get only the ID (in case the emoji name has a number)
        emoji_id = re.findall(r'\d+', emoji)[-1]
        # Get the name of the emoji (avoids the 'a:' prefix)
        # for animated emoji
        emoji_name = re.findall(r':\w+', emoji)[0][1:]
        try:
            data, img_type = await utils.get_emoji('discord', emoji_id)
            return await ctx.send(file=File(data, f'{emoji_name}.{img_type}'))
        except Exception as e:
            logging.warning(e)
            return await ctx.send("Couldn't embiggen at this time.")

    @commands.command(name='cat', aliases=['catte', 'likeblue'])
    async def wikicat(self, ctx):
        '''
        Gets a random cat picture from Wikipedia.
        '''
        logging.info(f'{ctx.author} requested a cat picture.')
        cat = wikimedia_cats.wikicats()
        init_msg = await ctx.send('BETA: Getting a cat picture, one sec.')
        async with ctx.channel.typing():
            try:
                await cat.async_init()
                artist = cat.info['user']
                desc = BeautifulSoup(
                    cat.info['extmetadata']['ImageDescription']['value'],
                    features='html.parser').text
                desc_url = cat.info['descriptionurl']
                filename = desc_url.split(':')[-1].replace('_', ' ')
                desc_surl = cat.info['descriptionshorturl']
                picture = cat.info['thumburl']
                await init_msg.delete()
                msg_embed = Embed(
                    title=filename,
                    url=desc_surl,
                    color=Colour.dark_purple(),
                    description=desc)
                msg_embed.set_author(name=artist)
                msg_embed.set_image(url=picture)
                return await ctx.send(embed=msg_embed)
            except Exception as e:
                try:
                    logging.warning(e)
                    logging.warning(f'cat info: {cat.info}')
                    logging.warning(f'cat breed: {cat.breed}')
                    logging.warning(f'cat images_list: {cat.images_list}')
                    logging.warning(f'cat list: {cat.cat_list}')
                    return await init_msg.edit(
                        content="BETA: Couldn't get a cat picture from Wikipedia.")  # noqa
                except Exception as e:
                    logging.warning(e)
                    logging.warning(cat)
                    return await init_msg.edit(
                        content="BETA: Couldn't get a cat picture from Wikipedia.")  # noqa

    @commands.command(name='headpat', aliases=['stick'])
    async def headpat(self, ctx, *name: str):
        '''
        Stick *really* wanted this command.
        '''
        guild = ctx.guild if ctx.guild else 'a direct message'
        logging.info(f'stick requested by {ctx.author} in {guild}.')
        name = ' '.join(name)
        if not name:
            msg = f"_headpats {ctx.author.display_name}_"
            return await ctx.send(msg)
        try:
            users = self.text_utils.user_searcher(self.bot, name)
        except ValueError:
            return await ctx.send('Please narrow down your search (use `username#id` if needed.)')
        if not users:
            msg = f"{ctx.author.display_name}, I couldn't find any users with the name '{name}'."
            msg += f" You can have a headpet anyway. _headpats {ctx.author.display_name}_"
            return await ctx.send(msg)
        msg = f"_headpats {', '.join([x.display_name for x in users])} and {ctx.author.display_name}_"
        return await ctx.send(msg)


class PronounCommands(commands.Cog, name='Pronoun commands'):
    def __init__(self, bot):
        self.bot = bot
        self.db_utils = misc.Database(bot.conn)
        self.text_utils = misc.TextUtils()
        logging.info('Pronoun commands initialized.')

    @commands.command(name='pronouns', aliases=['getpronouns'])
    async def get_pronoun(self, ctx, *name: str):
        '''
        Lists the pronouns for a given user.
        :param name: Either the username or the display name of a user to look up.
        '''
        guild = ctx.guild if ctx.guild else 'a direct message'
        logging.info(f'get_pronoun requested by {ctx.author} in {guild}.')
        if not name:
            users = [ctx.author]
        else:
            name = ' '.join(name)
            try:
                users = self.text_utils.user_searcher(self.bot, name)
            except ValueError:
                return await ctx.send('Please narrow your search (use `username#id` if needed.)')
        if not users:
            await ctx.send(f'No user "{name}" found.')
        msg = ''
        for user in users:
            try:
                pronouns = await self.db_utils.get_pronouns(user.id)
                if not pronouns:
                    raise self.db_utils.MissingUserError()
                msg += f"{user.display_name} uses the following pronouns:"
                msg += f" {pronouns}"
                msg += "\n"
            except self.db_utils.MissingUserError:
                msg += f"{user.display_name} has not set their pronouns yet."
        return await ctx.send(msg)

    @commands.command(name='addpronouns', aliases=['setpronouns'])
    async def set_pronoun(self, ctx, pronouns):
        '''
        Adds your pronouns.
        :param pronouns: a string of your pronouns.
        '''
        guild = ctx.guild if ctx.guild else 'a direct message'
        logging.info(f'set_pronoun requested by {ctx.author} in {guild}.')
        try:
            username = f"{ctx.author.name}#{ctx.author.discriminator}"
            await self.db_utils.set_pronouns(username, ctx.author.id, pronouns)
        except ValueError:
            return await ctx.send(f"{ctx.author.display_name}, you have a max of 31 characters for the pronoun field.")
        msg = f"{ctx.author.display_name}, I have added '{pronouns}' as your pronouns."
        return await ctx.send(msg)

    @commands.command(name='delpronouns', aliases=['rmpronouns'])
    async def rm_pronoun(self, ctx):
        '''
        Removes your pronouns.
        '''
        guild = ctx.guild if ctx.guild else 'a direct message'
        logging.info(f'rm_pronoun requested by {ctx.author} in {guild}.')
        await self.db_utils.rm_pronouns(ctx.author.id)
        msg = f"{ctx.author.display_name}, I have removed your pronouns from the database."
        return await ctx.send(msg)
