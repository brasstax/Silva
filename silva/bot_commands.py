#!/usr/bin/env python
import logging
from discord.ext import commands
import requests
import random


class SilvaCmds(commands.Cog, name="Silva commands"):
    def __init__(self, bot):
        self.bot = bot
        logging.info('Bot Initialized.')

    @commands.command()
    async def song(self, ctx):
        bot = self.bot
        try:
            fact = requests.get(
                'http://www.pycatfacts.com/catfacts.txt?sfw=true')
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
                logging.info(f"{word}, {aliases[word]}")
            for word, alias in aliases.items():
                choice = random.choice(alias)
                text = text.replace(word.lower(), choice)
                text = text.replace(word.capitalize(), choice)
            await ctx.send(text)
        except Exception as e:
            logging.warning(f'Could not get cat fact: {e}')
            await ctx.send("I couldn't get a fact at this time, sorry!")
