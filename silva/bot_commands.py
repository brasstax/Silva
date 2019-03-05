#!/usr/bin/env python
import logging
from discord.ext import commands
from discord import Embed
import requests
import random
from silva.utilities import gbfwiki


class SilvaCmds(commands.Cog, name="Silva commands"):
    def __init__(self, bot):
        self.bot = bot
        logging.info('Bot Initialized.')

    @commands.command(name='song', aliases=['tweyen'])
    async def song(self, ctx):
        '''
        Gets a fact about Song. Or Tweyen. Depends on Silva's mood.
        '''
        bot = self.bot
        try:
            fact = requests.get(
                'http://www.pycatfacts.com/catfacts.txt?sfw=true',
                timeout=10)
            text = fact.text
            cmd: str = '''
            SELECT word, alias, is_proper_noun FROM aliases;
            '''
            res: list = bot.cursor.execute(cmd)
            aliases: dict = {}
            for row in res:
                word = row['word']
                alias = row['alias']
                if row['is_proper_noun']:
                    alias = alias.capitalize()
                if word not in aliases.keys():
                    aliases[word]: list = []
                aliases[word].append(alias)
            for word, alias in aliases.items():
                choice = random.choice(alias)
                text = text.replace(word.lower(), choice)
                text = text.replace(word.capitalize(), choice)
            await ctx.send(text)
            logging.info(f'{ctx.message.author} called for song')
        except Exception as e:
            logging.warning(f'Could not get cat fact: {e}')
            await ctx.send("I couldn't get a fact at this time, sorry!")

    @commands.command()
    async def events(self, ctx):
        '''
        Gets information from gbf.wiki on current and future events.
        '''
        logging.info(f'events requested by {ctx.author}')
        wiki = gbfwiki.wiki()
        current_events = wiki.get_current_events()
        future_events = wiki.get_upcoming_events()
        msg = Embed(title='Granblue Fantasy Events', url='https://gbf.wiki')
        # We're not actually putting spaces in the value field,
        # but Unicode U+2800. This is so we can create fake not-titles
        # to divide our sections, but since we can't actually put a blank
        # or normal space in the value without Discord complaining, we resort
        # to a hack.
        msg.add_field(name='Current Events', value='⠀', inline=False)
        for event in current_events:
            msg.add_field(
                name=f"[{event['title']}]({event['url']})",
                value=f"Ends on {event['finish']}",
                inline=False
            )
        msg.add_field(name='Upcoming Events', value='⠀', inline=False)
        for event in future_events:
            msg.add_field(
                name=f"[{event['title']}]({event['url']})",
                value=f"{event['duration']}",
                inline=False
            )
        await ctx.send(embed=msg)
