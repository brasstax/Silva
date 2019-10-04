#!/usr/bin/env python
import logging
from discord.ext import commands
from discord import Embed, Colour, __version__, File
import aiohttp
from silva.utilities import gbfwiki, misc
from datetime import datetime
import random
import pytz
import re
import io


class SilvaCmds(commands.Cog, name="GBF-related commands"):
    def __init__(self, bot):
        self.bot = bot
        self.text_utils = misc.TextUtils()
        logging.info('Silva commands initialized.')

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
            self, ctx, word: str, alias: str, is_proper: bool='True'):
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
        emoji_regex = r'^<a?:\w+:\d+>$'
        if not re.match(emoji_regex, emoji):
            await ctx.send('No emoji found.')
        else:
            # Static emojis are uploaded as png, and animated emojis are
            # uploaded as a gif. Try to get the gif first; if 415,
            # get the PNG.
            # Get only the ID (in case the emoji name has a number)
            emoji_id = re.findall('\d+', emoji)[-1]
            # Get the name of the emoji (avoids the 'a:' prefix)
            # for animated emoji
            emoji_name = re.findall(':\w+', emoji)[0][1:]
            emoji_url = f'https://cdn.discordapp.com/emojis/{emoji_id}'
            try:
                async with aiohttp.ClientSession() as session:
                    resp = await session.get(
                            f'{emoji_url}.gif', timeout=10)
                    emoji_name_ext = f'{emoji_name}.gif'
                    if resp.status != 200:
                        resp = await session.get(
                            f'{emoji_url}.png', timeout=10)
                        emoji_name_ext = f'{emoji_name}.png'
                    data = io.BytesIO(await resp.read())
                    await ctx.send(file=File(data, f'{emoji_name_ext}'))
            except Exception as e:
                logging.warning(e)
                await ctx.send("Couldn't embiggen at this time.")
