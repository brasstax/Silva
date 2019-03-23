#!/usr/bin/env python
import logging
from discord.ext import commands
from discord import Embed, Colour
import aiohttp
import random
from silva.utilities import gbfwiki, misc
from datetime import datetime
import pytz


class SilvaCmds(commands.Cog, name="GBF-related commands"):
    def __init__(self, bot):
        self.bot = bot
        self.db_utils = misc.Database()
        logging.info('Silva commands initialized.')

    @commands.command(name='song', aliases=['tweyen'])
    async def song(self, ctx):
        '''
        Gets a fact about Song. Or Tweyen. Depends on Silva's mood.
        '''
        bot = self.bot
        db = self.db_utils
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    'http://www.pycatfacts.com/catfacts.txt?sfw=true',
                        timeout=10) as fact:
                    text = await fact.text()
            aliases = await db.get_aliases(bot.conn)
            for word, alias in aliases.items():
                choice = random.choice(alias)
                text = text.replace(word.lower(), choice)
                text = text.replace(word.capitalize(), choice)
            await ctx.send(text)
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


class MiscCommands(commands.Cog, name='Misc. commands'):
    def __init__(self, bot):
        self.bot = bot
        logging.info('Misc commands initialized.')

    @commands.command(name='testregex', hidden=True)
    @commands.is_owner()
    async def test_regex(self, ctx):
        pass

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

    @commands.command(name='github', aliases=['git'])
    async def github(self, ctx):
        '''
        Sends a link to the bot's github.
        '''
        guild = ctx.guild if ctx.guild else 'a direct message'
        logging.info(f'github requested by {ctx.author} in {guild}.')
        msg = 'https://github.com/brasstax/Silva'
        await ctx.send(msg)

    @commands.command(name='blame', aliases=['credits'])
    async def blame(self, ctx):
        '''
        Informs the user who wrote this bot.
        '''
        guild = ctx.guild if ctx.guild else 'a direct message'
        logging.info(f'blame requested by {ctx.author} in {guild}.')
        app_info = await self.bot.application_info()
        owner = app_info.owner
        msg = f'Blame {owner} for this bot.'
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
